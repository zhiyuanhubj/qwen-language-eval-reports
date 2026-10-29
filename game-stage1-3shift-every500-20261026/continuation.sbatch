#!/bin/bash
#SBATCH --job-name=qwen-every500-6500-9500
#SBATCH --account=xgen-mm
#SBATCH --partition=ml.p5en.48xlarge
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --gpus-per-node=h200:8
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --time=08:00:00
#SBATCH --time-min=02:00:00
#SBATCH --requeue
#SBATCH --output=/fsx/home/zhiyuan/language-pilot-20261011/game-stage1-3shift-every500-20261026/logs/continuation-%j.log
set -euo pipefail
exec /fsx/home/zhiyuan/miniconda3/envs/megatron-sft/bin/python -u /fsx/home/zhiyuan/language-pilot-20261011/game-stage1-3shift-every500-20261026/queued_node_entry.py
