"""One queued allocation at a time; resume remaining batches after short backfill leases."""
import fcntl,json,subprocess,time,traceback
from pathlib import Path
D=Path(__file__).resolve().parent;F=D/'status/continuation-20261029.json'

def write(p,data):
 tmp=p.with_suffix('.supervisor.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(p)
def finished():return [p.name for p in (D/'batches').iterdir() if (p/'status/batch-finished.json').exists()]
def all_done():return len(finished())==len(list((D/'batches').iterdir()))
def state(**kw):
 data=json.loads(F.read_text());data.update(kw,updated_utc=time.time());write(F,data)
with (D/'status/queue-supervisor.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);stalls=0
 while not all_done():
  data=json.loads(F.read_text());job=data.get('active_job');before=set(finished());active=False
  if job:
   p=subprocess.run(['squeue','-h','-j',str(job),'-o','%T'],text=True,capture_output=True);active=bool(p.stdout.strip())
  if not active:
   p=subprocess.run(['sbatch','--parsable',str(D/'continuation.sbatch')],check=True,text=True,capture_output=True);job=int(p.stdout.strip().split(';')[0]);history=data.get('allocation_history',[]);history.append({'job_id':job,'submitted_utc':time.time(),'already_finished_batches':sorted(before)})
   state(active_job=job,state='PENDING',allocation_history=history,public_Muse_API_untouched=True)
   write(D/'status/current-allocation.json',{'utc':time.time(),'job_id':job,'existing_owned_allocation':False,'dedicated_evaluation_allocation':True,'requested_nodes':1,'walltime_hours':8,'backfill_min_hours':2,'api_node2989_untouched':True})
  while True:
   p=subprocess.run(['squeue','-h','-j',str(job),'-o','%T|%R'],text=True,capture_output=True);queue=p.stdout.strip()
   if not queue:break
   state(active_job=job,state=queue.split('|')[0],scheduler=queue)
   if all_done():break
   time.sleep(30)
  if all_done():state(state='COMPLETE',completed_batches=finished());break
  acct=subprocess.run(['sacct','-X','-j',str(job),'-n','-P','-o','State'],text=True,capture_output=True).stdout.strip();advanced=set(finished())-before;stalls=0 if advanced else stalls+1
  state(state='CONTINUING' if stalls<3 else 'NEEDS_ATTENTION',last_allocation_state=acct,consecutive_allocations_without_batch_completion=stalls,active_job=None)
  if stalls>=3:break
  time.sleep(10)
