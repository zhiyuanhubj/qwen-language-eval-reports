# Game Stage1-3Shift：每500step详细评测

[下载完整HTML](report-v2-modes.html) · [实时进度](progress.md) · [中英文配对分析](language-analysis.md) · [固定版本与配置](plan.json) · [题目、回答、评分和日志](evidence/manifest.json)

新增4000、4500、5000、5500、6000，共4920条正式回答，旧500至3500每500step结果复用。当前仓库最高6100，本轮按用户要求每500step测试到6000。HTML对照共12个checkpoint。旧Stage1/Stage2日志与本GameStage1仓库不同，不混用。

每个checkpoint固定原246题（diagnostic128、benchmark72、friend46）、Thinking/NoTags各T0.6/p0.95和T1/p1，BF16、seed42、context32768、output16384。每批最多2个checkpoint、8个单卡服务，随后原V4.1模型与原rubric逐题逐项评分。完整原文和失败记录保留，上下文超限不截断或更改条件，覆盖数明确显示。

直接使用已有节点2989。上一轮Muse接续任务已结束，本轮切换未中断活动Muse试验；全部批次结束后恢复原MuseNVFP4服务，不重新运行已完成的32条接续任务。其他两个MuseBF16节点保留。

中英文分析按相同问题ID与3500配对，分别列纯文字诊断和三个subset。分数为单seed模型辅助评价，不是人工准确率；综合分包含格式问题影响，不能把没有独立final都解释成知识遗忘。所有配对ID、覆盖数、五项指标和格式问题计数保留。分析随实际评分自动更新，不伪造待测项目结果。

原回答和模板不变，评分JSON schema仅限制解释/证据长度；遇字符串中未转义控制字符时无损读取并保留原始评分响应。临时权重下载到节点NVMe，每批SHA校验通过后仅移除本轮下载缓存。模型权重不上传。

旧500/1000/1500明细在[原测试目录](../game-stage1-3shift-20261022/)，2000/2500/3000/3500在[2000–3800目录](../game-stage1-3shift-2000plus-20261023/)。本目录summary.json只含新增5个checkpoint。
