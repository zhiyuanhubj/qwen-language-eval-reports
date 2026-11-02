"""Check only this evaluation's services; pending GPU jobs are healthy waiting."""
import fcntl,json,os,subprocess,time
from pathlib import Path

D=Path(__file__).resolve().parent
REPORT='qwen-game-12000-report-20261102.service'
QUEUE='qwen-game-12000-queue-20261102.service'

def read(name):
 p=D/'status'/name
 return json.loads(p.read_text()) if p.exists() else {}

def run(args):
 return subprocess.run(args,check=True,text=True,capture_output=True,timeout=30).stdout.strip()

def recovery_action(unit,active,stale,terminal,needs_attention):
 if terminal or (unit==QUEUE and needs_attention):return None
 if active not in ('active','activating','deactivating'):return 'start'
 if active=='active' and stale:return 'restart'
 return None

def main():
 now=time.time();progress=read('progress.json');continuation=read('continuation-20261102.json');heartbeat=read('report-heartbeat.json')
 terminal=progress.get('terminal',False);needs_attention=continuation.get('state')=='NEEDS_ATTENTION'
 report_alive=max(heartbeat.get('loop_started_utc',0),heartbeat.get('started_utc',0))
 queue_alive=continuation.get('updated_utc',now)
 states={};actions=[];warnings=[]
 for unit,stale in [(REPORT,bool(report_alive and now-report_alive>900)),(QUEUE,now-queue_alive>300)]:
  active=run(['systemctl','--user','show',unit,'--property=ActiveState','--value']);states[unit]=active
  action=recovery_action(unit,active,stale,terminal,needs_attention)
  if action:
   run(['systemctl','--user',action,unit]);actions.append({'unit':unit,'action':action,'utc':now})
 if needs_attention:warnings.append('Repeated allocations made no batch progress; inspect preserved logs before resuming.')
 if heartbeat.get('last_error'):warnings.append(heartbeat['last_error'])
 last_publish=heartbeat.get('last_publish_utc')
 if not terminal and last_publish and now-last_publish>600:warnings.append('GitHub has not synchronized successfully for over 10 minutes.')
 record={'utc':now,'terminal':terminal,'services':states,'actions':actions,'warnings':warnings,'scheduler':progress.get('scheduler'),'last_check_utc':heartbeat.get('last_check_utc'),'last_publish_utc':last_publish,'last_publish_commit':heartbeat.get('last_publish_commit'),'automatic_chat_notifications':False,'detection_interval_seconds':30,'github_publish_interval_seconds':180,'watchdog_interval_seconds':60}
 path=D/'status/monitor-health.json';tmp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp');tmp.write_text(json.dumps(record,ensure_ascii=False,indent=2));tmp.replace(path)
 print(json.dumps(record,ensure_ascii=False))

if __name__=='__main__':
 with (D/'status/monitor-health.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);main()
