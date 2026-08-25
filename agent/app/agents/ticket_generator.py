"""
工单生成 Agent — 调用 LangGraph 工作流，汇总售后数据生成标准工单
"""
import time
from app.graphs.generate_graph import generate_workflow


def generate_ticket(
    title: str,
    description: str = "",
    customer_info: str = "",
    timeline_json: list | None = None,
    raw_log: str = "",
    engineer_notes: str = "",
    ticket_id: int | None = None,
) -> dict:
    """
    汇总所有售后数据，生成标准化工单。

    Args:
        title: 工单标题
        description: 原始问题描述
        customer_info: 客户环境信息
        timeline_json: 时间线数据（来自日志解析 Agent 的输出）
        raw_log: 原始操作日志
        engineer_notes: 工程师备注
        ticket_id: 关联的工单 ID

    Returns:
        {
            "success": bool,
            "ticket_id": int | None,
            "result": { fault_phenomenon, troubleshooting, root_cause, solution, summary_info },
            "error": str | None,
            "duration_ms": int,
        }
    """
    start = time.time()

    # 数据完整性检查
    has_data = bool(raw_log or timeline_json or description)
    if not has_data:
        return {
            "success": False,
            "ticket_id": ticket_id,
            "result": None,
            "error": "缺少必要数据：至少需要原始日志、时间线或问题描述之一",
            "duration_ms": int((time.time() - start) * 1000),
        }

    try:
        initial_state = {
            "title": title,
            "description": description or "",
            "customer_info": customer_info or "",
            "timeline_json": timeline_json or [],
            "raw_log": raw_log or "",
            "engineer_notes": engineer_notes or "",
            "fault_phenomenon": {},
            "troubleshooting": [],
            "root_cause": {},
            "solution": {},
            "summary_info": {},
            "retry_count": 0,
            "_quality_issues": [],
            "result": {},
            "error": None,
        }

        final_state = generate_workflow.invoke(initial_state)

        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "success": True,
            "ticket_id": ticket_id,
            "result": final_state.get("result", {}),
            "error": final_state.get("error"),
            "duration_ms": elapsed_ms,
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        print(f"[Agent] 工单生成异常: {e}")

        # 降级：返回基础结构
        return {
            "success": False,
            "ticket_id": ticket_id,
            "result": {
                "fault_phenomenon": {
                    "phenomenon": title,
                    "impact_scope": "待确认",
                    "occurrence_time": None,
                },
                "troubleshooting": [],
                "root_cause": {
                    "root_cause": "待分析",
                    "detail": f"Agent 处理异常: {str(e)[:200]}",
                    "category": "待分类",
                },
                "solution": {"solution": "待总结", "steps": [], "suggestion": ""},
                "summary_info": {
                    "summary": f"工单：{title}。Agent 自动生成失败，请手动填写。",
                    "tags": [],
                    "estimated_duration_minutes": None,
                },
            },
            "error": str(e)[:500],
            "duration_ms": elapsed_ms,
        }
