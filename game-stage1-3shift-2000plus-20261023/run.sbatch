#!/bin/bash
#SBATCH --job-name=qwen-game-2000plus-language
#SBATCH --account=xgen-mm
#SBATCH --partition=ml.p5en.48xlarge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --gres=gpu:h200:8
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --time=24:00:00
#SBATCH --output=/fsx/home/zhiyuan/language-pilot-20261011/game-stage1-3shift-2000plus-20261023/logs/slurm-%j.log
set -euo pipefail
for attempt in {1..120}; do
 if [[ -f /fsx/home/zhiyuan/language-pilot-20261011/game-stage1-3shift-2000plus-20261023/status/worker-ready.json ]]; then
  exec /fsx/home/zhiyuan/miniconda3/envs/megatron-sft/bin/python -u /fsx/home/zhiyuan/language-pilot-20261011/game-stage1-3shift-2000plus-20261023/worker.py
 fi
 sleep 5
done
exit 1
