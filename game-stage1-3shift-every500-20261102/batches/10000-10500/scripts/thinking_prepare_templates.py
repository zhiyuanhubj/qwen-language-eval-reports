import json,hashlib,sys
from pathlib import Path
from jinja2.sandbox import ImmutableSandboxedEnvironment
p=Path(sys.argv[1]);out=Path(sys.argv[2]);label=sys.argv[3];out.mkdir(exist_ok=True,parents=True)
c=json.loads((p/'tokenizer_config.json').read_text());native=(p/'chat_template.jinja').read_text() if (p/'chat_template.jinja').exists() else c['chat_template'];e=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True)
t="{% set pilot_native %}"+native+"{% endset %}{{ pilot_native }}{% if add_generation_prompt and not pilot_native.endswith('<think>\\n') %}{{ '<think>\\n' }}{% endif %}"
audits=[]
for messages in [[{'role':'user','content':'template audit'}],[{'role':'system','content':'Follow the user.'},{'role':'user','content':'audit'}],[{'role':'system','content':'Follow the user.'},{'role':'user','content':'first'},{'role':'assistant','content':'previous answer'},{'role':'user','content':'second'}],[{'role':'user','content':[{'type':'image','image':'dummy.png'},{'type':'text','text':'image audit'}]}]]:
 for mode in ['thinking-sampled','thinking-sampled-t1-p1']:
  text=e.from_string(t).render(messages=messages,add_generation_prompt=True,enable_thinking=True,pilot_mode=mode);assert text.endswith('<|im_start|>assistant\n<think>\n'),repr(text[-100:]);audits.append({'mode':mode,'messages':messages,'rendered_prompt':text,'open_think':True})
(out/(label+'.jinja')).write_text(t);(out/(label+'.template-audit.json')).write_text(json.dumps({'verified':True,'enable_thinking':True,'native_sha256':hashlib.sha256(native.encode()).hexdigest(),'sha256':hashlib.sha256(t.encode()).hexdigest(),'audits':audits},ensure_ascii=False,indent=2))
