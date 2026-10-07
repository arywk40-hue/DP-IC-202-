"""Explicit localhost ingestion service; use TLS proxy for any remote transport."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

from ml.operational.contracts import now_utc
from ml.operational.ingestion import Ingestor,strict_json


def keys_from_env(name='INDRA_NODE_KEYS_JSON'):
    value=os.environ.get(name)
    if not value:raise ValueError('Per-node key environment is required; no default credentials')
    try:return {node:bytes.fromhex(key) for node,key in json.loads(value).items()}
    except (ValueError,TypeError,AttributeError):raise ValueError('Invalid key configuration; values redacted') from None


def serve(store,host='127.0.0.1',port=8767):
    if host not in ['127.0.0.1','::1','localhost']:raise ValueError('Bind locally and use an authenticated TLS/private-network proxy; no default public exposure')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass  # No raw packet/key/location stdout logs.
        def reply(self,status,payload):
            body=json.dumps(payload,allow_nan=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/health':self.reply(200,{'nodes':store.health(now_utc()),'disaster_outputs':'DISABLED'})
            else:self.reply(404,{'status':'NOT_FOUND'})
        def do_POST(self):
            if self.path!='/ingest':self.reply(404,{'status':'NOT_FOUND'});return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=128000:raise ValueError('Message size')
                self.connection.settimeout(3)
                body=self.rfile.read(size)
                if len(body)!=size:raise ValueError('Truncated message')
                strict_json(body)
                result=store.ingest(body,now_utc());self.reply(200 if result.get('accepted') else 400,result)
            except (ValueError,TimeoutError,OSError):self.reply(400,{'status':'REJECTED_MALFORMED_OR_TIMEOUT'})
    return ThreadingHTTPServer((host,port),Handler)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',required=True);p.add_argument('--port',type=int,default=8767);a=p.parse_args()
    store=Ingestor(a.database,keys_from_env())
    try:serve(store,port=a.port).serve_forever()
    finally:store.close()
