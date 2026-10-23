# Stage1-3Shift：补测 checkpoint100 / 2800

[V2 完整对照报告：100 / 500 / 1000 / 1500 / 2800](report-v2-modes.html) · [补测进度](status/progress.json) · [固定配置](plan.json) · [全部题目、输出、评分与日志](evidence/manifest.json)

下载 report-v2-modes.html 后用浏览器打开。第二列明确标注 Thinking / NoTags。补测沿用原 diagnostic128 / benchmark72 / friend46，共246题 × 2 checkpoints × 4设置 =1968条回答。每个checkpoint均测 Thinking/NoTags、T0.6/p0.95与T1/p1。BF16、seed42、context32768、output16384不变。

同一已有节点2733的8张空闲GPU并行生成，随后切换同一V4.1评分模型。原rubric及候选原文不变，JSON schema仅限制评分解释和证据长度，避免复制长重复回答导致尾部卡住。评分输出预算8192，若耗尽则记录重试；每条评分保存实际预算、完整响应和原回答SHA。单seed模型辅助分数不等于人工准确率。

报告合并之前500/1000/1500结果用于对照，旧实验原文件保留。此目录summary.json只含新增100/2800；未生成、未评分项目仍标待完成。模型权重不上传。
