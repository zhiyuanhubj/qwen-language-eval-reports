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
note='Game Stage1-3Shift每500step详细补测。4000至9500每500step累计12个checkpoint，共11808条回答；4000至6000的4920条已完成，本次接续6500/7000/7500/8000/8500/9000/9500共6888条；500至3500每500step复用已完成结果。原246题、Thinking/NoTags、T0.6/p0.95与T1/p1、BF16、seed42、context32768、output16384不变。全部原始回答、thinking、final、逐项评分、错误与日志保留。评分为同一V4.1原rubric模型辅助分数，非人工准确率。上下文超限不截断历史、不变更设置，保留失败记录和覆盖分母。旧实验分数与原文不改写。'
summary = {'utc':time.time(),'note':note,'results':out}
previous=[]
for root in ['game-stage1-3shift-20261022','game-stage1-3shift-2000plus-20261023']:
    previous.extend(r for r in json.loads((D.parent/root/'summary.json').read_text())['results'] if int(r['model'].split('-')[-1])%500==0 and int(r['model'].split('-')[-1])<=3500)
combined=dict(summary,results=previous+out)
page=render(combined,'V2 · Game Stage1-3Shift · 每500step：500–9500')
for name,data in [('summary.json',json.dumps(summary,ensure_ascii=False,indent=2)),('report.html',page),('report-v2-modes.html',page)]:
    target=D/name;temp=D/(name+'.'+str(os.getpid())+'.tmp');temp.write_text(data);temp.replace(target)
