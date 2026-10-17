"""Run resumable translation clients against local Qwen services."""
import argparse,json,os,subprocess,sys,time,signal,urllib.request,urllib.error
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--decisions',type=Path,required=True);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--ports',default='31400,31401,31402,31403,31404,31405,31406,31407');p.add_argument('--concurrency',type=int,default=32);p.add_argument('--file-workers',type=int,choices=[1,2],default=2);p.add_argument('--subsets',default='',help='Comma-separated exact subset directory names');p.add_argument('--worker-id',type=int,default=1);a=p.parse_args()
 assert 1<=a.concurrency<=32 and a.worker_id>=0
 assert a.source.is_dir() and a.decisions.is_dir()
 ports=[int(x) for x in a.ports.split(',')];assert len(set(ports))==len(ports) and all(1<=x<=65535 for x in ports)
 if a.subsets:
  missing=[s for s in a.subsets.split(',') if not (a.source/s).is_dir()]
  if missing:p.error('Unknown source subsets: '+','.join(missing))
 d=a.work_dir.resolve();d.mkdir(parents=True,exist_ok=True);(d/'state').mkdir(exist_ok=True);(d/'logs').mkdir(exist_ok=True)
 configs={'translation-concurrency.json':{str(a.worker_id):a.concurrency},'translation-file-concurrency.json':{str(a.worker_id):a.file_workers},'model.json':{'repo':'Qwen/Qwen3.8-27B','served_model_name':'Qwen3.8-27B','dtype':'bfloat16','tensor_parallel_size':1,'enable_thinking':False}}
 # One supervisor owns this workspace configuration. Use separate work dirs for separate machines.
 for name,value in configs.items():
  path=d/name;temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));temp.replace(path)
 env={**os.environ,'OV_WORK_DIR':str(d),'OV_SOURCE':str(a.source.resolve()),'OV_DECISIONS':str(a.decisions.resolve()),'OV_SUBSETS':a.subsets,'SLURM_JOB_ID':str(a.worker_id)}
 children=[];logs=[]
 def stop(*_):raise SystemExit(0)
 signal.signal(signal.SIGTERM,stop)
 try:
  deadline=time.monotonic()+3600
  for port in ports:
   while True:
    try:
     with urllib.request.urlopen(f'http://127.0.0.1:{port}/v1/models',timeout=5) as response:models=json.load(response)
     if not any(m['id']=='Qwen3.8-27B' for m in models['data']):raise RuntimeError(f'Wrong model on port {port}')
     break
    except (OSError,ValueError):
     if time.monotonic()>deadline:raise TimeoutError(f'Model readiness timeout: {port}')
     time.sleep(5)
  for port in ports:
   log=(d/'logs'/f'translate-{port}.log').open('a');logs.append(log)
   children.append(subprocess.Popen([sys.executable,str(Path(__file__).with_name('translate.py')),str(port)],env=env,stdout=log,stderr=subprocess.STDOUT))
  while True:
   exits={port:c.poll() for port,c in zip(ports,children) if c.poll() is not None}
   if exits:raise RuntimeError(f'Worker exited: {exits}; inspect {d / "logs"}')
   time.sleep(10)
 finally:
  for c in children:
   if c.poll() is None:c.terminate()
  for c in children:
   try:c.wait(timeout=15)
   except subprocess.TimeoutExpired:c.kill();c.wait()
  for log in logs:log.close()
if __name__=='__main__':main()
