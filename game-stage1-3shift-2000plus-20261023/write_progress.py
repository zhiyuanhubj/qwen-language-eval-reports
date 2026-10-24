"""Generate a readable live progress page and persistent milestone history."""
import collections,datetime,json,math,os,time
from pathlib import Path
D=Path(__file__).resolve().parent
plan=json.loads((D/'plan.json').read_text());progress=json.loads((D/'status/progress.json').read_text());summary=json.loads((D/'summary.json').read_text());now=time.time()

def atomic(path,text):
 tmp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp');tmp.write_text(text);tmp.replace(path)
def utc(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).strftime('%m-%d %H:%M:%S UTC')
def family(mode):return 'Thinking' if mode.startswith('thinking') else 'NoTags'
def sampling(mode):return '1 / 1' if mode.endswith('t1-p1') else '0.6 / 0.95'
groups={}
for row in summary['results']:
 k=(row['model'],row['mode']);g=groups.setdefault(k,{'responses':0,'graded':0,'expected':0})
 for name in ['responses','graded','expected']:g[name]+=row[name]
progress['responses']=sum(g['responses'] for g in groups.values());progress['graded']=sum(g['graded'] for g in groups.values())
mp=D/'status/milestones.json';events=json.loads(mp.read_text()) if mp.exists() else [];known={e['id'] for e in events};major=False

def event(ident,message,important=False):
 global major
 if ident not in known:
  known.add(ident);events.append({'id':ident,'utc':now,'message':message});major|=important
for (model,mode),g in groups.items():
 for metric,label in [('responses','回答'),('graded','评分')]:
  for fraction in [.25,.5,.75,1]:
   if g[metric]>=math.ceil(g['expected']*fraction):event(f'{model}/{mode}/{metric}/{fraction}',f'{model} · {family(mode)} · {sampling(mode)}：{label}达到 {int(fraction*100)}%（当前{g[metric]}/{g["expected"]}）')
for batch in progress['finished_batches']:event('batch-done/'+batch,'批次 '+batch+'：回答、评分及SHA对应关系已校验，准备后续批次',True)
current=progress.get('current_batch',{});allocation=progress.get('batch_allocation_status',{});phase=allocation.get('phase',current.get('phase','waiting'))
if current.get('batch'):
 event('phase/'+current['batch']+'/'+phase,'当前批次 '+current['batch']+'：'+phase,phase in ['loading_judge','grading'])
exitpath=D/'status/existing-2989-exit.json';failure=None
if exitpath.exists():
 exited=json.loads(exitpath.read_text())
 if exited.get('worker_returncode') not in [None,0]:
  failure='评测进程异常退出（code='+str(exited['worker_returncode'])+'）；已保留输出，需处理后继续。'
  event('worker-error/'+str(exited.get('finished_utc')),failure,True)
atomic(mp,json.dumps(events,ensure_ascii=False,indent=2))
lines=['# Qwen 语言评测进度','',f'更新时间：**{utc(now)}**。后台约每30秒核对本地记录，GitHub约每3分钟同步；批次完成、切换评分和执行异常会触发同步。','',f'当前节点：**{progress.get("current_allocation",{}).get("job_id","待分配")}** · 当前批次：**{current.get("batch","待开始")}** · 阶段：`{phase}`','']
if failure:lines+=['**'+failure+'**','']
lines += [f'新增评测：回答 **{progress["responses"]:,}/{progress["expected"]:,}**，有效评分 **{progress["graded"]:,}/{progress["expected"]:,}**；完成批次 **{len(progress["finished_batches"])}/{progress["total_batches"]}**。已完成的2800复用984条，单独保留，不计入新增生成数。','', '先完成3800的生成和评分，再按计划处理2000～3200其余checkpoint。每个checkpoint固定246题 × Thinking/NoTags × 两组采样，共984条。','', '## 当前批次各组','', '| Checkpoint | 模式 | Temperature / Top-p | 回答 | 评分 |','|---|---|---|---:|---:|']
batchpath=D/'batches'/current.get('batch','')/'plan.json'
current_models=[i['label'] for i in json.loads(batchpath.read_text())['items']] if batchpath.exists() else []
for model in current_models:
 for mode in plan['modes']:
  g=groups[(model,mode)];lines.append(f'| {model.split("-")[-1]} | {family(mode)} | {sampling(mode)} | {g["responses"]}/{g["expected"]} | {g["graded"]}/{g["expected"]} |')
lines+=['','## 全部新增checkpoint','', '| Checkpoint | 回答 | 评分 | 状态 |','|---|---:|---:|---|']
for item in sorted(plan['items'],key=lambda i:(i['step']!=3800,i['step'])):
 gs=[groups[(item['label'],m)] for m in plan['modes']];a=sum(g['responses'] for g in gs);s=sum(g['graded'] for g in gs);n=sum(g['expected'] for g in gs)
 state='完成' if a==s==n else '评分中' if s else '待评分' if a==n else '生成中' if a else '待运行'
 lines.append(f'| {item["step"]} | {a}/{n} | {s}/{n} | {state} |')
lines+=['','## 最近里程碑','']
for e in reversed(events[-16:]):lines.append('- '+utc(e['utc'])+'：'+e['message'])
lines+=['','[下载完整HTML对照报告](report-v2-modes.html) · [机器可读进度](status/progress.json) · [全部里程碑](status/milestones.json) · [题目、完整回答、逐项评分与日志](evidence/manifest.json)','', '回答完成和评分完成分开统计。评分只采用与原回答SHA一致的有效记录；未完成项目不当作0分。页面是同步时快照，刷新本页可查看新的记录。','']
atomic(D/'progress.md','\n'.join(lines));print(json.dumps({'major_update':major,'events':len(events),'responses':progress['responses'],'graded':progress['graded']}))
