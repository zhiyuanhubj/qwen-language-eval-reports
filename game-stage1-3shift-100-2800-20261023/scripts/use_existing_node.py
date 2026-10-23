import json, subprocess, time, traceback
from pathlib import Path
D=Path(__file__).resolve().parent
PY='/fsx/home/zhiyuan/miniconda3/envs/megatron-sft/bin/python'
receipt={'utc':time.time(),'job':2733,'language_returncode':None,'beam_restore_requested':False}
try:
    result=subprocess.run(['srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c32','--gres=none','--immediate=30','--time=420',PY,'-u',str(D/'run_node.py')])
    receipt['language_returncode']=result.returncode
finally:
    # Clean up only this evaluation's containers before restoring the recorded Beam service.
    remote="import subprocess; names=subprocess.check_output(['docker','ps','-q','--filter','label=zhiyuan.game-language-job=2733'],text=True).split(); [subprocess.run(['docker','stop','-t','20',n],check=True) for n in names]"
    cleaned=subprocess.run(['srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c1','--gres=none','--immediate=30','python3','-c',remote])
    receipt['cleanup_returncode']=cleaned.returncode
    if cleaned.returncode==0:
        p=subprocess.run(['systemd-run','--user','--unit=beam-bf16-restore-after-language-100-2800-20261023',
            '--property=StandardOutput=append:'+str(D/'logs/beam-restore-controller.log'),
            '--property=StandardError=append:'+str(D/'logs/beam-restore-controller.log'),
            'srun','--jobid=2733','--overlap','--exact','-N1','-n1','-c32','--gres=none','--immediate=30',
            PY,'-u',str(D/'restore_beam.py')])
        receipt['beam_restore_requested']=p.returncode==0
    receipt['finished_utc']=time.time()
    (D/'status/task-exit.json').write_text(json.dumps(receipt,indent=2)+'\n')
