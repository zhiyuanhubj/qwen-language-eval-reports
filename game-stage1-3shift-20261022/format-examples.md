# “格式失败”具体是什么意思

这次原协议确实测了四种设置：Thinking / NoTags，各自 T=0.6、top_p=0.95 和 T=1、top_p=1。上次对话表格只展示低温组，不代表另一组未测。

Thinking 请求使用开放的 `<think>` 生成前缀，解析器以 `</think>` 分隔思考和最终答案。没有这个结束标记时，且API没有独立reasoning字段，旧解析器把全部返回文本放入 reasoning，final_answer 留空。它可能包含完整的解题过程甚至正确答案，**不是“没有thinking”，也不能直接算成“不懂中文/英文”**。

## 实际例子：1500 / Thinking / T0.6 / top_p0.95

题目 text-04-zh：一台机器6分钟生产9个零件，三台机器工作14分钟，说明假设并计算产量。

模型原文先推导单台速率、工作时间和机器数量，最后明确写出：

> 三台相同机器连续工作十四分钟，理论上共生产 **63** 个零件。

该次 finish_reason=stop，正常停止；原文无 `</think>`，因此 final_answer 为空。评分员已读原文，准确性、语言、逻辑均给100；指令、完整性各50，来源标为 raw_unclosed。这是输出分隔协议失败，实质答案仍然正确。完整原回答和评分见 [format-examples.json](format-examples.json)。

同一模型、同一setting共246条成功返回，其中193条没有解析出独立final；193条都有非空思考/正文文字，176条为正常stop，17条为length。没有闭合标签不等于一定输出超长或一定没有实质答案。

## 如何避免误读分数

- NoTags 本来就不要求thinking标签，没有thinking不会因此被扣分。
- 原rubric让评分员检查未闭合文本中的实质答案；只有规划、没有可评价答案时才标none。它同时规定 raw_unclosed 的指令/完整性各不高于50。
- 本轮另外发现56条 raw_unclosed 评分未一致执行这个上限。原始评分保留，没有覆盖；审计见 [status/format-scoring-consistency-audit.json](status/format-scoring-consistency-audit.json)。因此应同时看准确性、语言、逻辑、原文与格式指标，不能只凭综合分宣称知识遗忘。
- 主报告维持原协议，便于和旧报告比较；内容能力与格式合规应分别解读。若另做“忽略think标签、只评可见实质答案”的新口径，必须另表展示，不能覆盖旧分数。
