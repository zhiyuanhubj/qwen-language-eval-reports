import json,os,subprocess,sys,time
from pathlib import Path
import requests
D=Path(__file__).resolve().parent
assert os.environ['SLURM_JOB_ID']=='2733'
command=json.loads((D/'status/judge-runtime.json').read_text())['command']
for flag,value in [('--tensor-parallel-size','8'),('--data-parallel-size','1'),('--max-num-seqs','16')]:command[command.index(flag)+1]=value
i=command.index('--speculative-config');del command[i:i+2];command.append('--enforce-eager')
name=command[command.index('--name')+1]
(D/'status/grading-tail-structured-runtime.json').write_text(json.dumps({'utc':time.time(),'command':command,'note':'Same DeepSeek model weights and rubric; single-case TP8 DP1 eager serving, bounded JSON explanation/evidence. Original scores and candidate retained.'},indent=2))
with (D/'logs/judge-tail-structured-server.log').open('a') as log:
 p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
 try:
  deadline=time.monotonic()+2400
  while time.monotonic()<deadline:
   if p.poll() is not None:raise RuntimeError('Judge exited '+str(p.returncode))
   try:
    r=requests.get('http://127.0.0.1:30240/v1/models',timeout=5)
    if r.ok and any(x['id']=='DeepSeek-V4.1-Flash' for x in r.json()['data']):break
   except requests.RequestException:pass
   time.sleep(5)
  else:raise RuntimeError('Judge readiness timeout')
  subprocess.run([sys.executable,str(D/'grade_tail_structured_node.py')],check=True)
 finally:subprocess.run(['docker','stop','-t','20',name],stdout=subprocess.DEVNULL)
