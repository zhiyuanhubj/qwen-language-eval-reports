# OneVision 清洗与中文 QA 翻译

这是现有运行代码的可移植副本（2026-10-17），包含图文清洗、Qwen 中文翻译、服务启动和按 subset 分工。原有评测报告不受影响。仓库只上传代码、测试和不含样本内容的 subset 统计；不包含模型权重、图片、QA 明细、凭据或机器上的运行状态。

## 两个阶段

1. `clean.py`：DeepSeek-V4.1-Flash 看原图并审核整个对话；两次肯定审核才保留，分歧进入两次深度复审。五项布尔条件全部通过才保留；confidence 只记录，不设置信心阈值。失败、未完成和需复核的记录不当作合格数据。
2. `translate.py` / `run_translation.py`：Qwen3.8-27B 翻译清洗后的 QA，关闭 thinking，保留图片及非 messages 列。代码、公式、数字和 OCR 等受保护内容按规则保留。只输出通过自动校验的行；自动通过仍不代表经过人工语义审核。

翻译：一张 H200 一个 TP1 BF16 服务，一个 8 卡节点启动 8 个服务，每服务最多 32 路请求。两个文件共享同一个有上限的请求池，缓解文件末尾长请求导致的空闲，但不能完全消除长尾。逐行缓存、文件锁和原子 Parquet 写入支持断点续跑。

## 环境与模型服务

客户端 Python 3.10+：

```bash
python -m pip install -r requirements.txt
```

服务端需要 Docker、NVIDIA Container Toolkit、已下载的完整模型目录，以及**兼容这两个模型的 vLLM 镜像**。本次验证使用 vLLM `0.31.1rc1.dev253+g7d0b4e57a`，本地镜像 ID `sha256:2b3b0fe155011cbca03828e35fe1a483c1b5c9cf44c807cdee6ab51db734d553`。这是本地镜像 ID，不是保证可从公共仓库拉取的 registry digest；同事需要从已有环境导出/传递镜像，或构建匹配的版本。不能假设任意 `latest` 支持这些模型。

`serve.py` 可打印实际 Docker 命令，也可执行；已有同名容器会报错，不会替你删除。运行前确认卡和端口已分配给自己。服务只绑定本机回环地址；以下客户端在服务所在节点运行。

```bash
# 按实际模型目录及已有镜像设置；不要把密钥写入命令或仓库。
export VLLM_IMAGE='your-compatible-vllm-image'
python serve.py translate --model-path /models/Qwen3.8-27B \
  --image "$VLLM_IMAGE" --name ov-qwen --dry-run
# 检查打印出的命令后，去掉 --dry-run 执行；端口 31400..31407。

python serve.py clean --model-path /models/DeepSeek-V4.1-Flash \
  --image "$VLLM_IMAGE" --name ov-clean --dry-run
# 清洗使用独立的 8 张 H200，TP4 × DP2、CPU offload；已验证机器约 2 TiB RAM。
# 去掉 --dry-run 启动后等待 /v1/models 返回 DeepSeek-V4.1-Flash；端口 30240。
```

