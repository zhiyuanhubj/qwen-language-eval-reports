import html, json, statistics, sys, time, os, hashlib
from pathlib import Path
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D / 'scripts'))
from report_layout import render
plan = json.loads((D / 'plan.json').read_text())
prompts = {r['id']: r for r in map(json.loads, (Path(plan['suite']) / 'prompts.jsonl').read_text().splitlines())}
keys = ['accuracy', 'language', 'logic', 'instruction', 'completeness']
def read(path):
    rows = {}
    if path.exists():
        for line in path.read_text().split('\n'):
            try: r = json.loads(line)
            except ValueError: continue
            if r.get('status') == 'ok': rows[r['id']] = r
    return rows
out = []
for item in plan['items']:
    for mode in plan['modes']:
        label = item['label']; responses = read(D / mode / (label + '.jsonl'))
        scores = read(D / 'scores100' / (mode + '-' + label + '.jsonl'))
        scores = {i:s for i,s in scores.items() if i in responses and s.get('candidate_sha256')==hashlib.sha256(json.dumps(responses[i],sort_keys=True).encode()).hexdigest()}
        for subset, expected in [('diagnostic128',128),('benchmark72',72),('friend46',46)]:
            rr = [r for i,r in responses.items() if prompts[i]['subset'] == subset]
            ss = [s for i,s in scores.items() if prompts[i]['subset'] == subset]
            means = {k:round(statistics.mean(s['assessment']['scores'][k] for s in ss),2) for k in keys} if ss else {}
            row = {'model':label,'mode':mode,'subset':subset,'responses':len(rr),'graded':len(ss),'expected':expected,
                   'provisional':len(ss)!=expected,'means':means,'overall':round(statistics.mean(means.values()),2) if means else None,
                   'missing_final':sum(not r.get('final_answer') for r in rr),'length_limited':sum(r.get('finish_reason')=='length' for r in rr)}
            objective = D / mode / (label+'.objective.json')
            if subset == 'benchmark72' and objective.exists(): row['objective'] = json.loads(objective.read_text())['groups']
            out.append(row)
note='2000至3200每100step补测（含2000），并优先追加3800；已完成2800直接复用，不重复抽样。新增13个checkpoint，共12792条正式回答。沿用原246题、Thinking/NoTags、T0.6/p0.95和T1/p1、BF16、seed42、context32768、output16384。每批最多2个checkpoint，最多8个单卡候选服务，然后同一V4.1辅助评分。原rubric和完整候选回答不变，评分JSON解释设长度上限；只对JSON字符串中的未转义控制字符做无损读取并保留评分原文。尚未生成或尚未评分的项目保持未完成。表格还包含100/500/1000/1500及2800既有结果。'
runtime = D/'status/progress.json'
if runtime.exists():
    snapshot=json.loads(runtime.read_text());note += ' 运行快照：作业'+str(snapshot.get('current_allocation',snapshot.get('continuation_submission',{})).get('job_id','待更新'))+' '+snapshot.get('scheduler','状态待更新')+'；已完成批次'+str(len(snapshot.get('finished_batches',[])))+'/7。'
summary = {'utc':time.time(),'note':note,'results':out}
previous = []
for root in ['game-stage1-3shift-20261022','game-stage1-3shift-100-2800-20261023']:
    previous.extend(json.loads((D.parent/root/'summary.json').read_text())['results'])
combined = dict(summary, results=previous+out)
page = render(combined,'V2 · Stage1-3Shift · 2000–3200 每100step、3800及历史对照')
for name,data in [('summary.json',json.dumps(summary,ensure_ascii=False,indent=2)),('report.html',page),('report-v2-modes.html',page)]:
    target=D/name;temp=D/(name+'.'+str(os.getpid())+'.tmp');temp.write_text(data);temp.replace(target)
