"""Run resumable two-checkpoint batches under a cross-node exclusive claim."""
import atexit,datetime,hashlib,json,os,re,shutil,socket,subprocess,sys,time,traceback
from pathlib import Path
D=Path(__file__).resolve().parent;PY=sys.executable;JOB=os.environ['SLURM_JOB_ID'];HOST=socket.gethostname();EXISTING='--existing' in sys.argv
LOCK=D/'status/worker-lock';held=False;child=None

def write(p,data):
 tmp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(p)
def status(phase,**kw):
 write(D/'status'/('worker-'+JOB+'.json'),{'utc':time.time(),'job':JOB,'host':HOST,'phase':phase,**kw});print(phase,kw,flush=True)
def release():
 global held
 if held:
  try:
   owner=json.loads((LOCK/'owner.json').read_text());assert owner['job']==JOB and owner['pid']==os.getpid();(LOCK/'owner.json').unlink();LOCK.rmdir()
  finally:held=False
atexit.register(release)
def remaining_minutes():
 s=subprocess.check_output(['scontrol','show','job',JOB,'-o'],text=True);end=re.search(r'EndTime=(\S+)',s).group(1)
 return (datetime.datetime.fromisoformat(end).replace(tzinfo=datetime.timezone.utc).timestamp()-time.time())/60

def acquire():
 global held
 while True:
  if remaining_minutes()<105:status('lease_too_short_to_start_another_batch');return False
  try:
   LOCK.mkdir();held=True;write(LOCK/'owner.json',{'job':JOB,'host':HOST,'pid':os.getpid(),'utc':time.time()});return True
  except FileExistsError:
   try:
    owner=json.loads((LOCK/'owner.json').read_text());active=subprocess.check_output(['squeue','-h','-j',owner['job'],'-o','%T'],text=True).strip()
    if not active:
     terminal=subprocess.check_output(['sacct','-X','-j',owner['job'],'-n','-P','-o','State'],text=True).splitlines()
     if terminal and terminal[0].split('|')[0].split()[0] in ['COMPLETED','FAILED','CANCELLED','TIMEOUT','NODE_FAIL','PREEMPTED','OUT_OF_MEMORY']:
      # An exited allocation cannot have live GPU requests. Atomic rename elects one reclaiming worker.
      archived=LOCK.with_name('expired-worker-lock-'+str(time.time_ns()))
      try:LOCK.rename(archived)
      except FileNotFoundError:pass
      continue
   except (FileNotFoundError,json.JSONDecodeError):pass
   status('waiting_for_current_batch_lock');time.sleep(20)

def rows(p):
 out={}
 if p.exists():
  for line in p.open():
   if not line.strip():continue
   x=json.loads(line)
   if x.get('status')=='ok':out[x['id']]=x
 return out

def verify(B):
 plan=json.loads((B/'plan.json').read_text());counts=[]
 for item in plan['items']:
  for mode in plan['modes']:
   c=rows(B/mode/(item['label']+'.jsonl'));s=rows(B/'scores100'/(mode+'-'+item['label']+'.jsonl'))
   assert set(c)==set(s),(item['label'],mode,'grading coverage')
   assert all(s[i].get('candidate_sha256')==hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest() for i,r in c.items())
   counts.append({'model':item['label'],'mode':mode,'responses':len(c),'graded':len(s),'expected':246})
 return counts

try:
 status('starting',existing=EXISTING)
 while acquire():
  B=None
  try:
   batches=sorted((D/'batches').iterdir(),key=lambda p:int(p.name.split('-')[0]));B=next((p for p in batches if not (p/'status/batch-finished.json').exists()),None)
   if B is None:status('all_batches_finished');break
   used=[int(v) for v in subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).split()]
   assert len(used)==8 and max(used)<2000,('GPU conflict; preserve current workloads',used)
   modelroot=Path(json.loads((B/'plan.json').read_text())['model_root']);modelroot.mkdir(parents=True,exist_ok=True)
   if shutil.disk_usage(modelroot).free<48*1024**3:
    status('insufficient_local_storage',batch=B.name,free_bytes=shutil.disk_usage(modelroot).free);raise RuntimeError('Need48GiB free local storage; no unrelated data is deleted')
   attempts=rows(B/'status/attempts.jsonl')
   status('downloading',batch=B.name);write(D/'status/current-batch.json',{'utc':time.time(),'batch':B.name,'job':JOB,'host':HOST,'phase':'downloading'})
   with (B/'logs/download.log').open('a') as log:subprocess.run([PY,'-u',str(B/'download.py')],check=True,stdout=log,stderr=subprocess.STDOUT)
   status('evaluating_and_grading',batch=B.name);write(D/'status/current-batch.json',{'utc':time.time(),'batch':B.name,'job':JOB,'host':HOST,'phase':'evaluating_and_grading'})
   with (B/'logs/run.log').open('a') as log:subprocess.run([PY,'-u',str(B/'run_node.py')],check=True,stdout=log,stderr=subprocess.STDOUT)
   counts=verify(B);write(B/'status/batch-finished.json',{'utc':time.time(),'job':JOB,'host':HOST,'finished':True,'all_expected_answers':all(x['responses']==246 for x in counts),'counts':counts})
   status('batch_finished',batch=B.name,responses=sum(x['responses'] for x in counts),graded=sum(x['graded'] for x in counts))
   # Only evict this experiment's temporary, pinned-HF downloads after output/score verification.
   assert modelroot==Path('/opt/dlami/nvme/zhiyuan-game-2000plus-20261023/models')
   for item in json.loads((B/'plan.json').read_text())['items']:
    target=modelroot/item['label'];assert target.parent==modelroot
    if target.exists():shutil.rmtree(target)
   write(B/'status/temporary-weights-evicted.json',{'utc':time.time(),'raw_outputs_and_scores_sha_verified':True,'source_revisions_in_plan':True,'only_this_batch_download_cache_removed':True})
  except Exception:
   status('batch_error',batch=B.name if B else None,traceback=traceback.format_exc());raise
  finally:release()
  if EXISTING:
   continuation=json.loads((D/'status/continuation-submission.json').read_text())['job_id']
   state=subprocess.check_output(['squeue','-h','-j',str(continuation),'-o','%T'],text=True).strip()
   if state=='RUNNING':status('handoff_to_continuation',continuation_job=continuation);break
   if remaining_minutes()<110:status('existing_lease_handoff',remaining_minutes=remaining_minutes());break
except Exception:
 traceback.print_exc();sys.exit(1)
finally:release()