Qwen 验证权重版本：`Qwen/Qwen3.8-27B` revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`。模型权重访问权限与镜像分发由各自环境提供。8 卡 Qwen 服务和 8 卡清洗服务不能同时占用同一组卡。

## 清洗数据格式与运行

输入使用当前 OneVision Parquet 格式，含 `messages` 和图片字段；图片解析逻辑见 `clean.py`。本项目已有采样集使用 `canonical_index.json` 指定各 subset 的行数，**不是任意 Hugging Face 数据集都可以直接套用**。生成 inventory 时要求：

```json
{"datasets":[{"canonical_name":"subset_name","stats":{"output_rows":1000}}]}
```

source 目录下放 `canonical_index.json` 和 `subset_name/*.parquet`。清洗任务 ID 从相对文件名、起始行、行数生成，跨机器必须使用同一 inventory 和相同源文件。不要自行修改文件名、任务大小、规则或行顺序后合并结果。

```bash
python clean.py inventory --source /data/onevision --output work/filter --task-rows 256
python clean.py worker --source /data/onevision --output work/filter \
  --clean work/clean --cache work/source-cache --endpoint http://127.0.0.1:30240 \
  --job colleague-a --rank 0 --concurrency 64
python clean.py report --output work/filter
```

默认读取本地源文件；只有明确传入 `--data-url` 时才从该 HTTP 数据源补取缺失文件。`server_settings.json`、`review_settings.json` 固定本次 V4.1 复审策略。`--only-task TASK_ID` 用于指定失败任务恢复，不代表整个集合完成。

## 按 subset 分给同事

**可以。推荐先由一人生成完整 inventory，再按 subset 分发。**

```bash
python split_subsets.py work/filter/inventory.json --parts 3 \
  --completed-dir work/filter/tasks --output work/assignments
# 也可只选几个 subset（名称必须存在）：
# python split_subsets.py work/filter/inventory.json --parts 2 \
#   --subsets docvqa_train,chartqa,tallyqa --output work/selected-assignments
```

按行数贪心平衡，各 subset 整体交给一人；不拆同一个 subset，不重复任务，保留原 task key。行数只粗略估计工作量，图文复杂度不同会导致耗时不均。脚本拒绝未知 subset、空分配或覆盖已有分工目录。

**正在运行的主任务也必须同步排除分出去的任务。** 分工脚本只生成计划，不会修改线上任务；异地机器的文件锁不互通。先暂停/调整相关主 worker，让主任务和同事分别只读取自己的分片 inventory，再开始执行，否则会重复调用模型。

每人拿到：

- 自己的 `part-XX/inventory.json`、`subsets.txt`、`source-files.txt`。
- `source-files.txt` 列出的原始 Parquet（通过已有内部存储传递，保留相对路径）。
- 同一版本代码、模型和镜像。

```bash
# 同事只运行自己的 inventory，不重新生成全量清单。
python clean.py worker --source /data/onevision \
  --output work/assignments/part-01 --clean work/clean-part-01 \
  --cache work/cache-part-01 --job colleague-a --concurrency 64
```

交回 `clean-part-01/` 和 `part-01/tasks/` 下的 decisions / summary / done 文件，以及 `inventory.json`。先检查父清单哈希、policy hash、ruleset、模型版本、任务 key 集合无交集且覆盖分工，并确认 `unresolved_errors == 0`，再合并。**不要仅合并 Parquet 而丢失审核记录，也不要覆盖同名结果。** 最简单的交接方式是各分工目录保持独立，分别翻译；如移动数据，注意 `done.json` 中 `clean_file` 是原路径，必须核对它与实际源文件对应关系。

`subset-summary.csv` 是本次源清单的 subset 行数/任务数统计，可用于协商分工；它不是未完成任务列表，也不是原始全量 OneVision 的大小。已经完成的 subset 不应再次分发；使用 `--completed-dir` 按当前 done 状态筛掉已完成 task。

## 中文翻译

使用清洗阶段实际产生的目录及审核记录：

```bash
python run_translation.py --source work/clean-part-01 \
  --decisions work/assignments/part-01/tasks --work-dir work/translation-part-01 \
  --ports 31400,31401,31402,31403,31404,31405,31406,31407 \
  --concurrency 32 --file-workers 2 --worker-id 1
# 仅翻译指定 subset 时添加 --subsets subset_a,subset_b。
# 单卡测试：--ports 31400；服务端上限必须 >= 客户端并发。
```

每个机器/主管进程使用独立 work-dir。退出后用相同命令恢复。运行状态、逐行原始响应、错误和审核标记在 `work-dir/state/`，合格 Parquet 在 `work-dir/translated/`，日志在 `work-dir/logs/`。输入文件发生变化会拒绝复用旧结果。最后一个端口优先处理重试，其余优先新数据；失败任务有冷却时间。程序持续轮询新清洗输出，不会在一轮完成后自动退出。

启动服务后先检查 `/v1/models`。每个翻译 worker 会做三项小样例检查，但不能代替真实数据的语义抽检。持续观察合格条数/小时、错误原因、截断、GPU 利用率和磁盘配额；不要把 token/s 当作合格数据产出。状态文件按整文件完成更新，短窗口可能呈阶梯状。

## 验证与已知限制

```bash
python tests/test_portable.py
for f in tests/test_*validation.py tests/test_boolean_labels.py tests/test_chart_labels.py \
  tests/test_exact_formula.py tests/test_exact_ocr.py tests/test_python_context.py; do
  PYTHONPATH=. python "$f"
done
```

已验证运行配置来自现有集群。可移植启动器做了命令构造和离线测试，**没有在同事的硬件/镜像上完成端到端验收**。翻译校验仍可能漏掉中文语义错误；错误行和 review 行不等于已完成中文化。

固定 48 条真实 QA 的历史小样本：8 路约 65–67 秒、16 路 41.7 秒、32 路 29.8 秒；两个文件共用 8 路请求池约 71.6 秒，单文件基线约 112–114 秒。跨文件测试期间同节点其他服务有启动活动，不能当成全量性能保证。文件长尾、输出质量重试、存储配额和调度中断都仍会影响有效产能。
