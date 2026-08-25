"""
工单生成 Agent — 6 阶段 Prompt 模板（强制 JSON 输出）

生成流程：
  Stage 1: 故障现象提取
  Stage 2: 排查过程梳理
  Stage 3: 根因分析
  Stage 4: 解决方案总结
  Stage 5: 工单摘要生成
  Stage 6: 结构化组装（代码完成）
"""

# ====== Stage 1: 故障现象提取 ======
FAULT_PHENOMENON_PROMPT = """你是一位经验丰富的售后工程师。请根据以下售后处理记录，提取故障现象。

工单标题：{title}
问题描述：{description}
客户环境：{customer_info}

操作日志：
{log_text}

严格按照以下 JSON 格式输出（只输出 JSON，不要其他文字）：
{{"phenomenon": "故障现象1-2句话描述", "impact_scope": "影响范围描述", "occurrence_time": null}}"""

# ====== Stage 2: 排查过程梳理 ======
TROUBLESHOOTING_PROMPT = """你是一位售后故障排查专家。请根据操作时间线和日志，梳理关键排查步骤。

工单标题：{title}
故障现象：{fault_phenomenon}

操作时间线：
{timeline_text}

原始日志：
{log_text}

严格按照以下 JSON 数组格式输出（只输出 JSON 数组）：
[{{"step": 1, "action": "排查操作", "finding": "发现的结果"}}, ...]
只输出 JSON 数组。"""

# ====== Stage 3: 根因分析 ======
ROOT_CAUSE_PROMPT = """你是一位资深技术专家。请根据排查过程，分析故障的根本原因。

故障现象：{fault_phenomenon}
排查过程：{troubleshooting_text}
工程师备注：{engineer_notes}

严格按照以下 JSON 格式输出（只输出 JSON）：
{{"root_cause": "根因一句话概述", "detail": "详细技术分析100-200字", "category": "系统故障/数据库异常/网络异常/配置错误/功能BUG/操作咨询"}}"""

# ====== Stage 4: 解决方案总结 ======
SOLUTION_PROMPT = """你是一位售后解决方案专家。请根据排查过程和根因，总结解决方案。

根因：{root_cause}
排查过程：{troubleshooting_text}

严格按照以下 JSON 格式输出（只输出 JSON）：
{{"solution": "解决方案1-2句话概述", "steps": ["步骤1", "步骤2", "步骤3"], "suggestion": "后续预防建议"}}"""

# ====== Stage 5: 工单摘要生成 ======
SUMMARY_PROMPT = """你是一位售后工单审核员。请为售后处理记录生成工单摘要。

工单标题：{title}
故障现象：{fault_phenomenon}
根因：{root_cause}
解决方案：{solution}
处理时长：约 {duration} 分钟

严格按照以下 JSON 格式输出（只输出 JSON）：
{{"summary": "150字以内工单摘要", "tags": ["标签1", "标签2", "标签3"], "estimated_duration_minutes": 30}}"""

# ====== 多视角并行: 故障专家视角（替代原 Stage 3）======
FAULT_SPECIALIST_PROMPT = """你是一位资深技术故障分析专家。请从故障机制角度，分析根因并评估影响。

工单标题：{title}
故障现象：{fault_phenomenon}
排查过程：{troubleshooting_text}
工程师备注：{engineer_notes}

请从故障专家视角输出，严格按照 JSON 格式（只输出 JSON）：
{{"root_cause": "根因一句话概述", "detail": "从故障机制角度的详细分析100-200字", "category": "系统故障/数据库异常/网络异常/配置错误/功能BUG/操作咨询", "severity_hint": "高/中/低"}}"""

# ====== 多视角并行: 解决方案专家视角（替代原 Stage 4）======
SOLUTION_SPECIALIST_PROMPT = """你是一位售后解决方案专家。请从工程实践角度，总结解决方案和操作步骤。

工单标题：{title}
故障现象：{fault_phenomenon}
排查过程：{troubleshooting_text}

请从方案专家视角输出，严格按照 JSON 格式（只输出 JSON）：
{{"solution": "解决方案1-2句话概述", "steps": ["操作步骤1", "操作步骤2", "操作步骤3"], "suggestion": "后续预防建议", "alternative_approaches": ["备选方案"]}}"""

# ====== 多视角并行: 摘要专家视角（替代原 Stage 5）======
SUMMARY_SPECIALIST_PROMPT = """你是一位售后工单审核员。请从管理视角，为工单生成摘要和标签。

工单标题：{title}
故障现象：{fault_phenomenon}

请从摘要专家视角输出，严格按照 JSON 格式（只输出 JSON）：
{{"summary": "150字以内工单摘要，突出故障原因和解决效果", "tags": ["标签1", "标签2", "标签3"], "estimated_duration_minutes": 30, "quality_score": "good/mediocre/poor"}}"""

# ====== 综合三方结果 ======
SYNTHESIZER_PROMPT = """你是一位资深售后技术主管。请综合三位专家（故障专家、方案专家、摘要专家）的分析结果，输出统一的标准工单内容。

工单标题：{title}

故障专家视角：{fault_view}
方案专家视角：{solution_view}
摘要专家视角：{summary_view}

请检查三方结论的一致性，如有冲突请做出取舍并说明理由。严格按照 JSON 格式输出（只输出 JSON）：
{{"root_cause": {{"root_cause": "...", "detail": "...", "category": "..."}}, "solution": {{"solution": "...", "steps": ["..."], "suggestion": "..."}}, "summary_info": {{"summary": "...", "tags": ["..."], "estimated_duration_minutes": 30}}, "consistency_note": "三方一致性说明，如有冲突解释取舍理由"}}"""

# ====== Stage 6: 结构化组装（代码完成） ======
ASSEMBLY_INSTRUCTION = """
将前 5 个阶段的输出组装为完整的工单 JSON：
{{
    "fault_phenomenon": {{
        "phenomenon": "...",
        "impact_scope": "...",
        "occurrence_time": "..." | null
    }},
    "troubleshooting": [
        {{ "step": 1, "action": "...", "finding": "..." }}
    ],
    "root_cause": {{
        "root_cause": "...",
        "detail": "...",
        "category": "..."
    }},
    "solution": {{
        "solution": "...",
        "steps": ["..."],
        "suggestion": "..."
    }},
    "summary_info": {{
        "summary": "...",
        "tags": ["...", "..."],
        "estimated_duration_minutes": N
    }}
}}
"""
