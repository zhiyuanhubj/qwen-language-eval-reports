import json, os, socket, subprocess, time, urllib.request
from pathlib import Path
D=Path(__file__).resolve().parent
assert os.environ['SLURM_JOB_ID']=='2733' and socket.gethostname()=='ip-10-1-25-253'
plan=json.loads((D/'status/existing-node-handoff.json').read_text())
command=plan['previous_launch']['command']
assert command[command.index('--name')+1]=='zhiyuan-beam-bf16-2733'
used=[int(x) for x in subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).split()]
assert max(used)<2000,('Refuse conflicting GPU restoration',used)
with (D/'logs/beam-restore.log').open('a') as log:
    p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline=time.monotonic()+1800
        while time.monotonic()<deadline:
            if p.poll() is not None:raise RuntimeError('Beam restore exited '+str(p.returncode))
            try:
                data=json.load(opener.open('http://127.0.0.1:31328/v1/models',timeout=5))
                if any(x['id']=='Beam-1.0-501B-A23B' for x in data['data']):
                    (D/'status/beam-restored.json').write_text(json.dumps({'utc':time.time(),'job':2733,'endpoint_ready':True,'original_command_restored':True},indent=2));break
            except OSError:pass
            time.sleep(10)
        else:raise RuntimeError('Beam restoration readiness timeout')
        raise SystemExit(p.wait())
    finally:
        subprocess.run(['docker','stop','-t','20','zhiyuan-beam-bf16-2733'],stdout=subprocess.DEVNULL)
