"""
日志解析 LangGraph 工作流

流程：清洗 → 命令识别 → 阶段分割 → 摘要生成 → 标准化输出

使用 LangGraph StateGraph 管理状态流转，每个节点独立调用 LLM。
"""
import json
import re
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from app.llm.factory import get_llm
from app.prompts.log_parse import (
    COMMAND_EXTRACTION_PROMPT,
    PHASE_SEGMENTATION_PROMPT,
    PHASE_SUMMARY_PROMPT,
)


# ====== State 定义 ======

class ParseState(TypedDict):
    """日志解析工作流状态"""

    # 输入
    raw_log: str
    # 中间结果
    cleaned_log: str
    commands: list[dict]       # [{step, time, command, output_summary, purpose}]
    phases: list[dict]         # [{phase, step_start, step_end, summary}]
    phase_details: list[dict]  # [{phase, summary, key_findings, result, commands}]
    # 最终输出
    timeline: list[dict]
    # 状态
    error: Optional[str]
    phase_count: int
    total_steps: int


# ====== 节点函数 ======


def clean_log(state: ParseState) -> ParseState:
    """
    Node 1: 日志清洗
    - 去除 ANSI 转义序列
    - 统一编码
    - 移除明显的噪声行
    """
    log = state["raw_log"]

    # 去除 ANSI 转义序列 (\x1b[...m, \033[...m)
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    log = re.sub(r"\033\[[0-9;]*m", "", log)

    # 去除回车符
    log = log.replace("\r\n", "\n").replace("\r", "\n")

    # 去除连续空行
    log = re.sub(r"\n{3,}", "\n\n", log)

    # 尝试识别并规范化常见提示符行
    # 例如: [root@host ~]#  → 保留

    state["cleaned_log"] = log.strip()
    state["error"] = None
    return state


def extract_commands(state: ParseState) -> ParseState:
    """
    Node 2: 命令识别（LLM 调用）
    从清洗后的日志中提取所有关键命令和操作
    """
    log = state["cleaned_log"]

    # 短日志（< 500 字符或 < 8 行）直接规则提取，避免 LLM 调用开销
    line_count = len([l for l in log.split("\n") if l.strip()])
    if len(log) < 500 or line_count < 8:
        commands = _simple_command_extract(log)
        state["commands"] = commands
        state["total_steps"] = len(commands)
        state["_fast_path"] = True  # 标记快速通道
        return state

    try:
        llm = get_llm(temperature=0.2)
        prompt = COMMAND_EXTRACTION_PROMPT.format(log_text=log[:4000])  # 限制长度
        response = llm.invoke(prompt)
        commands = _parse_commands_from_llm(response.content)
    except Exception as e:
        # LLM 调用失败时降级为简单规则提取
        print(f"[Agent] LLM 命令识别失败，降级为规则提取: {e}")
        commands = _simple_command_extract(log)

    state["commands"] = commands
    state["total_steps"] = len(commands)
    return state


def segment_phases(state: ParseState) -> ParseState:
    """
    Node 3: 阶段分割（LLM 调用）
    将命令列表按操作意图划分为若干阶段
    """
    commands = state["commands"]

    if len(commands) <= 2:
        # 操作太少，直接归为一个阶段
        state["phases"] = [{
            "phase": "故障处理",
            "step_start": 1,
            "step_end": len(commands),
            "summary": "执行了 {} 个操作".format(len(commands)),
        }]
        return state

    # 构建操作描述文本
    ops_text = "\n".join(
        f"Step {c.get('step', i+1)}: [{c.get('command', 'N/A')}] {c.get('purpose', '')}"
        for i, c in enumerate(commands)
    )

    try:
        llm = get_llm(temperature=0.2)
        prompt = PHASE_SEGMENTATION_PROMPT.format(operations_text=ops_text[:3000])
        response = llm.invoke(prompt)
        phases = _parse_phases_from_llm(response.content, len(commands))
    except Exception as e:
        print(f"[Agent] LLM 阶段分割失败，降级: {e}")
        phases = [{
            "phase": "故障处理",
            "step_start": 1,
            "step_end": len(commands),
            "summary": "售后故障排查全过程",
        }]

    state["phases"] = phases
    state["phase_count"] = len(phases)
    return state


def summarize_phases(state: ParseState) -> ParseState:
    """
    Node 4: 阶段摘要生成（LLM 调用）
    为每个阶段生成详细摘要和关键发现
    """
    commands = state["commands"]
    phases = state["phases"]
    phase_details = []

    for phase in phases:
        start = phase.get("step_start", 1) - 1
        end = phase.get("step_end", len(commands))
        phase_cmds = commands[start:end]

        cmd_text = "\n".join(
            f"- {c.get('command', '')}: {c.get('output_summary', '')}"
            for c in phase_cmds
        )

        if len(cmd_text) < 300:
            # 内容少，不需要 LLM
            phase_details.append({
                "phase": phase["phase"],
                "summary": phase.get("summary", ""),
                "key_findings": "",
                "result": "完成",
                "commands": phase_cmds,
            })
            continue

        try:
            llm = get_llm(temperature=0.3)
            prompt = PHASE_SUMMARY_PROMPT.format(
                phase_name=phase["phase"],
                phase_operations=cmd_text[:2000],
            )
            response = llm.invoke(prompt)
            detail = _parse_summary_from_llm(response.content)
            detail["phase"] = phase["phase"]
            detail["commands"] = phase_cmds
            phase_details.append(detail)
        except Exception as e:
            print(f"[Agent] LLM 摘要生成失败: {e}")
            phase_details.append({
                "phase": phase["phase"],
                "summary": phase.get("summary", ""),
                "key_findings": "",
                "result": "完成",
                "commands": phase_cmds,
            })

    state["phase_details"] = phase_details
    return state


