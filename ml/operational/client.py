"""Bounded host transport; keys injected by environment, never serialized/logged."""
import json
import time
import uuid
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

from ml.operational.contracts import canonical_bytes,now_utc
from ml.operational.ingestion import sign


def send(url,node_id,key,records,attempts=3,timeout_seconds=3,opener=urlopen,sleeper=time.sleep):
    parsed=urlparse(url)
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ['127.0.0.1','localhost','::1']):raise ValueError('Remote transport requires HTTPS; no certificate bypass')
    if not 1<=attempts<=5 or not 0<timeout_seconds<=10:raise ValueError('Bounded retry/timeout required')
    packet=sign(node_id,key,uuid.uuid4().hex,now_utc(),records);body=canonical_bytes(packet)
    for attempt in range(attempts):
        try:
            request=Request(url,body,{'Content-Type':'application/json'},method='POST')
            with opener(request,timeout=timeout_seconds) as response:
                raw=response.read(64001)
                if len(raw)>64000:raise ValueError('Response budget')
                result=json.loads(raw)
                return {'status':'TRANSPORT_COMPLETE','attempts':attempt+1,'ack':result}
        except HTTPError as exc:
            if 400<=exc.code<500:return {'status':'AUTH_OR_INPUT_REJECTED','http_status':exc.code,'attempts':attempt+1}
        except (TimeoutError,URLError,OSError):pass
        if attempt+1<attempts:sleeper(min(.25*2**attempt,2.))
    return {'status':'TRANSPORT_UNAVAILABLE','attempts':attempts,'last_success':None}
