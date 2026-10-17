import concurrent.futures,json,os,sys,tempfile,threading
from pathlib import Path
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from split_subsets import split
from serve import commands

def main():
 m={'tasks':[{'key':f'{s}-{i}','subset':s,'rows':i+1,'file':s+'/a.parquet'} for s in ['a','b','c'] for i in range(3)],'policy_sha256':'same','ruleset':'same'}
 plans=split(m,2);keys=[t['key'] for p in plans for t in p['tasks']]
 assert len(keys)==len(set(keys))==9 and sum(p['rows'] for p in plans)==18
 assert not ({t['subset'] for t in plans[0]['tasks']}&{t['subset'] for t in plans[1]['tasks']})
 try:split(m,2,['missing'])
 except ValueError:pass
 else:raise AssertionError('Unknown subset accepted')
 a=SimpleNamespace(role='translate',gpus='0,1,2,3,4,5,6,7',max_num_seqs=32,model_path=Path('/models/qwen'),image='image',name='test',port=31400)
 cs=commands(a);assert len(cs)==8
 assert [int(c[c.index('--port')+1]) for c in cs]==list(range(31400,31408))
 assert all(c[c.index('--max-num-seqs')+1]=='32' and c[c.index('--tensor-parallel-size')+1]=='1' for c in cs)
 a.role='clean';a.port=30240;c=commands(a)[0];assert c[c.index('--tensor-parallel-size')+1]=='4' and c[c.index('--data-parallel-size')+1]=='2'
 with tempfile.TemporaryDirectory() as tmp:
  d=Path(tmp);os.environ['OV_WORK_DIR']=str(d/'work');os.environ['OV_SOURCE']=str(d/'source');os.environ['OV_DECISIONS']=str(d/'decisions');os.environ['SLURM_JOB_ID']='1'
  import translate as t
  import pyarrow as pa
  import pyarrow.parquet as pq
  class Handler(BaseHTTPRequestHandler):
   calls=0
   def log_message(self,*args):pass
   def do_POST(self):
    type(self).calls+=1;body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert body['chat_template_kwargs']['enable_thinking'] is False
    response={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'messages':[{'role':'user','content':'汽车是什么颜色的？'},{'role':'assistant','content':'汽车是红色的。'}]},ensure_ascii=False)}}]}
    data=json.dumps(response).encode();self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   (t.D/'model.json').write_text('{}');t.SOURCE.mkdir(parents=True);t.DECISIONS.mkdir(parents=True)
   messages=[{'role':'user','content':'What color is the car?'},{'role':'assistant','content':'The car is red.'}];paths=[]
   for i in range(2):
    p=t.SOURCE/'sample'/f'{i}.parquet';p.parent.mkdir(exist_ok=True);pq.write_table(pa.table({'messages':[messages,messages],'image':[b'unchanged-0',b'unchanged-1']}),p);paths.append(p)
    t.atomic(t.DECISIONS/str(i)/'done.json',{'keep_rows':[0,1],'file':f'sample/{i}.parquet','unresolved_errors':0})
   with concurrent.futures.ThreadPoolExecutor(2) as pool:
    t.ROW_POOL=pool;assert t.process_stream([(p,False) for p in paths],server.server_port,'fresh',2)==2
   assert Handler.calls==4
   for p in paths:
    result=pq.read_table(t.D/'translated'/p.relative_to(t.SOURCE));assert result['image'].to_pylist()==[b'unchanged-0',b'unchanged-1'];assert result.num_rows==2
    assert t.process(p,server.server_port) is None
   assert Handler.calls==4,'Resume repeated completed requests'
  finally:server.shutdown();server.server_close()
 print('PASS: subset partition, TP/DP commands, local HTTP translation, cross-file output, image preservation, resume')
if __name__=='__main__':main()