def build_timeline(state: ParseState) -> ParseState:
    """
    Node 5: 标准化输出
    将各阶段结果组装为完整时间线（纯代码，不调 LLM）
    """
    phase_details = state["phase_details"]
    timeline = []
    step_counter = 1

    for pd in phase_details:
        phase_name = pd["phase"]
        for cmd in pd.get("commands", []):
            timeline.append({
                "step": step_counter,
                "time": cmd.get("time"),
                "phase": phase_name,
                "operation": cmd.get("purpose", cmd.get("command", "")),
                "command": cmd.get("command"),
                "summary": cmd.get("output_summary", "") or pd.get("summary", ""),
                "result": cmd.get("output_summary") or pd.get("result", ""),
            })
            step_counter += 1

    state["timeline"] = timeline
    state["total_steps"] = len(timeline)
    return state


# ====== 辅助函数 ======


def _simple_command_extract(log: str) -> list[dict]:
    """简单规则提取命令（LLM 不可用时的降级方案）"""
    commands = []
    lines = log.strip().split("\n")
    step = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 识别常见的命令提示符行
        if re.match(r"^(\$|\#|>|\(venv\)|\[.*\][\$\#])\s", line):
            step += 1
            commands.append({
                "step": step,
                "time": None,
                "command": line,
                "output_summary": "",
                "purpose": "执行命令",
            })
        else:
            step += 1
            commands.append({
                "step": step,
                "time": None,
                "command": line[:80],
                "output_summary": line[:200] if len(line) > 80 else "",
                "purpose": "操作记录",
            })
    return commands


def _parse_commands_from_llm(text: str) -> list[dict]:
    """从 LLM 返回的文本中解析命令列表"""
    # 1. 尝试提取 ```json ... ``` 代码块
    md_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. 尝试直接匹配 JSON 数组
    json_match = re.search(r"\[.*\]", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # 3. 全部失败则降级
    return _simple_command_extract(text[:500])


def _parse_phases_from_llm(text: str, total_steps: int) -> list[dict]:
    """从 LLM 返回文本中解析阶段划分"""
    # 1. 尝试提取 markdown 代码块
    md_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1))
        except json.JSONDecodeError:
            pass
    # 2. 尝试直接匹配
    json_match = re.search(r"\[.*\]", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    return [{"phase": "故障处理", "step_start": 1, "step_end": total_steps, "summary": ""}]


def _parse_summary_from_llm(text: str) -> dict:
    """从 LLM 返回文本中解析阶段摘要"""
    # 1. 尝试提取 markdown 代码块
    md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1))
        except json.JSONDecodeError:
            pass
    # 2. 尝试直接匹配
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    return {"summary": text[:200], "key_findings": "", "result": ""}


# ====== 构建 LangGraph 工作流 ======


def create_parse_graph() -> StateGraph:
    """创建日志解析 LangGraph 工作流"""
    workflow = StateGraph(ParseState)

    # 添加节点
    workflow.add_node("clean", clean_log)
    workflow.add_node("extract_commands", extract_commands)
    workflow.add_node("segment_phases", segment_phases)
    workflow.add_node("summarize_phases", summarize_phases)
    workflow.add_node("build_timeline", build_timeline)

    workflow.set_entry_point("clean")

    # 条件分支1: 短日志 → 跳过LLM命令识别, 直接用规则提取后进入阶段分割
    def should_use_llm(state: ParseState) -> str:
        log = state["cleaned_log"]
        line_count = len([l for l in log.split("\n") if l.strip()])
        if len(log) < 500 or line_count < 8:
            commands = _simple_command_extract(log)
            state["commands"] = commands
            state["total_steps"] = len(commands)
            return "skip_llm"
        return "use_llm"

    workflow.add_conditional_edges(
        "clean",
        should_use_llm,
        {"use_llm": "extract_commands", "skip_llm": "segment_phases"},
    )

    # 条件分支2: 命令≤2个 → 跳过阶段分割, 直接做摘要
    def should_segment(state: ParseState) -> str:
        if len(state["commands"]) <= 2:
            state["phases"] = [{
                "phase": "故障处理",
                "step_start": 1,
                "step_end": len(state["commands"]),
                "summary": "执行了 {} 个操作".format(len(state["commands"])),
            }]
            state["phase_count"] = 1
            return "skip_segment"
        return "do_segment"

    workflow.add_conditional_edges(
        "extract_commands",
        should_segment,
        {"do_segment": "segment_phases", "skip_segment": "summarize_phases"},
    )

    workflow.add_edge("segment_phases", "summarize_phases")
    workflow.add_edge("summarize_phases", "build_timeline")
    workflow.add_edge("build_timeline", END)

    return workflow.compile()


# 导出编译好的 Graph（单例）
parse_workflow = create_parse_graph()
