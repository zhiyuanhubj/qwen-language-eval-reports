import json,subprocess,time
from pathlib import Path
D=Path(__file__).resolve().parent
PY='/fsx/home/zhiyuan/miniconda3/envs/megatron-sft/bin/python'
base=['srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c1','--gres=none','--immediate=20']
def status(phase,**kw):
 p=D/'status/grading-tail.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps({'utc':time.time(),'phase':phase,'job':2733,**kw},indent=2)+'\n');tmp.replace(p)
status('starting_tail_review')
result=None
try:
    status('grading_one_case')
    result=subprocess.run(['srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c32','--gres=none','--immediate=30','--time=60',PY,'-u',str(D/'grade_tail_restart_node.py')])
finally:
    cleanup="import subprocess; names=subprocess.check_output(['docker','ps','-q','--filter','label=zhiyuan.game-language-job=2733'],text=True).split(); [subprocess.run(['docker','stop','-t','20',n],check=True) for n in names]"
    subprocess.run(base+['python3','-c',cleanup],check=True)
    restored=subprocess.run(['systemd-run','--user','--unit=beam-bf16-final-restore-2733-20261023',
        '--property=StandardOutput=append:'+str(D/'logs/beam-restore-tail-controller.log'),
        '--property=StandardError=append:'+str(D/'logs/beam-restore-tail-controller.log'),
        'srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c32','--gres=none','--immediate=30',PY,'-u',str(D/'restore_beam.py')])
    status('finished' if result and result.returncode==0 else 'failed',review_returncode=result.returncode if result else None,beam_restore_requested=restored.returncode==0)
