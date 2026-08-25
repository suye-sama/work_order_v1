"""
售后过程采集 Agent — 调用 LangGraph 工作流，解析终端日志
"""
import time
from app.graphs.parse_graph import parse_workflow
from app.schemas.timeline import LogParseInput, LogParseOutput


def parse_log(log_text: str, ticket_id: int | None = None) -> dict:
    """
    解析终端操作日志，生成结构化时间线。

    Args:
        log_text: 原始的 SSH/堡垒机终端日志文本
        ticket_id: 关联的工单 ID（可选）

    Returns:
        {

            "timeline": [...],
            "phase_count": N,
            "total_steps": N,
            "raw_log_length": N,
            "duration_ms": N,
        }
    """
    start = time.time()

    # 输入校验
    if not log_text or not log_text.strip():
        return {
            "timeline": [],
            "phase_count": 0,
            "total_steps": 0,
            "raw_log_length": 0,
            "error": "日志内容为空",
        }

    # 如果日志非常短（< 50 字符），跳过 LLM，直接做简单提取
    if len(log_text.strip()) < 50:
        result = _simple_parse(log_text)
    else:
        try:
            # 调用 LangGraph 工作流
            initial_state = {
                "raw_log": log_text,
                "cleaned_log": "",
                "commands": [],
                "phases": [],
                "phase_details": [],
                "timeline": [],
                "error": None,
                "phase_count": 0,
                "total_steps": 0,
            }
            final_state = parse_workflow.invoke(initial_state)
            result = final_state
        except Exception as e:
            # LangGraph 工作流失败，降级为简单规则提取
            print(f"[Agent] LangGraph 工作流异常，降级处理: {e}")
            result = _simple_parse(log_text)

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "timeline": result.get("timeline", []),
        "phase_count": result.get("phase_count", 0),
        "total_steps": result.get("total_steps", 0),
        "raw_log_length": len(log_text),
        "error": result.get("error"),
        "duration_ms": elapsed_ms,
    }


def _simple_parse(log_text: str) -> dict:
    """
    简单规则解析（无 LLM 降级方案）
    按行拆分日志，每行作为一个时间线条目
    """
    lines = [l.strip() for l in log_text.strip().split("\n") if l.strip()]
    timeline = []
    for i, line in enumerate(lines, 1):
        # 判断是否为命令（以 $ 或 # 开头）
        is_command = line.startswith(("$", "#", ">"))
        timeline.append({
            "step": i,
            "time": None,
            "phase": "操作记录",
            "operation": "执行命令" if is_command else "输出信息",
            "command": line[:200] if is_command else None,
            "summary": line[:200],
            "result": "",
        })

    return {
        "timeline": timeline,
        "phase_count": 1,
        "total_steps": len(timeline),
        "error": None,
    }
