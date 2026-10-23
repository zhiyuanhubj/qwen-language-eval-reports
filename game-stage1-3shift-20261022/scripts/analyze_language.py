import json,statistics,hashlib,collections,time
from pathlib import Path
R=Path('/fsx/home/zhiyuan/language-pilot-20261011');D=R/'game-stage1-3shift-20261022';plan=json.loads((D/'plan.json').read_text());P={r['id']:r for r in map(json.loads,(Path(plan['suite'])/'prompts.jsonl').open())};keys=['accuracy','language','logic','instruction','completeness']
def read(p):
 rows={}
 if p.exists():
  for line in p.open():
   if not line.strip():continue
   r=json.loads(line)
   if r.get('status')=='ok':rows[r['id']]=r
 return rows
out=[]
for mode in plan['modes']:
 kind='thinking' if mode.startswith('thinking') else 'notags';roots={'base':R/('evaluation-'+kind+'-246-v1'),'500':D,'1000':D,'1500':D};labels={'base':'prior-base',**{str(i['step']):i['label'] for i in plan['items']}};C={};S={}
 for key in roots:
  C[key]=read(roots[key]/mode/(labels[key]+'.jsonl'));a=read(roots[key]/'scores100'/(mode+'-'+labels[key]+'.jsonl'));S[key]={i:r for i,r in a.items() if i in C[key] and r.get('candidate_sha256')==hashlib.sha256(json.dumps(C[key][i],sort_keys=True).encode()).hexdigest()}
 common=set.intersection(*(set(v) for v in S.values()))
 for scope in ['all_three_subsets','diagnostic128','diagnostic_text_only']:
  for language in ['zh','en']:
   ids=sorted(i for i in common if P[i]['target_language']==language and (scope=='all_three_subsets' or P[i]['subset']=='diagnostic128') and (scope!='diagnostic_text_only' or not P[i]['images']))
   models={}
   for key in roots:
    a=[S[key][i]['assessment'] for i in ids];means={k:round(statistics.mean(x['scores'][k] for x in a),2) for k in keys};models[key]={**means,'overall':round(statistics.mean(means.values()),2),'format_failure':sum(x.get('format_failure',False) for x in a),'source_none':sum(x.get('source')=='none' for x in a),'language_below75':sum(x['scores']['language']<75 for x in a),'final_missing':sum(not C[key][i].get('final_answer') for i in ids),'length_stop':sum(C[key][i].get('finish_reason')=='length' for i in ids)}
   out.append({'mode':mode,'scope':scope,'language':language,'paired_n':len(ids),'models':models,'ids':ids})
result={'utc':time.time(),'method':'Same question IDs with valid candidate SHA-matched scores across baseline and all3 checkpoints. All-subsets and diagnostic-only shown separately. Single seed, model-assisted scores, no causal or statistical significance claim. Baseline is historical local Qwen3.5-9B, not proof of exact training initialization.','results':out};(D/'language-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for r in out:
 if r['scope'] not in ['all_three_subsets','diagnostic_text_only']:continue
 print(r['scope'],r['mode'],r['language'],'n',r['paired_n'])
 for k,v in r['models'].items():print(k,v)

lookup={(r['scope'],r['mode'],r['language']):r for r in out}
lines=['# 中英文能力对照：500 / 1000 / 1500','', '以下按相同题目、相同模式、相同采样设置配对；只使用与原回答 SHA 一致的评分。分数是五项直接百分制的模型辅助评价，**不是准确率，也不是统计显著性检验**。每个设置仅一个 seed。', '', '**当前结论：退化集中在 Thinking 输出与交付格式，温度1时中文语言稳定性下降尤其明显；低温 NoTags 相对稳定，不能概括成中英文在所有模式都持续下降。**', '', '## 纯文字诊断题：中英文各32题', '', '同一组固定题，排除图像题。综合分是准确性、语言、逻辑、指令和完整性五项等权平均。旧基座是历史本地 Qwen3.5-9B 参照，不作为当前仓库训练初始化的证明。']
for metric,title in [('overall','综合分'),('language','语言项'),('accuracy','准确性项'),('final_missing','未解析到独立最终答案的条数')]:
 lines+=['','### '+title,'','| 模式 | 采样 | 语言 | 旧基座 | 500 | 1000 | 1500 |','|---|---|---|---:|---:|---:|---:|']
 for mode in plan['modes']:
  for language in ['zh','en']:
   r=lookup[('diagnostic_text_only',mode,language)];v=r['models'];kind='Thinking' if mode.startswith('thinking') else 'NoTags';sampling='T=1/p=1' if 't1-p1' in mode else 'T=0.6/p=0.95';fmt=lambda x:str(x) if metric=='final_missing' else f'{x:.2f}'
   lines.append('| '+ ' | '.join([kind,sampling,'中文' if language=='zh' else '英文']+[fmt(v[k][metric]) for k in ['base','500','1000','1500']])+' |')
lines+=['','## 如何解读','', '- 低温 Thinking 纯文字题的综合分：中文 88.73 → 83.44 → 75.20，英文 92.43 → 85.32 → 78.16。','- 同一设置下，500 的64道中英纯文字题中有16道未解析到独立 final，1500 增至48道。原始思考文本中可能仍有答案；评分已依原规则检查原文，但对交付失败限制指令/完整性分，不能把综合分下降全解释成知识遗忘。','- 低温 NoTags 纯文字题：中文综合分 93.73 → 94.65 → 93.48，英文 93.22 → 94.78 → 95.13，整体稳定。','- 高温 Thinking 中文语言项 84.09 → 78.00 → 64.34，确有输出语言稳定性恶化。高温 NoTags 英文纯文字题也从综合92.46降至82.61，应与低温结果区分。','- 这是一组固定小样本和单seed结果，不等同大规模通用能力、完整公开benchmark或因果结论。','', '## 原三个subset合并、按目标语言拆分的配对综合分','', '| 模式 | 采样 | 语言 | 配对题数 | 旧基座 | 500 | 1000 | 1500 |','|---|---|---|---:|---:|---:|---:|---:|']
for mode in plan['modes']:
 for language in ['zh','en']:
  r=lookup[('all_three_subsets',mode,language)];v=r['models'];kind='Thinking' if mode.startswith('thinking') else 'NoTags';sampling='T=1/p=1' if 't1-p1' in mode else 'T=0.6/p=0.95'
  lines.append('| '+' | '.join([kind,sampling,'中文' if language=='zh' else '英文',str(r['paired_n'])]+[f"{v[k]['overall']:.2f}" for k in ['base','500','1000','1500']])+' |')
lines+=['','英文合并组含benchmark72，中文组不含这些英文题，因此不要直接把中英文两列之差解释为语言优劣；应比较同一种语言、同一批题目在不同checkpoint的变化。缺失评分会改变配对题数，以JSON中的ID清单为准。','', '[完整指标和配对题目ID](language-analysis.json) · [主报告](report.html) · [原始输出、逐项评分和日志](evidence/manifest.json)','']
(D/'language-analysis.md').write_text('\n'.join(lines))

with (D/'language-analysis.md').open('a') as f:f.write('\n\n格式解读补充：综合分包含标签/交付格式的影响；已发现部分 raw_unclosed 评分未一致执行上限，原分保留。请结合[格式失败的实际例子与审计](format-examples.md)及单项语言/准确性/逻辑解读，勿将所有综合降分等同知识遗忘。\n')
