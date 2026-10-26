"""Run the fixed diagnostic against an approved local OpenAI-compatible server.

This does not start a model server. Keep raw responses and reasoning for blind
review. Script heuristics only select examples for review; they are not scores.
"""
import argparse,base64,concurrent.futures,hashlib,json,re,time
from pathlib import Path
import requests

def verify(root):
    manifest=json.loads((root/'manifest.json').read_text())
    for name,expected in manifest['hashes'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
    return manifest

def messages_for(row,root):
    messages=json.loads(json.dumps(row['messages']))
    if row['images']:
        assert len(messages)==1 and messages[0]['role']=='user'
        text=messages[0]['content'].replace('<image>','').strip()
        images=[{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode((root/p).read_bytes()).decode()}} for p in row['images']]
        messages[0]['content']=images+[{'type':'text','text':text}]
    return messages

def sections(message,thinking=True):
    content=message.get('content') or '';reason=message.get('reasoning_content') or message.get('reasoning') or ''
    if '</think>' in content:
        thought,content=content.split('</think>',1);reason=reason+'\n'+thought.removeprefix('<think>')
    if not reason and '</think>' not in (message.get('content') or '') and (thinking or content.lstrip().startswith('<think>')):
        reason,content=content.removeprefix('<think>'),''
    return reason.strip(),content.replace('<|im_end|>','').replace('<|endoftext|>','').strip()

def review_flags(text,language):
    clean=re.sub(r'```.*?```','',text,flags=re.S);flags=[]
    if language=='en' and len(re.findall(r'[\u4e00-\u9fff]',clean))>=8:flags.append('Chinese span in English response')
    if language=='zh' and re.search(r'\b[A-Za-z]+(?:[ ,;:]+[A-Za-z]+){7,}\b',clean):flags.append('English phrase in Chinese response')
    for label,pattern in [('Cyrillic',r'[\u0400-\u052f]'),('Arabic',r'[\u0600-\u06ff]'),('Devanagari',r'[\u0900-\u097f]'),('Kana',r'[\u3040-\u30ff]')]:
        if len(re.findall(pattern,clean))>=6:flags.append(label+' characters')
    return flags

def main():
    p=argparse.ArgumentParser();p.add_argument('--suite',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',required=True);p.add_argument('--revision',required=True);p.add_argument('--base-url',default='http://127.0.0.1:9019/v1')
    p.add_argument('--authorization',type=Path,required=True);p.add_argument('--mode',choices=['nonthinking-notags-t06-p095', 'nonthinking-notags-t1-p1'],required=True);p.add_argument('--smoke',action='store_true');p.add_argument('--workers',type=int,default=4)
    args=p.parse_args();thinking=False;temperature,top_p={'nonthinking-notags-t06-p095':(0.6,0.95),'nonthinking-notags-t1-p1':(1.0,1.0)}[args.mode];authorization=json.loads(args.authorization.read_text())
    assert authorization.get('user_approved_gpu_evaluation') is True,'Await explicit user approval'
    manifest=verify(args.suite);rows=[json.loads(l) for l in (args.suite/'prompts.jsonl').open()]
    if args.smoke:rows=[rows[0],rows[64],rows[128],rows[200]]
    response=requests.get(args.base_url+'/models',timeout=30);response.raise_for_status()
    assert args.model in [x['id'] for x in response.json()['data']],'Incorrect served checkpoint identity'
    seeds=[42]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    metadata={'backend':'vllm-0.31.1rc1.dev253+g7d0b4e57a','protocol':'notags-three-subsets-v1','max_new_tokens':16384,'max_model_len':32768,'dtype':'bfloat16','stop_token_ids':[248046,248044],'model':args.model,'revision':args.revision,'suite_manifest_sha256':hashlib.sha256((args.suite/'manifest.json').read_bytes()).hexdigest(),'mode':args.mode,'seeds':seeds,'enable_thinking':thinking,'smoke':args.smoke,'temperature':temperature,'top_p':top_p,'template_policy':'enable_thinking=false; native assistant generation suffix with ALL think prefix tags absent; audited rendered prompt','created':time.time()}
    meta_path=args.output.with_suffix('.metadata.json')
    if meta_path.exists():
        prior=json.loads(meta_path.read_text())
        for k in ['model','revision','suite_manifest_sha256','mode','seeds','enable_thinking','smoke','temperature','top_p','template_policy','protocol']:assert metadata[k]==prior[k]
    else:meta_path.write_text(json.dumps(metadata,indent=2))
    done=set();prior_rows={}
    if args.output.exists():
        for line in args.output.open():
            row=json.loads(line)
            if row.get('status')=='ok':
                done.add((row['id'],row['seed']));prior_rows[(row['id'],row['seed'])]=row
    def run(task):
        row,seed,messages=task;start=time.time()
        payload={'model':args.model,'messages':messages,'max_tokens':16384,'temperature':temperature,'top_p':top_p,'seed':seed,'chat_template_kwargs':{'enable_thinking':thinking,'pilot_mode':args.mode},'stop_token_ids':[248046,248044],'skip_special_tokens':False}
        try:
            r=requests.post(args.base_url+'/chat/completions',json=payload,timeout=3600);r.raise_for_status();raw=r.json()
            choice=raw['choices'][0];reason,answer=sections(choice['message'],thinking)
            return {'status':'ok','id':row['id'],'seed':seed,'category':row['category'],'target_language':row['target_language'],'model':args.model,'revision':args.revision,'reasoning':reason,'final_answer':answer,'finish_reason':choice['finish_reason'],'elapsed':time.time()-start,'usage':raw.get('usage'),'review_only_flags':{'reasoning':review_flags(reason,row['target_language']),'answer':review_flags(answer,row['target_language'])},'raw_response':raw,'rubric':row['rubric'],'input_messages':messages,'conversation_group':row['conversation_group'],'turn':row['turn']}
        except Exception as exc:return {'status':'error','id':row['id'],'seed':seed,'type':type(exc).__name__,'error':str(exc)[:1000],'elapsed':time.time()-start}
    groups={}
    for row in rows:groups.setdefault(row['conversation_group'],[]).append(row)
    import threading
    lock=threading.Lock()
    def conversation(task):
        group,seed=task;history=[]
        for row in sorted(group,key=lambda r:r['turn']):
            base=messages_for(row,args.suite)
            if not history:history=[m for m in base if m['role']=='system']
            messages=history+[m for m in base if m['role']=='user']
            if (row['id'],seed) in prior_rows:
                result=prior_rows[(row['id'],seed)]
                assert result['input_messages']==messages, 'Resume history mismatch'
            else:
                result=run((row,seed,messages))
                with lock:
                    output.write(json.dumps(result,ensure_ascii=False)+'\n');output.flush();print(result['id'],result['status'],flush=True)
            if result['status']!='ok':return
            actual=result['raw_response']['choices'][0]['message']
            history=messages+[{'role':'assistant','content':actual.get('content') or ''}]
    with args.output.open('a') as output,concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(conversation,[(group,seed) for group in groups.values() for seed in seeds]))

if __name__=='__main__':main()
