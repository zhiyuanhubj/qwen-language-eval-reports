import atexit, concurrent.futures, hashlib, json, os, signal, socket, subprocess, sys, time, traceback
from pathlib import Path
import requests

D = Path(__file__).resolve().parent
PY = sys.executable
PLAN = json.loads((D/'plan.json').read_text())
JOB = os.environ['SLURM_JOB_ID']
IMAGE = 'vllm/vllm-openai:zhiyuan-v41-7d0b4e57a'
IMAGE_ID = 'sha256:2b3b0fe155011cbca03828e35fe1a483c1b5c9cf44c807cdee6ab51db734d553'
DOCKER = ['env','-u','DOCKER_HOST','-u','DOCKER_CONTEXT','-u','DOCKER_TLS','-u','DOCKER_TLS_VERIFY','-u','DOCKER_CERT_PATH','docker','--host=unix:///var/run/docker.sock']
containers = set()

def status(label, phase, **kw):
    path = D/'status'/(label+'.json'); tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'utc':time.time(),'job':JOB,'node':socket.gethostname(),'phase':phase,**kw},indent=2)); tmp.replace(path)
    print(label,phase,flush=True)

def stop(name):
    if name not in containers: return
    p=subprocess.run(DOCKER+['inspect',name],capture_output=True,text=True)
    if p.returncode == 0:
        info=json.loads(p.stdout)[0]
        assert info['Config']['Labels'].get('zhiyuan.game-language-job') == JOB
        subprocess.run(DOCKER+['stop','-t','20',name],stdout=subprocess.DEVNULL)
    containers.discard(name)

def cleanup():
    for name in list(containers): stop(name)
atexit.register(cleanup)
def terminate(*_): raise SystemExit('allocation termination')
signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)

def ready(port, name, process):
    deadline=time.monotonic()+2400
    while time.monotonic()<deadline:
        if process.poll() is not None: raise RuntimeError(f'{name} exited {process.returncode}')
        try:
            r=requests.get(f'http://127.0.0.1:{port}/v1/models',timeout=5)
            if r.ok and name in [m['id'] for m in r.json()['data']]: return
        except requests.RequestException: pass
        time.sleep(5)
    raise RuntimeError('model readiness timeout; inspect server log')

def success(path):
    result={}
    if path.exists():
        for line in path.read_text().splitlines():
            try: row=json.loads(line)
            except ValueError: continue
            if row.get('status')=='ok': result[row['id']]=row
    return result

def candidate(task):
    gpu,item,kinds=task;label=item['label']; model=D/'models'/label;port=19800+gpu
    state_label=label+'-'+kinds[0]
    receipt=json.loads((D/'status'/(label+'.weights.json')).read_text())
    assert receipt['verified'] and receipt['revision']==item['revision']
    for f in receipt['files']: assert (model/f['file']).stat().st_size==f['bytes']
    failures=[]
    for kind in kinds:
        modes=[m for m in PLAN['modes'] if m.startswith('thinking' if kind=='thinking' else 'nonthinking')]
        if all(set(success(D/m/(label+'.jsonl')))==expected for m in modes):continue
        templates=D/'templates'/kind;templates.mkdir(exist_ok=True)
        subprocess.run([PY,str(D/'scripts'/(kind+'_prepare_templates.py')),str(model),str(templates),label],check=True)
        name=f'game-language-{JOB}-{gpu}-{kind}';containers.add(name)
        try:
            status(state_label,'loading',mode_family=kind,gpu=gpu)
            with (D/'logs'/(label+'.'+kind+'.server.log')).open('a') as log:
                p=subprocess.Popen(DOCKER+['run','--rm','--name',name,'--label','zhiyuan.game-language-job='+JOB,
                    '--gpus','device='+str(gpu),'--network','host','--ipc','host','-v','/fsx:/fsx:ro',
                    '--entrypoint','vllm',IMAGE,'serve',str(model),'--served-model-name',label,
                    '--chat-template',str(templates/(label+'.jinja')),'--host','127.0.0.1','--port',str(port),
                    '--dtype','bfloat16','--max-model-len','32768','--max-num-seqs','16',
                    '--gpu-memory-utilization','0.85','--generation-config','vllm','--enforce-eager'],stdout=log,stderr=subprocess.STDOUT)
                ready(port,label,p)
                for mode in modes:
                    if set(success(D/mode/(label+'.jsonl')))==expected:continue
                    for smoke in [True,False]:
                        status(state_label,'smoke' if smoke else 'evaluating',mode=mode,gpu=gpu)
                        path=D/mode/(label+('.smoke' if smoke else '')+'.jsonl')
                        cmd=[PY,str(D/'scripts'/(kind+'_run_eval.py')),'--suite',PLAN['suite'],'--output',str(path),
                             '--model',label,'--revision',item['revision'],'--base-url',f'http://127.0.0.1:{port}/v1',
                             '--authorization',str(D/'authorization.json'),'--workers','8','--mode',mode]
                        if smoke:cmd.append('--smoke')
                        with (D/'logs'/(label+'.'+mode+'.client.log')).open('a') as clientlog:
                            subprocess.run(cmd,check=True,stdout=clientlog,stderr=subprocess.STDOUT)
                        got=set(success(path))
                        if smoke and len(got)!=4:raise RuntimeError('smoke failed; see raw errors')
                        if not smoke:
                            subprocess.run([PY,str(D/'scripts'/(kind+'_score_benchmark_exact.py')),'--suite',PLAN['suite'],
                                '--responses',str(path),'--output',str(path.with_suffix('.objective.json'))],check=True)
                            if got != expected: failures.append({'mode':mode,'success':len(got),'expected':len(expected)})
                        subprocess.run([PY,str(D/'report.py')],check=True)
        except Exception as e:
            failures.append({'family':kind,'error':repr(e)});traceback.print_exc()
        finally:stop(name)
    status(state_label,'generation_complete' if not failures else 'generation_partial',failures=failures)
    return failures

