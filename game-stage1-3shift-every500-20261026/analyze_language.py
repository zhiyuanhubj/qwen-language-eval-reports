"""SHA-matched, paired question analysis; keep delivery failures separate from content."""
import hashlib,json,statistics,time
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parent;plan=json.loads((D/'plan.json').read_text());P={p['id']:p for p in map(json.loads,(Path(plan['suite'])/'prompts.jsonl').open())};KEYS=['accuracy','language','logic','instruction','completeness'];OLD=R/'game-stage1-3shift-2000plus-20261023';BASE=R/'game-stage1-3shift-20261022'

def read(p):
 out={}
 if p.exists():
  for l in p.open():
   if not l.strip():continue
   r=json.loads(l)
   if r.get('status')=='ok':out[r['id']]=r
 return out

def source(step):return D if step>=4000 else OLD if step>=2000 else BASE

def stats(ids,c,s):
 if not ids:return None
 scores=[s[i]['assessment']['scores'] for i in ids];means={k:round(statistics.mean(x[k] for x in scores),2) for k in KEYS}
 return {'n':len(ids),'means':means,'overall':round(statistics.mean(sum(x[k] for k in KEYS)/5 for x in scores),2),'unparsed_final':sum(not c[i].get('final_answer') for i in ids),'length_stop':sum(c[i].get('finish_reason')=='length' for i in ids),'raw_unclosed':sum(s[i]['assessment'].get('source')=='raw_unclosed' for i in ids),'no_assessable_answer':sum(s[i]['assessment'].get('source')=='none' for i in ids)}
rows=[]
for mode in plan['modes']:
 C={};S={}
 for step in plan['requested_steps']:
  root=source(step);label=f'game-stage1-3shift-{step}';C[step]=read(root/mode/(label+'.jsonl'));a=read(root/'scores100'/(mode+'-'+label+'.jsonl'));S[step]={i:r for i,r in a.items() if i in C[step] and r.get('candidate_sha256')==hashlib.sha256(json.dumps(C[step][i],sort_keys=True).encode()).hexdigest()}
 for step in plan['requested_steps']:
  common=set(S[step])&set(S[3500])
  for scope in ['diagnostic_text_only','all_three_subsets']:
   for lang in ['zh','en']:
    ids=sorted(i for i in common if P[i]['target_language']==lang and (scope!='diagnostic_text_only' or (P[i]['subset']=='diagnostic128' and not P[i]['images'])))
    now=stats(ids,C[step],S[step]);baseline=stats(ids,C[3500],S[3500]);rows.append({'step':step,'baseline_step':3500,'mode':mode,'scope':scope,'language':lang,'paired_n':len(ids),'candidate':now,'baseline':baseline,'overall_delta':round(now['overall']-baseline['overall'],2) if ids else None,'ids':ids})
result={'utc':time.time(),'baseline_step':3500,'method':'Same question IDs, same target language/mode/sampling, valid candidateSHA-matched scores. Each model paired separately with3500; paired IDs/n recorded. Single-seed model-assisted rubric scores, not causal/statistical claims. Multiturn history depends on preceding model replies; text-only diagnostic shown separately. Original raw and scores preserved.','results':rows};(D/'language-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
lines=['# 每500step中英文详细对照','', '比较500至6000每500step。新增4000/4500/5000/5500/6000，旧结果直接复用；3500作为配对参照。只使用与原回答SHA一致的成功评分，按同一问题ID、同一目标语言、同一模式和采样设置配对。未评分显示待评分，绝不填成0分。','', '五项是原V4.1 rubric的模型辅助分数，并非人工准确率。单seed、小题集和评分生成格式差异不支持统计显著性结论。综合分包含指令与交付格式影响；未解析final也可能有实质答案，需结合准确性、语言、逻辑、原始thinking和final看。benchmark72严格答案正确率单独见主HTML。多轮题上文随模型此前回复变化，因此另列中英文各32道固定纯文字诊断题。','']
for scope,title in [('diagnostic_text_only','纯文字诊断题：中英文各32题'),('all_three_subsets','三个subset：按目标语言拆分')]:
 lines+=['## '+title,'','| Step | 模式 | T / p | 语言 | 配对题数 | 综合 | 语言项 | 准确性项 | 逻辑项 | 未解析final | 长度上限 | 比3500综合差 |','|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:
  if r['scope']!=scope:continue
  kind='Thinking' if r['mode'].startswith('thinking') else 'NoTags';sampling='1/1' if r['mode'].endswith('t1-p1') else '0.6/0.95';v=r['candidate']
  values=[str(r['step']),kind,sampling,'中文' if r['language']=='zh' else '英文',str(r['paired_n'])]
  values += [f'{v["overall"]:.2f}',f'{v["means"]["language"]:.2f}',f'{v["means"]["accuracy"]:.2f}',f'{v["means"]["logic"]:.2f}',str(v['unparsed_final']),str(v['length_stop']),f'{r["overall_delta"]:+.2f}'] if v else ['待评分']*7
  lines.append('| '+' | '.join(values)+' |')
 lines+=['']
lines+=['英文合并题集含benchmark72，中文不含这些英文题；不直接用两种语言均分之差推断语言优劣。应按相同语言、相同配对问题比较step变化。所有五项指标、题目ID和3500对应统计见[JSON](language-analysis.json)。','', '[主报告](report-v2-modes.html) · [实时进度](progress.md) · [完整原始明细](evidence/manifest.json)',''];(D/'language-analysis.md').write_text('\n'.join(lines));print('language_analysis_rows',len(rows))
