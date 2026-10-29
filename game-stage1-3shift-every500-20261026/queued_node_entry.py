"""Allocation-scoped wrapper; clean up only this job's evaluation containers."""
import concurrent.futures,json,os,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;JOB=os.environ['SLURM_JOB_ID'];restart=os.environ.get('SLURM_RESTART_COUNT','0');child=None;started=time.time();rc=None

def terminate(*_):raise SystemExit('allocation termination')
signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
try:
 child=subprocess.Popen([sys.executable,'-u',str(D/'worker.py')]);rc=child.wait()
finally:
 if child is not None and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:child.kill()
 cmd=['docker','--host=unix:///var/run/docker.sock'];p=subprocess.run(cmd+['ps','-q','--filter','label=zhiyuan.game-language-experiment=game-stage1-3shift-every500-20261026','--filter','label=zhiyuan.game-language-job='+JOB],text=True,capture_output=True)
 names=p.stdout.split() if p.returncode==0 else []
 def stop(name):
  r=subprocess.run(cmd+['stop','-t','5',name],capture_output=True,timeout=15)
  if r.returncode:subprocess.run(cmd+['kill',name],capture_output=True,timeout=10)
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(stop,names))
 (D/'status'/f'queued-exit-{JOB}-{restart}.json').write_text(json.dumps({'started_utc':started,'finished_utc':time.time(),'job':JOB,'restart_count':restart,'worker_returncode':rc,'own_containers_cleaned':names,'public_Muse_API_untouched':True},indent=2))
raise SystemExit(rc or 0)
