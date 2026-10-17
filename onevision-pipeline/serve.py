"""Explicit Docker startup commands; --dry-run prints commands without launching."""
import argparse,subprocess,shlex
from pathlib import Path

def commands(a):
 gpus=a.gpus.split(',');assert gpus and len(gpus)==len(set(gpus)) and all(g.isdigit() for g in gpus)
 assert 1<=a.max_num_seqs<=32
 base=['docker','run','-d','--network','host','--ipc','host','--ulimit','memlock=-1','--ulimit','stack=67108864','-v',str(a.model_path.resolve())+':/model:ro','-e','HF_HUB_OFFLINE=1']
 if a.role=='translate':
  return [base+['--name',f'{a.name}-{i}','--gpus','device='+g,'-e','OMP_NUM_THREADS=4',a.image,'--model','/model','--served-model-name','Qwen3.8-27B','--host','127.0.0.1','--port',str(a.port+i),'--tensor-parallel-size','1','--dtype','bfloat16','--max-model-len','32768','--max-num-seqs',str(a.max_num_seqs),'--max-num-batched-tokens','8192','--gpu-memory-utilization','0.88','--limit-mm-per-prompt','{"image":0,"video":0}'] for i,g in enumerate(gpus)]
 assert len(gpus)==8,'Validated cleaning configuration requires eight H200 GPUs'
 return [base+['--name',a.name,'--gpus','"device='+','.join(gpus)+'"','--shm-size','32g','-e','OMP_NUM_THREADS=8','-e','MKL_NUM_THREADS=8','-e','VLLM_ENGINE_READY_TIMEOUT_S=3600',a.image,'--model','/model','--served-model-name','DeepSeek-V4.1-Flash','--trust-remote-code','--tokenizer-mode','deepseek_v41','--reasoning-parser','deepseek_v41','--tensor-parallel-size','4','--data-parallel-size','2','--mm-encoder-tp-mode','data','--max-model-len','32768','--max-num-seqs','128','--max-num-batched-tokens','16384','--gpu-memory-utilization','0.90','--enable-prefix-caching','--engram-config','{"cpu_offload":true}','--speculative-config','{"method":"dspark","num_speculative_tokens":5,"draft_sample_method":"probabilistic","rejection_sample_method":"block","enable_adaptive_verification":true}','--limit-mm-per-prompt','{"image":8}','--host','127.0.0.1','--port',str(a.port)]]
def main():
 p=argparse.ArgumentParser();p.add_argument('role',choices=['translate','clean']);p.add_argument('--model-path',type=Path,required=True);p.add_argument('--image',required=True,help='Compatible local/registry vLLM image; preferably pinned by digest');p.add_argument('--gpus',default='0,1,2,3,4,5,6,7');p.add_argument('--port',type=int);p.add_argument('--name',default='onevision');p.add_argument('--max-num-seqs',type=int,default=32);p.add_argument('--dry-run',action='store_true');a=p.parse_args();a.port=a.port or (31400 if a.role=='translate' else 30240)
 for cmd in commands(a):
  print(shlex.join(cmd),flush=True)
  if not a.dry_run:
   assert a.model_path.is_dir(),'Model directory missing'
   subprocess.run(cmd,check=True)
if __name__=='__main__':main()
