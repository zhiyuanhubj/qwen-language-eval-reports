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
note='2026-11-02 新增10000/10500/11000/11500/12000五个checkpoint，每个246题×四模式，共4920条。原suite、模板、采样、BF16、seed42、32768上下文和16384输出不变；沿用原V4.1 rubric，保留thinking/final/评分/错误/日志。旧500–9500结果只读复用，缺项不当成0分。'
summary = {'utc':time.time(),'note':note,'results':out}
previous=[]
for root in ['game-stage1-3shift-20261022','game-stage1-3shift-2000plus-20261023','game-stage1-3shift-every500-20261026']:
    previous.extend(r for r in json.loads((D.parent/root/'summary.json').read_text())['results'] if int(r['model'].split('-')[-1])%500==0 and int(r['model'].split('-')[-1])<=9500)
combined=dict(summary,results=previous+out)
page=render(combined,'V2 · Game Stage1-3Shift · 每500step：500–12000')
for name,data in [('summary.json',json.dumps(summary,ensure_ascii=False,indent=2)),('report.html',page),('report-v2-modes.html',page)]:
    target=D/name;temp=D/(name+'.'+str(os.getpid())+'.tmp');temp.write_text(data);temp.replace(target)