subprocess.run(DOCKER+['info','--format','{{.ServerVersion}}'],check=True)
used=[int(x) for x in subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).split()]
assert len(used)==8 and max(used)<2000,('Refuse GPU conflict',used)
if subprocess.run(DOCKER+['image','inspect',IMAGE],capture_output=True).returncode:
    subprocess.run(DOCKER+['load','-i','/fsx/home/zhiyuan/llava-quality-filter-20261010/images/v41-nightly-7d0b4e57a.tar.gz'],check=True)
assert subprocess.check_output(DOCKER+['image','inspect',IMAGE,'--format','{{.Id}}'],text=True).strip()==IMAGE_ID
while not (D/'status/downloads-ready.json').exists():
    status('allocation','waiting_downloads');time.sleep(30)
manifest=json.loads((Path(PLAN['suite'])/'manifest.json').read_text())
assert hashlib.sha256((Path(PLAN['suite'])/'manifest.json').read_bytes()).hexdigest()==PLAN['suite_manifest_sha256']
for f,digest in manifest['hashes'].items():assert hashlib.sha256((Path(PLAN['suite'])/f).read_bytes()).hexdigest()==digest
expected={r['id'] for r in map(json.loads,(Path(PLAN['suite'])/'prompts.jsonl').read_text().splitlines())}
assert len(expected)==246
tasks=[(gpu,item,[kind]) for gpu,(item,kind) in enumerate((item,kind) for item in PLAN['items'] for kind in ['thinking','notags'])]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    results=list(pool.map(candidate,tasks))
complete=all(set(success(D/m/(i['label']+'.jsonl')))==expected for i in PLAN['items'] for m in PLAN['modes'])
if complete:(D/'complete.json').write_text(json.dumps({'utc':time.time(),'cases':2952,'generation_complete':True}))
# A separate evaluation judge; never invoke or restart the paused cleaning pipeline.
status('allocation','loading_judge',generation_complete=complete)
name='game-language-judge-'+JOB;containers.add(name)
cache=Path('/opt/dlami/nvme')/('zhiyuan-game-language-'+JOB);cache.mkdir(exist_ok=True)
with (D/'logs/judge-server.log').open('a') as log:
    command=DOCKER+['run','--rm','--name',name,'--label','zhiyuan.game-language-job='+JOB,'--gpus','all',
        '--network','host','--ipc','host','--ulimit','memlock=-1','--ulimit','stack=67108864',
        '-v','/fsx/data/zhiyuan/models/DeepSeek-V4.1-Flash:/model:ro','-v',str(cache)+':/root/.cache',
        '-e','HF_HUB_OFFLINE=1','-e','TRANSFORMERS_OFFLINE=1','-e','OMP_NUM_THREADS=8',
        '-e','VLLM_ENGINE_READY_TIMEOUT_S=3600',IMAGE,'--model','/model','--served-model-name','DeepSeek-V4.1-Flash',
        '--trust-remote-code','--tensor-parallel-size','4','--data-parallel-size','2',
        '--tokenizer-mode','deepseek_v41','--reasoning-parser','deepseek_v41','--max-model-len','65536',
        '--max-num-seqs','64','--max-num-batched-tokens','16384','--gpu-memory-utilization','0.90',
        '--enable-prefix-caching','--engram-config','{"cpu_offload": true}',
        '--speculative-config','{"method":"dspark","num_speculative_tokens":5,"draft_sample_method":"probabilistic","rejection_sample_method":"block","enable_adaptive_verification":true}',
        '--mm-encoder-tp-mode','data','--limit-mm-per-prompt','{"image":8}',
        '--host','127.0.0.1','--port','30240']
    (D/'status/judge-runtime.json').write_text(json.dumps({'image':IMAGE,'image_id':IMAGE_ID,'command':command,'candidate_context':32768,'judge_context':65536,'note':'Longer judge context retains complete candidate text; candidate evaluation context is unchanged.'},indent=2))
    p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    try:
        ready(30240,'DeepSeek-V4.1-Flash',p)
        status('allocation','grading',generation_complete=complete)
        judge=subprocess.Popen([PY,str(D/'scripts/judge.py')],stdout=open(D/'logs/judge.log','a'),stderr=subprocess.STDOUT)
        # With generation errors, grade all generated cases without claiming full completion.
        while judge.poll() is None:
            if p.poll() is not None:raise RuntimeError('Judge server exited')
            if not complete:
                pending=False
                for i in PLAN['items']:
                    for mode in PLAN['modes']:
                        pending |= bool(set(success(D/mode/(i['label']+'.jsonl')))-set(success(D/'scores100'/(mode+'-'+i['label']+'.jsonl'))))
                if not pending:judge.terminate();break
            time.sleep(20)
        result=judge.wait()
        if complete and result:raise RuntimeError('Scoring exited '+str(result))
    finally:stop(name)
subprocess.run([PY,str(D/'report.py')],check=True)
if complete:
    assert all(set(success(D/'scores100'/(m+'-'+i['label']+'.jsonl')))==expected for i in PLAN['items'] for m in PLAN['modes']), 'Scoring coverage incomplete'
status('allocation','finished' if complete else 'partial',generation_complete=complete)
