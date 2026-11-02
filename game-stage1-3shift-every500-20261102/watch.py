"""Publish fixed-plan progress and raw evidence without allocating any GPU."""
import gzip,hashlib,json,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
D=Path(__file__).resolve().parent;W=Path('/fsx/home/zhiyuan/.cache/qwen-game-every500-publish-20261102');DEST=W/D.name

def command(args,**kw):return subprocess.run(args,check=True,text=True,capture_output=True,**kw)
def write(p,value):
 tmp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2));tmp.replace(p)
def publish():
 command([sys.executable,str(D/'analyze_language.py')])
 assert W.name=='qwen-game-every500-publish-20261102' and (W/'.git').is_file()
 command(['git','fetch','origin','main'],cwd=W);command(['git','pull','--rebase','origin','main'],cwd=W);DEST.mkdir(exist_ok=True)
 for name in ['plan.json','authorization.json','summary.json','report.html','report-v2-modes.html','progress.md','language-analysis.json','language-analysis.md','continuation.sbatch']:
  shutil.copy2(D/name,DEST/name)
 for p in [*D.glob('*.py'),*D.glob('scripts/*.py'),*D.glob('status/*.json'),*D.glob('batches/*/plan.json'),*D.glob('batches/*/*.py'),*D.glob('batches/*/scripts/*.py'),*D.glob('batches/*/status/*.json')]:
  if p.is_symlink():continue
  target=DEST/p.relative_to(D);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 evidence=DEST/'evidence';evidence.mkdir(exist_ok=True);manifest=evidence/'manifest.json';previous={}
 if manifest.exists():previous={r['path']:r for r in json.loads(manifest.read_text()).get('files',[])}
 plan=json.loads((D/'plan.json').read_text());sources=[]
 for mode in plan['modes']:sources.extend((D/mode).glob('*.json*'))
 sources.extend((D/'scores100').glob('*.json*'));sources.extend((D/'templates').rglob('*.json'));sources.extend((D/'templates').rglob('*.jinja'));sources.extend((D/'logs').glob('*.log'));sources.extend(D.glob('batches/*/logs/*.log'))
 files=[]
 for p in sources:
  rel=str(p.relative_to(D))+'.gz';target=evidence/rel;before=p.stat();cached=previous.get(rel)
  if cached and cached.get('stat_size')==before.st_size and cached.get('stat_mtime_ns')==before.st_mtime_ns and target.exists():files.append(cached);continue
  data=p.read_bytes();after=p.stat()
  if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):continue
  if p.suffix=='.jsonl' and data and not data.endswith(b'\n'):continue
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(gzip.compress(data,compresslevel=6,mtime=0));files.append({'path':rel,'uncompressed_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'stat_size':before.st_size,'stat_mtime_ns':before.st_mtime_ns})
 suite=Path(plan['suite'])
 for name in ['prompts.jsonl','manifest.json','benchmark-answers.json']:
  data=(suite/name).read_bytes();(evidence/(name+'.gz')).write_bytes(gzip.compress(data,mtime=0));files.append({'path':name+'.gz','bytes':len(data),'uncompressed_sha256':hashlib.sha256(data).hexdigest()})
 write(manifest,{'utc':time.time(),'files':files})
 (DEST/'README.md').write_text((D/'README.md').read_text())
 root=W/'README.md';text=root.read_text().replace('新五个checkpoint续测已准备，尚未提交GPU作业','新五个checkpoint续测已提交独立GPU队列，阶段以续测进度为准').replace('4000/4500/5000/5500/6000报告与详细分析','每500step至9500的报告与详细分析');root.write_text(text);marker='<!-- game-every500-latest -->'
 if marker not in text:
  first,sep,rest=text.partition('\n');root.write_text(first+sep+'\n'+marker+'\n**Game Stage1每500step新评测：** [每500step至9500的报告与详细分析](game-stage1-3shift-every500-20261026/README.md) · [实时进度](game-stage1-3shift-every500-20261026/progress.md)。旧500–3500复用。\n'+rest)
 command(['git','add','--','README.md',D.name],cwd=W)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=W).returncode:
  command(['git','commit','-m','Update GameStage1 every500step evaluation and detailed evidence'],cwd=W);command(['git','push','origin','HEAD:main'],cwd=W)

last_publish=0
while True:
 try:
  command([sys.executable,str(D/'report.py')]);summary=json.loads((D/'summary.json').read_text());batches=sorted((D/'batches').iterdir());finished=[b.name for b in batches if (b/'status/batch-finished.json').exists()];progress={'utc':time.time(),'responses':sum(r['responses'] for r in summary['results']),'graded':sum(r['graded'] for r in summary['results']),'expected':json.loads((D/'plan.json').read_text())['expected_responses'],'reused_steps':json.loads((D/'plan.json').read_text())['reused_steps'],'requested_grid_expected':json.loads((D/'plan.json').read_text())['requested_grid_responses'],'finished_batches':finished,'total_batches':len(batches),'terminal':len(finished)==len(batches)}
  for name in ['current-batch','continuation-submission','current-allocation']:
   p=D/'status'/(name+'.json')
   if p.exists():progress[name.replace('-','_')]=json.loads(p.read_text())
  continuation=D/'status/continuation-20261102.json'
  if continuation.exists():progress['continuation_20261102']=json.loads(continuation.read_text())
  jobid=progress['current_allocation']['job_id']
  queue=command(['squeue','-h','-j',str(jobid),'-o','%T|%R']).stdout.strip()
  progress['scheduler']=queue or command(['sacct','-X','-j',str(jobid),'-n','-P','-o','State']).stdout.strip()
  if progress.get('current_batch'):
   bp=D/'batches'/progress['current_batch']['batch']/'status/allocation.json'
   if bp.exists():progress['batch_allocation_status']=json.loads(bp.read_text())
  write(D/'status/progress.json',progress)
  readable=json.loads(command([sys.executable,str(D/'write_progress.py')]).stdout)
  if time.time()-last_publish>=180 or progress['terminal'] or readable['major_update']:publish();last_publish=time.time()
  print(json.dumps(progress),flush=True)
  if progress['terminal']:break
 except Exception:traceback.print_exc()
 time.sleep(30)
