"""
日志解析 Agent — 多阶段 Prompt 模板

解析流程：
  1. 日志清洗（代码处理，不需要 LLM）
  2. 命令识别 → 提取所有执行的命令和关键输出
  3. 阶段分割 → 按操作意图切分日志
  4. 摘要生成 → 为每个阶段生成一句话摘要
  5. 标准化输出 → 组装为 Timeline JSON
"""

# ====== Stage 1: 命令识别 ======
COMMAND_EXTRACTION_PROMPT = """你是一位资深的运维工程师。请分析以下终端操作日志，提取其中所有的关键操作。

日志内容：
{log_text}

请严格按照以下 JSON 数组格式输出，不要输出任何其他文字：
[
  {{
    "step": 1,
    "time": "2026-01-10 14:30:00",
    "command": "systemctl status nginx",
    "output_summary": "nginx.service: inactive (dead)",
    "purpose": "检查 Nginx 服务状态"
  }},
  ...
]

注意：
- step 从 1 开始递增
- time 如果日志中没有明确时间戳，填 null
- command 填写用户执行的命令
- output_summary 填写命令输出的关键信息（报错、异常、状态变更），不超过50字
- purpose 用中文简要说明该命令的目的

只输出 JSON 数组，不要输出任何解释、说明或思考过程。"""

# ====== Stage 2: 阶段分割 ======
PHASE_SEGMENTATION_PROMPT = """你是一位售后故障排查专家。以下是工程师在处理故障时的操作记录。

请将这些操作按"排查意图"划分为若干阶段。常见阶段：环境检查、日志分析、故障定位、修复操作、验证测试。

操作记录：
{operations_text}

严格按照以下 JSON 数组格式输出：
[
  {{"phase": "环境检查", "step_start": 1, "step_end": 3, "summary": "登录服务器并检查服务状态"}},
  ...
]
只输出 JSON 数组。"""

# ====== Stage 3: 阶段摘要生成 ======
PHASE_SUMMARY_PROMPT = """你是一位售后工单撰写专家。请为以下售后处理阶段生成简洁的摘要。

阶段：{phase_name}
操作内容：
{phase_operations}

严格按照以下 JSON 格式输出：
{{"summary": "该阶段做了什么（一句话，50字内）", "key_findings": "关键发现（异常或错误重点说明）", "result": "成功/失败/发现异常"}}
只输出 JSON。"""

# ====== Stage 4: 标准化时间线组装（由代码完成，这里定义 JSON 模板）=====
TIMELINE_TEMPLATE = """
请将以下所有信息组装为统一的时间线 JSON 数组。

每个时间线条目格式：
{{
  "step": <序号>,
  "time": "<ISO时间字符串，如果未知则填null>",
  "phase": "<阶段名称>",
  "operation": "<操作描述>",
  "command": "<执行的命令>",
  "summary": "<一句话摘要>",
  "result": "<操作结果>"
}}

操作信息：
{operations_detail}

阶段信息：
{phases_detail}

请输出完整的 JSON 数组。
"""
