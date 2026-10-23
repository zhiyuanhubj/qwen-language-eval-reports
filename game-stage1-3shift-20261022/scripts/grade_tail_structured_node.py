import hashlib,importlib.util,json,time
from pathlib import Path
import requests
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tail_grader',D/'scripts/judge.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
mode='thinking-sampled-t1-p1';label='game-stage1-3shift-1500';ident='benchmark-ai2d-2925'
c=next(json.loads(l) for l in (D/mode/(label+'.jsonl')).open() if json.loads(l).get('id')==ident);p=m.P[ident]
data={'prompt':m.judge_prompt(c,p),'target_language':p['target_language'],'reference_and_image_ground_truth':m.facts(p),'finish_reason':c.get('finish_reason'),'FINAL':c.get('final_answer',''),'RAW_REASONING':c.get('reasoning','') if not c.get('final_answer') else '(Hidden: grade final only)'}
keys=list(m.WEIGHTS)
schema={'type':'object','properties':{'source':{'type':'string','enum':['final','raw_unclosed','none']},'format_failure':{'type':'boolean'},'scores':{'type':'object','properties':{k:{'type':'integer','minimum':0,'maximum':100} for k in keys},'required':keys,'additionalProperties':False},'reasons':{'type':'object','properties':{k:{'type':'string','minLength':1,'maxLength':512} for k in keys},'required':keys,'additionalProperties':False},'evidence':{'type':'array','items':{'type':'string','maxLength':120},'maxItems':3},'needs_manual_review':{'type':'boolean'}},'required':['source','format_failure','scores','reasons','evidence','needs_manual_review'],'additionalProperties':False}
payload={'model':'DeepSeek-V4.1-Flash','messages':[{'role':'system','content':m.SYSTEM},{'role':'user','content':json.dumps(data,ensure_ascii=False)}],'temperature':0,'seed':17,'max_tokens':8192,'chat_template_kwargs':{'thinking':False,'enable_thinking':False},'response_format':{'type':'json_schema','json_schema':{'name':'bilingual_assessment','strict':True,'schema':schema}}}
t=time.time();r=requests.post('http://127.0.0.1:30240/v1/chat/completions',json=payload,timeout=600)
(D/'status/grading-tail-structured-response.json').write_text(json.dumps({'utc':time.time(),'http_status':r.status_code,'payload':payload,'response':r.json()},ensure_ascii=False,indent=2))
r.raise_for_status();raw=r.json();ch=raw['choices'][0];assert ch['finish_reason']=='stop',ch['finish_reason'];v=json.loads(ch['message']['content']);assert v['source'] in ['final','raw_unclosed','none']
for k in keys:assert type(v['scores'][k]) is int and 0<=v['scores'][k]<=100
record={'status':'ok','cohort':mode,'model':label,'id':ident,'finish_reason':c.get('finish_reason'),'candidate_sha256':hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest(),'assessment':v,'judge_raw_response':raw,'judge_endpoint':'http://127.0.0.1:30240/v1/chat/completions','judge_max_output_tokens':8192,'seconds':time.time()-t,'tail_retry':True,'judge_response_format':'json_schema; bounded explanation/evidence length to prevent copying candidate repetition; same original system rubric and full candidate','rubric_sha256':hashlib.sha256(m.SYSTEM.encode()).hexdigest()}
with (D/'scores100'/(mode+'-'+label+'.jsonl')).open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
(D/'status/grading-tail-verified.json').write_text(json.dumps({'utc':time.time(),'status':'ok','id':ident,'candidate_sha256':record['candidate_sha256'],'original_rubric_unchanged':True,'raw_candidate_unchanged':True,'bounded_json_schema':True},indent=2))
print('TAIL_REVIEW_COMPLETE',v['scores'],flush=True)
