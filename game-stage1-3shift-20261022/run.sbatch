#!/bin/bash
#SBATCH --job-name=qwen-game-language-500-1500
#SBATCH --partition=ml.p5en.48xlarge-low
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --gres=gpu:h200:8
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --time=04:00:00
#SBATCH --output=/fsx/home/zhiyuan/language-pilot-20261011/game-stage1-3shift-20261022/logs/slurm-%j.log
set -euo pipefail
exec /fsx/home/zhiyuan/miniconda3/envs/megatron-sft/bin/python -u /fsx/home/zhiyuan/language-pilot-20261011/game-stage1-3shift-20261022/run_node.py
