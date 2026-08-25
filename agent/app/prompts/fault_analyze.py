"""
故障分析 Agent — Prompt 模板
"""

# ====== 对比分析 ======
COMPARISON_PROMPT = """你是一位资深售后技术专家。请对比分析当前故障与历史相似案例。

当前故障：
  标题：{title}
  现象：{fault_phenomenon}
  根因：{root_cause}
  分类：{category}

历史相似案例：
{similar_cases_text}

请分析：
1. 当前故障与历史案例的异同点
2. 是否为已知问题模式
3. 解决方案是否可以复用

严格按照 JSON 格式输出（只输出 JSON）：
{{"is_known_issue": true/false, "comparison": "对比分析150-200字", "can_reuse_solution": true/false, "primary_reference": "最相似的案例标题"}}"""

# ====== 风险评估 ======
RISK_ASSESSMENT_PROMPT = """你是一位系统可靠性工程师。请评估当前故障的风险。

故障信息：
  标题：{title}
  现象：{fault_phenomenon}
  根因：{root_cause}
  解决方案：{solution}
  对比分析：{comparison}

请评估：
1. severity: 严重程度（高/中/低）
2. recurrence_risk: 复发风险（高/中/低）
3. affected_versions: 可能受影响的版本范围
4. risk_detail: 风险分析（100-150字）

严格按照 JSON 格式输出（只输出 JSON）：
{{"severity": "高/中/低", "recurrence_risk": "高/中/低", "affected_versions": ["V3.2.0","V3.2.1"], "risk_detail": "风险分析100-150字"}}"""

# ====== 辩论: 质疑风险评估 ======
CHALLENGER_PROMPT = """你是一位资深系统可靠性审计员。请质疑以下风险评估结论，找出其中可能存在的疑点和疏漏。

故障标题：{title}
根因：{root_cause}
当前评估结论：
  严重程度：{severity}
  复发风险：{recurrence_risk}
  风险详情：{risk_detail}

辩论轮次：第 {round} 轮

请从以下角度质疑：
1. 严重程度是否被低估或高估？
2. 复发风险评估是否充分考虑了根因特性？
3. 是否有未考虑的连锁影响或边界场景？

如果评估已经相当合理，可以回复无质疑。严格按照 JSON 格式输出：
{{"has_challenges": true/false, "challenges": ["质疑点1", "质疑点2"], "suggested_revision": "建议修正方向"}}"""

# ====== 辩论: 回应质疑并修正评估 ======
DEFENDER_PROMPT = """你是一位系统风险评估师。请回应以下质疑并修正评估结论。

当前风险评估：
{risk}

质疑意见：
{challenges}

请逐条回应质疑：
1. 如果质疑合理，修正评估结论
2. 如果质疑不成立，解释理由
3. 综合所有意见后输出最终评估

严格按照 JSON 格式输出（只输出 JSON）：
{{"severity": "高/中/低", "recurrence_risk": "高/中/低", "risk_detail": "修正后的风险分析100-150字", "response_to_challenges": "对质疑的逐条回应", "need_further_debate": true/false}}"""

# ====== 改进建议 ======
IMPROVEMENT_PROMPT = """你是一位运维架构师。请根据故障分析结果，提出改进建议。

故障：{title}
根因：{root_cause}
风险：{risk_detail}
复发风险：{recurrence_risk}

请提出：
1. prevention: 短期预防措施（具体可操作）
2. long_term_advice: 长期优化建议（架构/流程层面）

严格按照 JSON 格式输出（只输出 JSON）：
{{"prevention": "短期预防措施100-150字", "long_term_advice": "长期优化建议100-150字"}}"""