"""An explicit assignment must not claim a global unassigned task or global completion."""
import asyncio,json,sys,tempfile,threading
from pathlib import Path
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import clean
import pyarrow as pa
import pyarrow.parquet as pq
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,value):
  raw=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):self.reply({'data':[{'id':clean.MODEL}]})
 def do_POST(self):
  self.rfile.read(int(self.headers['Content-Length']));verdict={**{k:True for k in clean.FLAGS},'confidence':1.0,'reason':'Fixture: arithmetic verified'}
  self.reply({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(verdict)}}],'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}})
def main():
 with tempfile.TemporaryDirectory() as root:
  root=Path(root);source=root/'source';source.mkdir();output=root/'output';dest=root/'clean'
  for s in ('assigned','other'):
   (source/s).mkdir();pq.write_table(pa.table({'messages':[[{'role':'user','content':'What is 1 + 1?'},{'role':'assistant','content':'2'}]]}),source/s/'data.parquet')
  (source/'canonical_index.json').write_text(json.dumps({'datasets':[{'canonical_name':s,'stats':{'output_rows':1}} for s in ('assigned','other')]}))
  args=SimpleNamespace(source=source,output=output,task_rows=256);clean.inventory(args);full=json.loads((output/'inventory.json').read_text());chosen=[t for t in full['tasks'] if t['subset']=='assigned'];assignment=root/'assignment.json';assignment.write_text(json.dumps({**full,'tasks':chosen,'rows':1,'subsets':1}))
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  # The worker includes one 30-second completion sweep.
  args=SimpleNamespace(source=source,output=output,clean=dest,cache=root/'cache',endpoint=f'http://127.0.0.1:{server.server_port}',job='assignment-test',rank=0,concurrency=2,only_task=None,first_deep=False,data_url=None,inventory=assignment)
  print('fixture',root,args.endpoint,flush=True)
  try:asyncio.run(asyncio.wait_for(clean.worker(args),timeout=90))
  finally:server.shutdown();server.server_close()
  assert (output/'tasks'/chosen[0]['key']/'done.json').exists()
  other=next(t for t in full['tasks'] if t['subset']=='other');assert not (output/'tasks'/other['key']).exists()
  assert not (output/'complete.json').exists()
  marker=json.loads((output/'complete-assignment-test.json').read_text());assert marker['rows']==1 and marker['tasks']==1
  assert pq.read_table(dest/'assigned'/f'{chosen[0]["key"]}.parquet').num_rows==1
 print('PASS: assigned task only; shared output preserved; no global completion claim')
if __name__=='__main__':main()
