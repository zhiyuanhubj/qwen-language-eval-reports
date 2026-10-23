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
 for name in ['plan.json','authorization.json','summary.json','report.html','report-v2-modes.html','run.sbatch']:
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
 (DEST/'README.md').write_text('''# Stage1-3Shift：2000–3200 每100step

[下载 V2 对照报告](report-v2-modes.html) · [进度快照](status/progress.json) · [固定计划与HF版本](plan.json) · [原始回答、评分、题目及日志](evidence/manifest.json)

范围包含2000、2100、2200、2300、2400、2500、2600、2700、2800、2900、3000、3100、3200。2800直接复用之前已完成的984条，不重新抽样。新增12个checkpoint，共11808条正式回答。页面同时保留100/500/1000/1500历史对照，共17个checkpoint。

每个checkpoint沿用原246题（diagnostic128、benchmark72、friend46），Thinking与NoTags、T0.6/p0.95与T1/p1共四组设置。BF16、seed42、context32768、output16384。Thinking/NoTags在第二列明确标注。下载HTML后用浏览器打开。

每批两个checkpoint、8张GPU并行生成，随后同一V4.1模型辅助评分。一个节点执行一个批次；现有2733节点仍在执行Beam Pro测试，其模型和原始试验保持运行。单独排队申请24小时节点（3037）执行本轮；批次锁和原始输出检查支持断点接续。只在一个评测节点上生成或评分。临时模型下载放本地NVMe；每批输出与评分SHA校验通过后仅移除该批新下载的权重缓存，HF固定版本保留在计划中。所有原始输出与错误保留。

评分沿用原rubric、完整候选回答、同一评分模型；JSON schema限制解释长度。遇评分JSON字符串含未转义控制字符时无损读取，评分原始响应保留。分数是单seed模型辅助评分，不等于人工准确率或统计显著性结论。缺失生成、评分均明确标未完成。

2800旧明细在[100/2800补测目录](../game-stage1-3shift-100-2800-20261023/)，500/1000/1500旧明细在[先前目录](../game-stage1-3shift-20261022/)。本目录summary.json只记录新增12个checkpoint，HTML合并历史对照。模型权重不上传。
''')
 root=W/'README.md';text=root.read_text();marker='<!-- stage1-2000plus-latest -->'
 if marker not in text:
  first,sep,rest=text.partition('\n');entry='\n'+marker+'\n**Stage1-3Shift 2000至3200每100step补测：** [V2完整对照报告](game-stage1-3shift-2000plus-20261023/report-v2-modes.html) · [进度](game-stage1-3shift-2000plus-20261023/status/progress.json)。复用2800，新增12个checkpoint正在分批运行。\n';root.write_text(first+sep+entry+rest.replace('**Stage1-3Shift 最新补测（100 / 2800）：**','**Stage1-3Shift 先前补测（100 / 2800）：**'))
 command(['git','add','--','README.md',D.name],cwd=W)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=W).returncode:
  command(['git','commit','-m','Update Stage1 checkpoints2000-3200 evaluation progress and evidence'],cwd=W);command(['git','push','origin','HEAD:main'],cwd=W)

last_publish=0
while True:
 try:
  command([sys.executable,str(D/'report.py')]);summary=json.loads((D/'summary.json').read_text());batches=sorted((D/'batches').iterdir());finished=[b.name for b in batches if (b/'status/batch-finished.json').exists()];progress={'utc':time.time(),'responses':sum(r['responses'] for r in summary['results']),'graded':sum(r['graded'] for r in summary['results']),'expected':11808,'reused_checkpoint2800_responses':984,'requested_grid_expected':12792,'finished_batches':finished,'total_batches':len(batches),'terminal':len(finished)==len(batches)}
  for name in ['current-batch','continuation-submission']:
   p=D/'status'/(name+'.json')
   if p.exists():progress[name.replace('-','_')]=json.loads(p.read_text())
  write(D/'status/progress.json',progress)
  if time.time()-last_publish>=180 or progress['terminal']:publish();last_publish=time.time()
  print(json.dumps(progress),flush=True)
  if progress['terminal']:break
 except Exception:traceback.print_exc()
 time.sleep(30)
