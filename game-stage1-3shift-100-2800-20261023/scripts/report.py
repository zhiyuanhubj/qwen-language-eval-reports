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
note='补测 checkpoint100/2800：沿用原246题、Thinking/NoTags、T0.6/p0.95与T1/p1、BF16、seed42、context32768、output16384。新增计划1968条回答；页面同时合并先前500/1000/1500结果。评分沿用DeepSeek-V4.1-Flash原rubric与完整原文，解释使用有长度上限的JSON schema；原始分数不改写。暂缺项目保留待完成。'
summary = {'utc':time.time(),'note':note,'results':out}
combined = dict(summary, results=json.loads((D.parent/'game-stage1-3shift-20261022/summary.json').read_text())['results']+out)
page = render(combined,'V2 · Stage1-3Shift · checkpoint 100 / 500 / 1000 / 1500 / 2800')
for name,data in [('summary.json',json.dumps(summary,ensure_ascii=False,indent=2)),('report.html',page),('report-v2-modes.html',page)]:
    target=D/name;temp=D/(name+'.'+str(os.getpid())+'.tmp');temp.write_text(data);temp.replace(target)
