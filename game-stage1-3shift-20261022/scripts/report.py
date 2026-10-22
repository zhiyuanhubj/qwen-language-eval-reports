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
note='Stage1-3Shift checkpoint 500/1000/1500 重测。沿用原固定246题、Thinking/NoTags和两组采样：T0.6/p0.95、T1/p1；BF16、seed42、context32768、output16384。计划2952条正式回答。原始输出、thinking、错误和评分分别保留。五项直接百分制为DeepSeek-V4.1-Flash辅助评分，不是人工准确率；benchmark72另列严格答案判分。上下文错误和未评分项目不标完成。旧实验不覆盖。'
if (D/'status/unicode-jsonl-fix.json').exists():
    note+=' 已修正JSONL读取：按ASCII换行分隔，避免将模型原文中的Unicode换行误当成新记录；500/T1的text-06-en原文和评分均保留，未重新生成或改写。'
if (D/'status/task-exit.json').exists():
    note+=' 500/Thinking/T0.6的friend-EM2-3保留HTTP400：实际输入至少32769 tokens，超过原32768上下文。未截断历史或修改上下文，故成功生成2951/2952；这不是完整生成率。首轮评分在4小时时限停止，1500/Thinking/T1的benchmark-ai2d-2925因评分输出预算耗尽单独补评，沿用同一评分模型和rubric，只提高评分输出预算；以实际评分覆盖数判断是否完成。'
summary = {'utc':time.time(),'note':note,'results':out}
for name,data in [('summary.json',json.dumps(summary,ensure_ascii=False,indent=2)),('report.html',render(summary,'Stage1-3Shift · checkpoint 500 / 1000 / 1500'))]:
    target=D/name;temp=D/(name+'.'+str(os.getpid())+'.tmp');temp.write_text(data);temp.replace(target)
