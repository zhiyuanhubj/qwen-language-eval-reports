import html,json,re
from datetime import datetime,timezone
KEYS=['accuracy','language','logic','instruction','completeness']
def group(model):
 if model=='prior-base':return 'Base'
 if re.match(r'prior-[AB]\d+$',model):return 'A/B'
 return 'Stage2' if model.startswith('stage2-') else 'Stage1'
def order(row):
 m=row['model'];n=re.findall(r'\d+',m);return (0 if 'prior-A' in m else 1 if 'prior-B' in m else 0,int(n[-1]) if n else 0,row['mode'].endswith('t1-p1'))
def render(data,title):
 rows=data['results'];esc=html.escape;total=sum(r['expected'] for r in rows);answered=sum(r['responses'] for r in rows);graded=sum(r['graded'] for r in rows)
 runs={}
 for r in rows:
  k=(r['model'],r['mode']);v=runs.setdefault(k,[0,0,0]);v[0]+=r['responses'];v[1]+=r['graded'];v[2]+=r['expected']
 complete=sum(a==e for a,g,e in runs.values());finished=sum(g==e for a,g,e in runs.values())
 parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><style>body{margin:0;background:#f5f7fb;color:#152438;font:14px system-ui,sans-serif}main{max-width:1600px;margin:auto;padding:28px}h1{font-size:27px;margin:0 0 8px}h2{margin:24px 0 10px}.muted,small{color:#5c6d80}small{display:block;font-size:11px}.cards{display:flex;gap:16px;flex-wrap:wrap;margin:20px 0}.card{background:white;border:1px solid #dce3ed;border-radius:10px;padding:14px 20px;min-width:190px}.card b{display:block;font-size:25px}.controls{display:flex;gap:16px;flex-wrap:wrap;position:sticky;top:0;background:#f5f7fb;padding:12px 0;z-index:3}select,input{font:inherit;padding:9px;border:1px solid #bac6d5;border-radius:6px;background:white}.table{overflow:auto;background:white;border:1px solid #dce3ed;border-radius:8px}table{width:100%;border-collapse:collapse;white-space:nowrap}td,th{padding:10px 12px;text-align:right;border-bottom:1px solid #e7ecf3}th{background:#edf2f8;font-size:12px}td:first-child,th:first-child,td:nth-child(2),td:nth-child(5),td:nth-child(6){text-align:left}tr:hover{background:#f5f9ff}.done{color:#16704a}.partial{color:#9b5a00}.pending{color:#67778a}.score{font-weight:650}.objective{background:#edf7ff}details{background:white;padding:14px;border-radius:8px;margin-top:20px}details p{white-space:pre-wrap;line-height:1.8}a{color:#2258a5}.empty{padding:20px;color:#65758a}</style><main><h1>'+esc(title)+'</h1>']
 utc=datetime.fromtimestamp(data['utc'],timezone.utc).strftime('%Y-%m-%d %H:%M UTC');parts.append('<div class="muted">数据快照：'+utc+' · 两组均为采样解码 · T=0.6 / top_p=0.95 与 T=1 / top_p=1</div>')
 parts.append('<div class="cards">'+''.join('<div class="card">'+label+'<b>'+value+'</b></div>' for label,value in [('已生成答案',f'{answered:,} / {total:,}'),('已完成评分',f'{graded:,} / {total:,}'),('答案完整的模型×设置',f'{complete} / {len(runs)}'),('评分完整的模型×设置',f'{finished} / {len(runs)}')])+'</div>')
 parts.append('<p><b>每行对应：checkpoint × 生成模式 × 采样参数 × 题集。</b>相同模型和温度出现两行时，分别是 Thinking 与 NoTags；请看“生成模式”列。<br><b>回答完成不等于评分完成。</b>有评分就显示数字；尚未评分明确标“待评分”，不当作0分。橙色数字为已评分样本的临时均分，旁边列出覆盖数。公开72题的标准答案判分不依赖Judge，单独显示。</p><div class="controls"><label>题集 <select id="subset"><option value="benchmark72">公开标准答案 · 72题</option><option value="diagnostic128">原诊断集 · 128题</option><option value="friend46">朋友题集 · 46题</option></select></label><label>生成模式 <select id="family"><option value="all">Thinking + NoTags</option><option value="thinking">Thinking · 开启思考</option><option value="notags">NoTags · 关闭思考/无标签</option></select></label><label>采样设置 <select id="mode"><option value="all">两组并列</option><option value="06">T=0.6 / p=0.95</option><option value="1">T=1 / p=1</option></select></label><input id="search" placeholder="搜索模型或步数"><a href="https://github.com/zhiyuanhubj/qwen-language-eval-reports/blob/main/game-stage1-3shift-20261022/summary.json">下载完整JSON</a></div>')
 parts.append('<p><a href="https://github.com/zhiyuanhubj/qwen-language-eval-reports/tree/main/game-stage1-3shift-20261022/evidence">完整题目、回答、逐题评分与运行日志</a> · <a href="https://github.com/zhiyuanhubj/qwen-language-eval-reports/blob/main/game-stage1-3shift-20261022/evidence/manifest.json">文件清单及校验值</a>（明细为上传时快照，未完成项仍保留。）</p>')
 headers=['模型','生成模式','Temperature','Top-p','题集','状态','回答','评分','准确性','语言','逻辑','指令','完整性','整体均分','标准答案正确率','未解析final','长度上限']
 for g in ['Base','Stage1','Stage2','A/B']:
  subsetrows=[r for r in rows if group(r['model'])==g]
  if not subsetrows:continue
  models=len({r['model'] for r in subsetrows});parts.append('<section><h2>'+g+(' · 独立训练实验' if g=='A/B' else '')+f' <small>{models}个模型，按checkpoint步数升序</small></h2><div class="table"><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>')
  for r in sorted(subsetrows,key=order):
   n=r['expected'];a=r['responses'];s=r['graded'];partial=s<n;mode='1' if r['mode'].endswith('t1-p1') else '06';model=r['model'];display=model.replace('prior-','').replace('stage2-','').replace('historical','checkpoint-')
   if a==n:status='回答完成 · '+('评分完成' if s==n else '评分中' if s else '待评分')
   else:status='未运行 / 待恢复' if a==0 else '回答不完整 · 待恢复/核查'
   cls='done' if s==n else 'partial' if s else 'pending';score=lambda v: ('待评分' if v is None else f'{v:.2f}'+('<small>临时</small>' if partial else ''))
   obj=r.get('objective',{}).get('all72');objective='不适用' if r['subset']!='benchmark72' else '待标准答案判分'
   if obj:objective=f"{obj['correct']}/{obj['expected']} · {obj['accuracy_percent']:.2f}%"+('<small>回答不完整</small>' if not obj.get('complete') else '')
   evidence='https://github.com/zhiyuanhubj/qwen-language-eval-reports/blob/main/game-stage1-3shift-20261022/evidence/'
   score_link=('<a href="'+evidence+'scores100/'+r['mode']+'-'+model+'.jsonl.gz">逐题评分</a>') if s else '评分待生成'
   detail=esc(display)+'<small><a href="'+evidence+r['mode']+'/'+model+'.jsonl.gz">完整回答</a> · '+score_link+'</small>'
   family='thinking' if r['mode'].startswith('thinking') else 'notags'
   family_text='<b>Thinking</b><small>开启思考</small>' if family=='thinking' else '<b>NoTags</b><small>关闭思考 / 无标签</small>'
   vals=[detail,family_text,'0.6' if mode=='06' else '1.0','0.95' if mode=='06' else '1.0',esc(r['subset']),esc(status),f'{a}/{n}',f'{s}/{n}']+[score(r['means'].get(k)) for k in KEYS]+[score(r['overall']),objective,str(r['missing_final']),str(r['length_limited'])]
   parts.append('<tr data-subset="'+r['subset']+'" data-mode="'+mode+'" data-family="'+family+'" data-model="'+esc(model)+'">'+''.join('<td class="'+(cls+' score' if 8<=i<=13 else 'objective' if i==14 else '')+'">'+v+'</td>' for i,v in enumerate(vals))+'</tr>')
  parts.append('</tbody></table><div class="empty" hidden>此分组无匹配模型。</div></div></section>')
 parts.append('<details><summary>评测设置、Thinking格式问题与评分局限</summary><p>'+esc(data['note'])+'</p></details><p class="muted">本页为Stage1-3Shift的500、1000、1500三个checkpoint；每个checkpoint有Thinking/NoTags各两组采样，共四种设置。缺失答案的最终统计按完整题集分母计入；未评分不能冒充最终0分。此页面是本地快照，生成新报告后需刷新。</p></main><script>function filter(){const s=document.getElementById("subset").value,m=document.getElementById("mode").value,f=document.getElementById("family").value,q=document.getElementById("search").value.toLowerCase();document.querySelectorAll("tbody tr").forEach(r=>r.hidden=r.dataset.subset!==s||(f!=="all"&&r.dataset.family!==f)||(m!=="all"&&r.dataset.mode!==m)||!r.dataset.model.toLowerCase().includes(q));document.querySelectorAll("section").forEach(s=>s.querySelector(".empty").hidden=[...s.querySelectorAll("tbody tr")].some(r=>!r.hidden));}document.querySelectorAll("select,input").forEach(e=>e.addEventListener("input",filter));filter();</script></html>')
 return ''.join(parts)
