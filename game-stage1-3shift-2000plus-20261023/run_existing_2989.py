"""Use the user-reassigned owned node; restore its recorded Muse runtime afterwards."""
import json,subprocess,time
from pathlib import Path
D=Path(__file__).resolve().parent;H=Path('/fsx/home/zhiyuan/.private/qwen-language-node-handoff-20261024');PY='/fsx/home/zhiyuan/miniconda3/envs/megatron-sft/bin/python'
r={'started_utc':time.time(),'job':2989,'worker_returncode':None}
try:
 p=subprocess.run(['srun','--jobid=2989','--overlap','--exact','-N1','-n1','-c64','--gres=none','--immediate=30',PY,'-u',str(D/'worker.py')]);r['worker_returncode']=p.returncode
finally:
 code="import json,subprocess; names=subprocess.check_output(['docker','ps','-q','--filter','label=zhiyuan.game-language-experiment=game-stage1-3shift-2000plus-20261023'],text=True).split(); [subprocess.run(['docker','stop','-t','20',n],check=True) for n in names]"
 cleaned=subprocess.run(['srun','--jobid=2989','--overlap','--exact','-N1','-n1','-c1','--gres=none','--immediate=30','python3','-c',code]);r['cleanup_returncode']=cleaned.returncode
 if cleaned.returncode==0:
  restore=subprocess.run(['systemd-run','--user','--unit=muse-pro-2989-restore-after-qwen-20261024','--property=StandardOutput=append:'+str(H/'restore-controller.log'),'--property=StandardError=append:'+str(H/'restore-controller.log'),'srun','--jobid=2989','--overlap','--exact','-N1','-n1','-c48','--gres=none','--immediate=30',PY,'-u',str(H/'restore_muse_and_continue.py')]);r['muse_restore_requested']=restore.returncode==0
 r['finished_utc']=time.time();(D/'status/existing-2989-exit.json').write_text(json.dumps(r,indent=2))
