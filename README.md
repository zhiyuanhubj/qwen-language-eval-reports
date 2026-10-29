# Qwen language evaluation reports

<!-- game-every500-latest -->
**Game Stage1每500step新评测：** [每500step至9500的报告与详细分析](game-stage1-3shift-every500-20261026/README.md) · [实时进度](game-stage1-3shift-every500-20261026/progress.md)。旧500–3500复用。

<!-- last-stage1-stage2-checkpoint-logs -->
**旧Stage1 / Stage2最后checkpoint完整日志：** [Stage1 step4100 / Stage2 step4000全部题目下载包](last-checkpoint-full-logs/README.md)，含四组设置、完整thinking和final、评分及运行日志。

<!-- stage1-2000plus-latest -->
**Stage1-3Shift 2000至3800每100step补测：** [V2完整对照报告](game-stage1-3shift-2000plus-20261023/report-v2-modes.html) · [实时进度](game-stage1-3shift-2000plus-20261023/progress.md)。复用2800，新增18个checkpoint按计划分批执行，当前状态见进度快照。

<!-- stage1-100-2800-latest -->
**Stage1-3Shift 先前补测（100 / 2800）：** [五个 checkpoint 对照报告](game-stage1-3shift-100-2800-20261023/report-v2-modes.html) · [实时快照进度](game-stage1-3shift-100-2800-20261023/status/progress.json)。沿用三个subset和四种设置；新增结果在运行中，未完成项明确标注。

Evaluation reports for the Qwen3.5-9B base, historical training checkpoints,
stage-2 checkpoints, and A/B language-regression experiments.

**Status: grading in progress. This is not a final result release.**

- [Thinking report](thinking/report.html)
- [Non-thinking report (without think tags)](notags/report.html)
- [Snapshot timestamps and completion counts](status.json)

Download an HTML file and open it in a browser; GitHub's file view displays source.
The reports are self-contained. GitHub Pages has not been enabled.

Each mode covers 89 models × 2 sampling settings × 246 prompts = 43,788 cases.
The three subsets are diagnostic128, benchmark72, and friend46.
Sampling settings are temperature 0.6/top-p 0.95 and temperature 1/top-p 1.
Candidate inference uses BF16, seed 42, a 32,768-token context, and a
16,384-token output limit. Existing successful outputs are retained during resume.

Partial scores remain provisional. Generated answers and completed grading are
separate counts. Context-exhaustion failures are retained; they are not successful
answers. Model-assisted rubric scores are not benchmark exact-match accuracy.
The HTML reports include detailed scoring caveats and objective scores where available.

The evidence directory includes evaluation questions, complete raw model outputs,
per-question scores, errors, prompt templates, and run logs, individually compressed
with gzip. Model weights and training datasets are excluded. The manifest records
file sizes, SHA-256 checksums, and the snapshot time. Later scores may be pending.
The repository is public as requested by its owner.


[Downloadable questions, answers, scores and logs](evidence/README.md) · [File manifest and checksums](evidence/manifest.json)


## 中英文固定题跨 checkpoint 肉眼对照

三个 subset 均有题目及已生成测试记录上传。按目标回答语言统计：diagnostic128 中文64/英文64；benchmark72 英文72；friend46 中文18/英文28。目标语言不代表每个提示词都只含一种语言。上传完成不代表所有评分完成。

[下载交互对照 HTML](https://raw.githubusercontent.com/zhiyuanhubj/qwen-language-eval-reports/main/manual-review/index.html) 后用浏览器打开，可离线查看全部320条记录：5道中文、5道英文，8个模型节点，Thinking/NoTags，两组采样设置。

[评分CSV](manual-review/scores.csv) · [完整原始JSON](manual-review/comparison.json) · [选题规则和来源校验](manual-review/manifest.json)

以下文本可直接在GitHub阅读，展示Thinking、T=0.6/p=0.95下每题8个模型节点的完整thinking、最终答案、五项评分及理由；其余设置见HTML。

- [text-00-zh · diagnostic128](manual-review/text-00-zh.txt)
- [text-04-zh · diagnostic128](manual-review/text-04-zh.txt)
- [text-08-zh · diagnostic128](manual-review/text-08-zh.txt)
- [friend-C05 · friend46](manual-review/friend-C05.txt)
- [friend-C15 · friend46](manual-review/friend-C15.txt)
- [text-00-en · diagnostic128](manual-review/text-00-en.txt)
- [text-04-en · diagnostic128](manual-review/text-04-en.txt)
- [text-08-en · diagnostic128](manual-review/text-08-en.txt)
- [benchmark-gsm8k-153 · benchmark72](manual-review/benchmark-gsm8k-153.txt)
- [benchmark-arc-challenge-40 · benchmark72](manual-review/benchmark-arc-challenge-40.txt)


## OneVision 清洗与中文翻译代码

[启动说明、按 subset 分工、清洗及翻译代码](onevision-pipeline/README.md)。包含一节点八个 Qwen 服务、32 路并发和跨文件请求池；不包含模型和原始数据。
