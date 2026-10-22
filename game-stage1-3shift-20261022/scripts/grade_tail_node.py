"""Retry the single unfinished review, retaining the original rubric and candidate."""
import hashlib, importlib.util, json, os, subprocess, sys, time
from pathlib import Path
import requests
D=Path(__file__).resolve().parent
assert os.environ['SLURM_JOB_ID']=='2733'
mode='thinking-sampled-t1-p1';label='game-stage1-3shift-1500';ident='benchmark-ai2d-2925'
candidate=next(json.loads(l) for l in (D/mode/(label+'.jsonl')).open() if json.loads(l).get('id')==ident)
runtime=json.loads((D/'status/judge-runtime.json').read_text());command=runtime['command'];name=command[command.index('--name')+1]
used=[int(x) for x in subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).split()]
assert max(used)<2000,used
source=(D/'scripts/judge.py').read_text().replace("'max_tokens':2200","'max_tokens':8192").replace("payload['max_tokens']=4400","payload['max_tokens']=16384")
module_path=D/'scripts/judge_tail_budget.py';module_path.write_text(source)
spec=importlib.util.spec_from_file_location('language_judge_tail',module_path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original_post=module.requests.post;attempts=[]
def post(*args,**kwargs):
    response=original_post(*args,**kwargs)
    try:raw=response.json()
    except ValueError:raw={'http_status':response.status_code,'text':response.text}
    attempts.append({'utc':time.time(),'max_tokens':kwargs.get('json',{}).get('max_tokens'),'raw_response':raw})
    (D/'status/grading-tail-native-attempts.json').write_text(json.dumps(attempts,ensure_ascii=False,indent=2))
    return response
module.requests.post=post
with (D/'logs/judge-tail-server.log').open('a') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+2400
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Tail judge exited '+str(process.returncode))
            try:
                r=requests.get('http://127.0.0.1:30240/v1/models',timeout=5)
                if r.ok and any(x['id']=='DeepSeek-V4.1-Flash' for x in r.json()['data']):break
            except requests.RequestException:pass
            time.sleep(5)
        else:raise RuntimeError('Tail judge readiness timeout')
        record=module.judge((mode,label,candidate))
        record['tail_retry']=True
        record['tail_budget_policy']={'initial':8192,'on_length':16384,'original_rubric_unchanged':True}
        with (D/'scores100'/(mode+'-'+label+'.jsonl')).open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
        assert record['status']=='ok',record
        assert record['candidate_sha256']==hashlib.sha256(json.dumps(candidate,sort_keys=True).encode()).hexdigest()
        (D/'status/grading-tail-verified.json').write_text(json.dumps({'utc':time.time(),'candidate_sha256':record['candidate_sha256'],'id':ident,'status':'ok','raw_candidate_unchanged':True},indent=2))
    finally:
        subprocess.run(['docker','stop','-t','20',name],stdout=subprocess.DEVNULL)
subprocess.run([sys.executable,str(D/'report.py')],check=True)
