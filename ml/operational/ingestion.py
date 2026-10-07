"""Per-node HMAC ingestion, idempotent retry/replay checks and derived health."""
import base64
import binascii
import hashlib
import hmac
import json
import re
import sqlite3
import threading
from pathlib import Path

from ml.operational.contracts import canonical_bytes,observation,utc,CORE,VERSION


def sign(node_id,key,nonce,sent_at,records):
    raw=canonical_bytes({'schema_version':VERSION,'observations':records})
    header=(node_id+'\n'+nonce+'\n'+utc(sent_at).isoformat()+'\n').encode()
    return dict(protocol='indra_hmac_v1',node_id=node_id,nonce=nonce,sent_at_utc=utc(sent_at).isoformat(),
                payload_base64=base64.b64encode(raw).decode(),signature_hex=hmac.new(key,header+raw,hashlib.sha256).hexdigest())


def strict_json(raw):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('Duplicate JSON key')
            out[k]=v
        return out
    def invalid(value):raise ValueError('Non-standard JSON numeric constant')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)


class Ingestor:
    def __init__(self,path,keys,clock_skew_seconds=120,max_age_seconds=300,max_raw_rows=10000):
        if not keys or len(set(keys.values()))!=len(keys) or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',node) for node in keys):raise ValueError('Distinct keys and bounded node identifiers required')
        if any(not isinstance(k,bytes) or len(k)<32 for k in keys.values()):raise ValueError('Independent per-node keys must have ≥32 bytes')
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,check_same_thread=False);self.lock=threading.RLock();self.keys=dict(keys)
        self.skew,self.max_age,self.max_raw=clock_skew_seconds,max_age_seconds,max_raw_rows
        self.db.executescript('''CREATE TABLE IF NOT EXISTS raw_messages(id INTEGER PRIMARY KEY,received_utc TEXT,sha256 TEXT,bytes BLOB,status TEXT);
CREATE TABLE IF NOT EXISTS nonces(node_id TEXT,nonce TEXT,response TEXT,PRIMARY KEY(node_id,nonce));
CREATE TABLE IF NOT EXISTS observations(node_id TEXT,time_utc TEXT,channel TEXT,json TEXT,PRIMARY KEY(node_id,time_utc,channel));
CREATE TABLE IF NOT EXISTS health(node_id TEXT PRIMARY KEY,last_attempt TEXT,last_success TEXT,status TEXT,error TEXT);''')
    def close(self):self.db.close()
    def ingest(self,wire,received_at):
        if not isinstance(wire,bytes) or len(wire)>128000:return {'status':'REJECTED_RESOURCE_LIMIT','accepted':False}
        received=utc(received_at);trusted=None;nonce=None
        with self.lock,self.db:
            try:
                envelope=strict_json(wire)
                if set(envelope)!={'protocol','node_id','nonce','sent_at_utc','payload_base64','signature_hex'} or envelope['protocol']!='indra_hmac_v1':raise ValueError('Envelope schema')
                node=envelope['node_id'];nonce=envelope['nonce'];key=self.keys.get(node)
                if key is None or not isinstance(nonce,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}',nonce):raise ValueError('Unknown identity/nonce')
                sent=utc(envelope['sent_at_utc']);raw=base64.b64decode(envelope['payload_base64'],validate=True)
                expected=hmac.new(key,(node+'\n'+nonce+'\n'+envelope['sent_at_utc']+'\n').encode()+raw,hashlib.sha256).hexdigest()
                if not isinstance(envelope['signature_hex'],str) or not hmac.compare_digest(expected,envelope['signature_hex']):raise ValueError('Authentication failure')
                trusted=node
                message_sha=hashlib.sha256((node+'\n'+nonce+'\n'+envelope['sent_at_utc']+'\n').encode()+raw).hexdigest()
                if abs((received-sent).total_seconds())>self.skew:raise ValueError('Clock skew')
                cached=self.db.execute('SELECT response FROM nonces WHERE node_id=? AND nonce=?',(node,nonce)).fetchone()
                if cached:
                    previous=json.loads(cached[0])
                    if previous.get('message_sha256')!=message_sha:raise ValueError('Nonce reused with different signed payload')
                    return {**previous,'status':'DUPLICATE_RETRY','duplicate':True}
                payload=strict_json(raw)
                if set(payload)!={'schema_version','observations'} or payload['schema_version']!=VERSION:raise ValueError('Unsupported payload version')
                records=payload['observations']
                if not isinstance(records,list) or not 1<=len(records)<=64:raise ValueError('Observation budget')
                normalized=[]
                for record in records:
                    if not isinstance(record,dict):raise ValueError('Observation must be an object')
                    if record.get('node_id')!=node:raise ValueError('Spoofed observation identity')
                    stamp=utc(record['timestamp_utc'])
                    if stamp>received or (received-stamp).total_seconds()>self.max_age:raise ValueError('Future/stale observation clock')
                    normalized.append(observation(record,True,received.isoformat()))
                if len({(r['latitude'],r['longitude'],r['elevation_m']) for r in normalized})!=1:raise ValueError('Snapshot position/elevation mismatch')
                times={r['timestamp_utc'] for r in normalized}
                if len(times)!=1 or len({r['channel'] for r in normalized})!=len(normalized):raise ValueError('One unique-channel snapshot per packet')
                stamp=next(iter(times));last=self.db.execute('SELECT MAX(time_utc) FROM observations WHERE node_id=?',(node,)).fetchone()[0]
                if last is not None and utc(stamp)<=utc(last):raise ValueError('Out-of-order/duplicate timestamp')
                for r in normalized:self.db.execute('INSERT INTO observations VALUES (?,?,?,?)',(node,stamp,r['channel'],json.dumps(r,allow_nan=False)))
                complete={r['channel'] for r in normalized if r['quality_flag']=='valid' and r['value'] is not None}
                status='healthy' if set(CORE)<=complete else 'degraded'
                self.db.execute('INSERT INTO health VALUES (?,?,?,?,?) ON CONFLICT(node_id) DO UPDATE SET last_attempt=excluded.last_attempt,last_success=excluded.last_success,status=excluded.status,error=excluded.error',
                                (node,received.isoformat(),stamp,status,None if status=='healthy' else 'MISSING_OR_REJECTED_CORE'))
                result={'status':'ACCEPTED','accepted':True,'node_id':node,'observation_count':len(normalized),'health':status}
            except (ValueError,TypeError,KeyError,UnicodeError,binascii.Error) as exc:
                result={'status':'REJECTED_AUTH_OR_SCHEMA_OR_CLOCK','accepted':False,'reason':str(exc)}
                if trusted:
                    self.db.execute('INSERT INTO health VALUES (?,?,NULL,?,?) ON CONFLICT(node_id) DO UPDATE SET last_attempt=excluded.last_attempt,status=excluded.status,error=excluded.error',
                                    (trusted,received.isoformat(),'degraded',str(exc)))
            if trusted and nonce:
                result['message_sha256']=message_sha
                self.db.execute('INSERT OR IGNORE INTO nonces VALUES (?,?,?)',(trusted,nonce,json.dumps(result)))
            self.db.execute('INSERT INTO raw_messages(received_utc,sha256,bytes,status) VALUES (?,?,?,?)',
                            (received.isoformat(),hashlib.sha256(wire).hexdigest(),wire,result['status']))
            self.db.execute('DELETE FROM raw_messages WHERE id NOT IN (SELECT id FROM raw_messages ORDER BY id DESC LIMIT ?)',(self.max_raw,))
            return result
    def latest(self):
        with self.lock:
            rows=self.db.execute('SELECT json FROM observations o WHERE time_utc=(SELECT MAX(time_utc) FROM observations WHERE node_id=o.node_id)').fetchall()
        return [json.loads(r[0]) for r in rows]
    def health(self,reference_time):
        t=utc(reference_time);out=[]
        with self.lock:rows=self.db.execute('SELECT node_id,last_attempt,last_success,status,error FROM health').fetchall()
        for node,attempt,success,status,error in rows:
            age=None if success is None else (t-utc(success)).total_seconds()
            if age is None:status='unavailable'
            elif age<0:status='clock_skew'
            elif age>self.max_age:status='stale'
            out.append(dict(node_id=node,last_attempt_utc=attempt,last_success_utc=success,age_seconds=age,status=status,error=error))
        return out
