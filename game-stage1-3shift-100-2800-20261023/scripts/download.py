import concurrent.futures, hashlib, json, os, subprocess, time
from pathlib import Path
from huggingface_hub import HfApi

D = Path(__file__).resolve().parent
plan = json.loads((D / 'plan.json').read_text())

def download(item):
    label = item['label']; target = Path(plan['model_root']) / label
    receipt = D / 'status' / (label + '.weights.json')
    if receipt.exists() and json.loads(receipt.read_text()).get('verified'):
        return
    info = HfApi().model_info(item['repo'], revision=item['revision'], files_metadata=True)
    assert info.sha == item['revision']
    files = [f for f in info.siblings if '/' not in f.rfilename and f.rfilename.endswith(('.json', '.jinja', '.safetensors', '.model', '.txt'))]
    env = dict(os.environ, HF_HUB_DISABLE_PROGRESS_BARS='1', HF_HUB_DISABLE_XET='1')
    subprocess.run(['/fsx/home/zhiyuan/.local/bin/hf', 'download', item['repo'],
                    *[f.rfilename for f in files], '--revision', item['revision'],
                    '--local-dir', str(target), '--max-workers', '3'], env=env, check=True)
    verified = []
    for f in files:
        path = target / f.rfilename
        assert path.stat().st_size == f.size
        digest = hashlib.sha256()
        blob = hashlib.sha1(('blob ' + str(f.size) + '\0').encode())
        with path.open('rb') as stream:
            while chunk := stream.read(16 * 1024 ** 2):
                digest.update(chunk); blob.update(chunk)
        if f.lfs:
            assert digest.hexdigest() == f.lfs.sha256, f.rfilename
        else:
            assert blob.hexdigest() == f.blob_id, f.rfilename
        verified.append({'file': f.rfilename, 'bytes': f.size, 'sha256': digest.hexdigest()})
    receipt.write_text(json.dumps({'verified': True, **item, 'files': verified, 'utc': time.time()}, indent=2))

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(download, plan['items']))
(D / 'status' / 'downloads-ready.json').write_text(json.dumps({'utc': time.time(), 'verified': True}))
