import argparse,concurrent.futures,json,re,subprocess,time
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--jobs',type=int,nargs='+',required=True)
parser.add_argument('--state',type=Path,default=Path('inference-progress.json'))
parser.add_argument('--interval',type=int,default=60)
parser.add_argument('--stalled-seconds',type=int,default=180)
args=parser.parse_args()
assert args.interval>0 and args.stalled_seconds>0
state_path=args.state;state_path.parent.mkdir(parents=True,exist_ok=True)
REMOTE=r'''import urllib.request,json,subprocess,re,time
text=urllib.request.urlopen('http://127.0.0.1:30240/metrics',timeout=10).read().decode()
def total(name):
 return sum(float(line.rsplit(' ',1)[1]) for line in text.splitlines() if line.startswith(name+'{'))
container=json.loads(subprocess.check_output(['docker','inspect','llava-v41-quality-native-dp2'],text=True))[0]
gpus=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,power.draw','--format=csv,noheader,nounits'],text=True)
rows=[[float(v.strip()) for v in line.split(',')] for line in gpus.splitlines()]
print(json.dumps({'tokens':total('vllm:generation_tokens_total'),'running':total('vllm:num_requests_running'),'started':container['State']['StartedAt'],'gpu_util_mean':sum(r[0] for r in rows)/len(rows),'gpu_power_mean':sum(r[1] for r in rows)/len(rows)}))'''
def poll(job):
 result=subprocess.run(['srun',f'--jobid={job}','--overlap','--exact','-N1','-n1','-c1','--gres=none','--immediate=15','python3','-c',REMOTE],capture_output=True,text=True,timeout=35)
 if result.returncode:raise RuntimeError('inference poll failed, exit '+str(result.returncode))
 return json.loads(result.stdout.strip().splitlines()[-1])
previous={}
if state_path.exists():
 try:previous=json.loads(state_path.read_text()).get('nodes',{})
 except (ValueError,OSError):pass
while True:
 output={'utc':time.time(),'nodes':{},'alerts':[]}
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(poll,job):str(job) for job in args.jobs}
  for future in concurrent.futures.as_completed(futures):
   job=futures[future];old=previous.get(job,{})
   try:
    current=future.result();now=time.time()
    same=current.get('started')==old.get('started') and current['tokens']==old.get('tokens')
    current['last_token_change']=old.get('last_token_change',now) if same else now
    current['unchanged_seconds']=round(now-current['last_token_change']);current['observed_utc']=now
    if current['running']>0 and current['unchanged_seconds']>=args.stalled_seconds:output['alerts'].append('GENERATION_STALLED '+job+' '+str(current['unchanged_seconds'])+'s')
    output['nodes'][job]=current
   except Exception as error:
    output['nodes'][job]={**old,'poll_error':type(error).__name__,'failed_poll_utc':time.time()};output['alerts'].append('POLL_FAILED '+job)
 tmp=state_path.with_suffix('.tmp');tmp.write_text(json.dumps(output,indent=2)+'\n');tmp.replace(state_path);previous=output['nodes']
 time.sleep(args.interval)
