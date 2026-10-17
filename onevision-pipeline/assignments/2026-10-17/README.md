# 正式分工：同事 1/3，zhiyuan 2/3

分配对象是 **OneVision 剩余全量清洗任务**，不是已清洗约 10% 数据的中文翻译。以 2026-10-17 生成清单时的未完成源行数为准；不再包含当时已完成的 697,565 行。数据和任务 ID 不变。按行数分配不保证两组实际耗时正好为 1:2。

| 执行方 | 剩余源行数 | 任务数 | 占比 |
|---|---:|---:|---:|
| 同事 | 1,836,448 | 7,177 | 33.333% |
| zhiyuan | 3,672,947 | 15,043 | 66.667% |

**同事负责以下 7 个 subset 的清单内任务：**

- Evol-Instruct-GPT4-Turbo
- Super-CLEVR
- gqa
- ifeval_like
- open_orca
- openmathinstruct
- textocr_gpt4v

zhiyuan 负责剩余 91 个未完成 subset，完整名单见 [zhiyuan/subsets.txt](zhiyuan/subsets.txt)。没有出现在两份名单中的 subset 在快照时已完成，不需要重跑。当前运行和补跑中的 subset 保留在 zhiyuan 这边。

## 同事启动

从 `onevision-pipeline/` 目录运行，先按上一级 README 启动 V4.1 服务。只传递 [colleagues/source-files.txt](colleagues/source-files.txt) 中的原始 Parquet，并保持相对目录结构。原始数据需要通过内部存储传递，GitHub 仅提供清单，不包含数据。

```bash
python clean.py worker \
  --source /data/onevision \
  --inventory assignments/2026-10-17/colleagues/inventory.json \
  --output work/colleagues-filter \
  --clean work/colleagues-clean \
  --cache work/colleagues-cache \
  --endpoint http://127.0.0.1:30240 \
  --job colleagues --rank 0 --concurrency 64
```

如多位同事共同完成这 1/3：再次用 `split_subsets.py` 拆 `colleagues/inventory.json`，每人领取不相交分片；不要在独立存储上同时跑同一完整清单。共享文件锁只在共同文件系统上防止冲突。

## zhiyuan 的启动范围

本次分工已应用到线上 2733、2866 两个清洗客户端：启动参数显式指向 zhiyuan 清单，同事的 7 个 subset 不再由这两个客户端领取。后续续期清洗进程使用同一分工。

使用 `--inventory assignments/2026-10-17/zhiyuan/inventory.json`，并保留原有 `--output` 与 `--clean`，从已存在的记录恢复。主清单仍保留完整数据集，运行范围由显式 `--inventory` 约束；分片完成只写 `complete-<job>.json`，不会错误地标记全量完成。

## 交接与验收

交回自己的 `work/colleagues-filter/tasks/`、`work/colleagues-clean/`、节点日志和所用清单、代码版本。校验 task key 在同事清单内、各任务 `unresolved_errors=0`、policy hash 和 ruleset 一致；reject/review 是有效审核结论，不应伪装成 keep。

分片清单保留源文件名/行范围和 policy hash，但已移除本集群的历史审核绝对路径。同事环境默认独立完成审核，不会读取主机历史缓存。不要擅自降低复审条件。

分工不自动代表同事已开跑；同事领取、数据传输和部署仍需各自落实。当前约 30 万条中文翻译及剩余翻译队列不属于这次清洗分工。
