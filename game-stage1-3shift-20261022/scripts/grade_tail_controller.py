"""Wait for the borrowed node to be idle; review one case, then restore Beam."""
import json, subprocess, time
from pathlib import Path
D=Path(__file__).resolve().parent
PY='/fsx/home/zhiyuan/miniconda3/envs/megatron-sft/bin/python'
def status(phase,**kw):
    p=D/'status/grading-tail.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps({'utc':time.time(),'phase':phase,'job':2733,**kw},indent=2)+'\n');tmp.replace(p)
remote=r'''import subprocess,json
x=json.loads(subprocess.check_output(['docker','inspect','zhiyuan-beam-bf16-2733'],text=True))[0]
assert x['Config']['Labels'].get('zhiyuan.task')=='beam-benchmark-20261018'
connections=subprocess.run(['ss','-Hnt','state','established','sport','=',':31328'],capture_output=True,text=True).stdout
p=subprocess.run(['docker','logs','--since','5m','--tail','1000','zhiyuan-beam-bf16-2733'],capture_output=True,text=True)
logs=p.stdout+'\n'+p.stderr
activity=any('chat/completions' in l or 'Decode batch' in l or 'Prefill batch' in l for l in logs.splitlines())
used=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu','--format=csv,noheader,nounits'],text=True)
print(json.dumps({'idle':not connections.strip() and not activity and max(int(x) for x in used.split())==0,'connections':len(connections.splitlines()),'recent_generation':activity}))'''
base=['srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c1','--gres=none','--immediate=20']
status('waiting_for_beam_idle')
while True:
    p=subprocess.run(base+['python3','-c',remote],capture_output=True,text=True,timeout=40)
    if p.returncode==0:
        observation=json.loads(p.stdout.strip().splitlines()[-1]);status('waiting_for_beam_idle',observation=observation)
        if observation['idle']:break
    time.sleep(30)
status('starting_tail_review')
result=None
try:
    subprocess.run(['systemctl','--user','stop','beam-bf16-restore-after-language-2733-20261022.service'],check=True)
    subprocess.run(base+['docker','stop','-t','30','zhiyuan-beam-bf16-2733'],check=False)
    status('grading_one_case')
    result=subprocess.run(['srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c32','--gres=none','--immediate=30','--time=60',PY,'-u',str(D/'grade_tail_node.py')])
finally:
    cleanup="import subprocess; names=subprocess.check_output(['docker','ps','-q','--filter','label=zhiyuan.game-language-job=2733'],text=True).split(); [subprocess.run(['docker','stop','-t','20',n],check=True) for n in names]"
    subprocess.run(base+['python3','-c',cleanup],check=True)
    restored=subprocess.run(['systemd-run','--user','--unit=beam-bf16-restore-after-language-tail-2733-20261022',
        '--property=StandardOutput=append:'+str(D/'logs/beam-restore-tail-controller.log'),
        '--property=StandardError=append:'+str(D/'logs/beam-restore-tail-controller.log'),
        'srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c32','--gres=none','--immediate=30',PY,'-u',str(D/'restore_beam.py')])
    status('finished' if result and result.returncode==0 else 'failed',review_returncode=result.returncode if result else None,beam_restore_requested=restored.returncode==0)
