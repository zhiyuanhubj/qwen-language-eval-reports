"""Publish fixed-plan progress and raw evidence without allocating any GPU."""
import gzip,hashlib,json,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
D=Path(__file__).resolve().parent;W=Path('/fsx/home/zhiyuan/.cache/qwen-game-2000plus-publish-20261023');DEST=W/D.name

def command(args,**kw):return subprocess.run(args,check=True,text=True,capture_output=True,**kw)
def write(p,value):
 tmp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2));tmp.replace(p)
def publish():
 assert W.name=='qwen-game-2000plus-publish-20261023' and (W/'.git').is_file()
 command(['git','fetch','origin','main'],cwd=W);command(['git','reset','--hard','origin/main'],cwd=W);DEST.mkdir(exist_ok=True)
 for name in ['plan.json','authorization.json','summary.json','report.html','report-v2-modes.html','progress.md','run.sbatch']:
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
 (DEST/'README.md').write_text('''# Stage1-3Shift：2000–3800 每100step

[下载 V2 对照报告](report-v2-modes.html) · [实时可读进度](progress.md) · [进度JSON](status/progress.json) · [固定计划与HF版本](plan.json) · [原始回答、评分、题目及日志](evidence/manifest.json)

范围完整包含2000至3800每100step，共19个checkpoint；3300、3400、3500、3600、3700已补齐计划。2800直接复用之前已完成的984条，不重新抽样。新增18个checkpoint，共17712条正式回答；新增3800优先执行。页面同时保留100/500/1000/1500历史对照，共23个checkpoint。

每个checkpoint沿用原246题（diagnostic128、benchmark72、friend46），Thinking与NoTags、T0.6/p0.95与T1/p1共四组设置。BF16、seed42、context32768、output16384。Thinking/NoTags在第二列明确标注。下载HTML后用浏览器打开。

每批最多两个checkpoint、最多8张GPU并行生成，随后同一V4.1模型辅助评分。用户2026-10-24明确要求直接使用现有节点，故将独立MuseNVFP4节点2989切给本轮；另两个节点的MuseBF16服务保留。3037排队作业已取消。3800优先，然后2000至3800其余批次。Muse已有终态结果校验值保留；切换时4条已采样的运行任务明确记录中断，不自动重抽。全部Qwen批次结束后恢复原Muse服务，仅继续32条从未开始的任务。跨节点批次锁和原始输出检查支持断点接续。模型下载放本地NVMe，每批输出与评分SHA校验后只移除本轮该批下载缓存，所有原始输出和错误保留。

评分沿用原rubric、完整候选回答、同一评分模型；JSON schema限制解释长度。遇评分JSON字符串含未转义控制字符时无损读取，评分原始响应保留。分数是单seed模型辅助评分，不等于人工准确率或统计显著性结论。缺失生成、评分均明确标未完成。

2800旧明细在[100/2800补测目录](../game-stage1-3shift-100-2800-20261023/)，500/1000/1500旧明细在[先前目录](../game-stage1-3shift-20261022/)。本目录summary.json只记录新增18个checkpoint，HTML合并历史对照。模型权重不上传。
''')
 root=W/'README.md';text=root.read_text().replace('2000至3200每100step补测：','2000至3800每100step补测：').replace('2000至3200每100step及3800补测：','2000至3800每100step补测：').replace('新增13个checkpoint按计划','新增18个checkpoint按计划').replace('复用2800，新增12个checkpoint正在分批运行。','复用2800，新增13个checkpoint按计划分批执行，当前状态见进度快照。');text=text.replace('[进度](game-stage1-3shift-2000plus-20261023/status/progress.json)','[实时进度](game-stage1-3shift-2000plus-20261023/progress.md)');root.write_text(text);marker='<!-- stage1-2000plus-latest -->'
 if marker not in text:
  first,sep,rest=text.partition('\n');entry='\n'+marker+'\n**Stage1-3Shift 2000至3200每100step补测：** [V2完整对照报告](game-stage1-3shift-2000plus-20261023/report-v2-modes.html) · [进度](game-stage1-3shift-2000plus-20261023/status/progress.json)。复用2800，新增12个checkpoint正在分批运行。\n';root.write_text(first+sep+entry+rest.replace('**Stage1-3Shift 最新补测（100 / 2800）：**','**Stage1-3Shift 先前补测（100 / 2800）：**'))
 command(['git','add','--','README.md',D.name],cwd=W)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=W).returncode:
  command(['git','commit','-m','Update Stage1 checkpoints2000-3200 evaluation progress and evidence'],cwd=W);command(['git','push','origin','HEAD:main'],cwd=W)

last_publish=0
while True:
 try:
  command([sys.executable,str(D/'report.py')]);summary=json.loads((D/'summary.json').read_text());batches=sorted((D/'batches').iterdir());finished=[b.name for b in batches if (b/'status/batch-finished.json').exists()];progress={'utc':time.time(),'responses':sum(r['responses'] for r in summary['results']),'graded':sum(r['graded'] for r in summary['results']),'expected':json.loads((D/'plan.json').read_text())['expected_responses'],'reused_checkpoint2800_responses':984,'requested_grid_expected':json.loads((D/'plan.json').read_text())['requested_grid_responses'],'finished_batches':finished,'total_batches':len(batches),'terminal':len(finished)==len(batches)}
  for name in ['current-batch','continuation-submission','current-allocation']:
   p=D/'status'/(name+'.json')
   if p.exists():progress[name.replace('-','_')]=json.loads(p.read_text())
  jobid=progress.get('current_allocation',progress['continuation_submission'])['job_id']
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
