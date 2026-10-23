"""Refresh this evaluation's report and publish only its requested evidence."""
import gzip, hashlib, json, shutil, subprocess, sys, time, traceback
from pathlib import Path
D=Path(__file__).resolve().parent
W=Path('/tmp/qwen-game-100-2800-publish-20261023')
DEST=W/'game-stage1-3shift-100-2800-20261023'
job=json.loads((D/'status/submission.json').read_text())['job_id']

def command(args, **kw):
    return subprocess.run(args,check=True,text=True,capture_output=True,**kw)

def publish():
    # This is a private, disposable publishing worktree, never the user's checkout.
    assert W.name=='qwen-game-100-2800-publish-20261023' and (W/'.git').is_file()
    command(['git','fetch','origin','main'],cwd=W)
    command(['git','reset','--hard','origin/main'],cwd=W)
    DEST.mkdir(exist_ok=True)
    for name in ['plan.json','summary.json','report.html','report-v2-modes.html']:
        shutil.copy2(D/name,DEST/name)
    (DEST/'status').mkdir(exist_ok=True)
    for p in (D/'status').glob('*.json'):shutil.copy2(p,DEST/'status'/p.name)
    for p in [*D.glob('*.py'),*(D/'scripts').glob('*.py')]:
        target=DEST/'scripts'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
    evidence=DEST/'evidence';evidence.mkdir(exist_ok=True)
    sources=[]
    plan=json.loads((D/'plan.json').read_text())
    for mode in plan['modes']:
        sources.extend((D/mode).glob('*.json*'))
    sources.extend((D/'scores100').glob('*.json*'))
    sources.extend((D/'templates').rglob('*.json'))
    sources.extend((D/'templates').rglob('*.jinja'))
    sources.extend(p for p in (D/'logs').glob('*.log') if p.name!='download.log')
    files=[]
    for p in sources:
        relative=p.relative_to(D);target=evidence/(str(relative)+'.gz');target.parent.mkdir(parents=True,exist_ok=True)
        before=p.stat();data=p.read_bytes();after=p.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):continue
        if p.suffix=='.jsonl' and data and not data.endswith(b'\n'):continue
        target.write_bytes(gzip.compress(data,mtime=0))
        files.append({'path':str(relative)+'.gz','uncompressed_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    (DEST/'README.md').write_text('# Stage1-3Shift：补测 checkpoint100 / 2800\n\n[V2 完整对照报告：100 / 500 / 1000 / 1500 / 2800](report-v2-modes.html) · [补测进度](status/progress.json) · [固定配置](plan.json) · [全部题目、输出、评分与日志](evidence/manifest.json)\n\n下载 report-v2-modes.html 后用浏览器打开。第二列明确标注 Thinking / NoTags。补测沿用原 diagnostic128 / benchmark72 / friend46，共246题 × 2 checkpoints × 4设置 =1968条回答。每个checkpoint均测 Thinking/NoTags、T0.6/p0.95与T1/p1。BF16、seed42、context32768、output16384不变。\n\n同一已有节点2733的8张空闲GPU并行生成，随后切换同一V4.1评分模型。原rubric及候选原文不变，JSON schema仅限制评分解释和证据长度，避免复制长重复回答导致尾部卡住。评分输出预算8192，若耗尽则记录重试；每条评分保存实际预算、完整响应和原回答SHA。单seed模型辅助分数不等于人工准确率。\n\n报告合并之前500/1000/1500结果用于对照，旧实验原文件保留。此目录summary.json只含新增100/2800；未生成、未评分项目仍标待完成。模型权重不上传。\n')
    # Include the identical frozen question set once; do not copy model data.
    suite=Path(plan['suite'])
    for name in ['prompts.jsonl','manifest.json','benchmark-answers.json']:
        data=(suite/name).read_bytes()
        (evidence/(name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
        files.append({'path':name+'.gz','uncompressed_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    (evidence/'manifest.json').write_text(json.dumps({'utc':time.time(),'files':files},indent=2))
    command(['git','add','--','game-stage1-3shift-100-2800-20261023'],cwd=W)
    changed=subprocess.run(['git','diff','--cached','--quiet'],cwd=W).returncode
    if changed:
        command(['git','commit','-m','Update Stage1-3Shift language evaluation progress and evidence'],cwd=W)
        command(['git','push','origin','HEAD:main'],cwd=W)

last_publish=0
while True:
    terminal=False
    try:
        job=json.loads((D/'status/submission.json').read_text())['job_id']
        p=command(['squeue','-h','-j',str(job),'-o','%T|%S|%R'])
        scheduling=p.stdout.strip()
        if not scheduling:
            state=command(['sacct','-X','-j',str(job),'-n','-P','-o','State']).stdout.strip().splitlines()
            scheduling=state[0] if state else 'UNKNOWN'
            terminal=bool(state) and state[0].split('|')[0].split()[0] in ['COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED']
        task_exit=D/'status/task-exit.json'
        if task_exit.exists():terminal=True
        command([sys.executable,str(D/'report.py')])
        summary=json.loads((D/'summary.json').read_text())
        progress={'utc':time.time(),'job':job,'scheduler':scheduling,'terminal':terminal,
            'responses':sum(r['responses'] for r in summary['results']),
            'graded':sum(r['graded'] for r in summary['results']),'expected':1968}
        tail=D/'status/grading-tail.json'
        if tail.exists():progress['grading_tail']=json.loads(tail.read_text())
        (D/'status/progress.json').write_text(json.dumps(progress,indent=2))
        ready_to_finish=terminal and progress['graded']>=progress['responses']
        if time.time()-last_publish>=180 or ready_to_finish:
            publish();last_publish=time.time()
        print(json.dumps(progress),flush=True)
        if ready_to_finish:break
    except Exception:
        traceback.print_exc()
    time.sleep(30)
