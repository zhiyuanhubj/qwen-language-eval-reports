"""Complete one review without changing the candidate or rubric; preserve raw JSON string."""
import importlib.util,json,time,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('review',D/'scripts/judge.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
mode='thinking-sampled-t1-p1';label='game-stage1-3shift-100';ident='text-04-en'
path=D/mode/(label+'.jsonl');x=next(json.loads(l) for l in path.open() if json.loads(l).get('id')==ident and json.loads(l).get('status')=='ok')
score_path=D/'scores100'/(mode+'-'+label+'.jsonl')
assert not any(json.loads(l).get('status')=='ok' and json.loads(l).get('id')==ident for l in score_path.open())
original_loads=json.loads;repairs=[]
def lossless_loads(s,*args,**kwargs):
 try:return original_loads(s,*args,**kwargs)
 except json.JSONDecodeError as e:
  if not e.msg.startswith('Invalid control character'):raise
  repairs.append({'error':str(e),'raw_sha256':hashlib.sha256(s.encode()).hexdigest()})
  return original_loads(s,*args,strict=False,**kwargs)
m.json.loads=lossless_loads
result=m.judge((mode,label,x))
result['tail_review']=True;result['json_control_character_parser']={'policy':'Allow literal control characters only inside JSON strings; no content removed or replaced; original judge_raw_response retained','repairs':repairs}
(D/'status/control-character-tail-attempt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
assert result['status']=='ok',result
for k in m.WEIGHTS:assert isinstance(result['assessment']['reasons'][k],str)
with score_path.open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
(D/'status/control-character-tail-verified.json').write_text(json.dumps({'utc':time.time(),'id':ident,'status':'ok','candidate_sha256':result['candidate_sha256'],'rubric_sha256':result['rubric_sha256'],'candidate_and_rubric_unchanged':True,'literal_control_characters_in_judge_strings_preserved':True,'repairs':repairs},indent=2))
print('TAIL_COMPLETE',ident,result['assessment']['scores'],flush=True)
