"""
故障分析 Agent — 深度分析工单，评估风险，提出改进建议
"""
import time
from app.graphs.analyze_graph import analyze_workflow


def analyze_fault(
    ticket_id: int | None = None,
    title: str = "",
    fault_phenomenon: dict | None = None,
    root_cause: dict | None = None,
    solution: dict | None = None,
    category: str = "",
    customer_info: str = "",
) -> dict:
    """
    对工单进行深度故障分析。

    Returns:
        {
            "success": bool,
            "result": { is_known_issue, severity, recurrence_risk, comparison, ... },
            "duration_ms": int
        }
    """
    start = time.time()

    fp = _extract(fault_phenomenon) or title
    rc = _extract(root_cause) or "待分析"
    sol = _extract(solution) or "待总结"

    try:
        initial_state = {
            "ticket_id": ticket_id,
            "title": title,
            "fault_phenomenon": fp,
            "root_cause": rc,
            "solution": sol,
            "category": category or "系统故障",
            "customer_info": customer_info or "",
            "similar_cases": [],
            "comparison": {},
            "risk": {},
            "improvement": {},
            "debate_round": 0,
            "_challenges": [],
            "result": {},
            "error": None,
        }
        final_state = analyze_workflow.invoke(initial_state)
        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "success": True,
            "ticket_id": ticket_id,
            "result": final_state.get("result", {}),
            "duration_ms": elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "success": False,
            "ticket_id": ticket_id,
            "result": {},
            "error": str(e)[:500],
            "duration_ms": elapsed_ms,
        }


def _extract(data) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for k in ("phenomenon", "root_cause", "solution", "summary", "detail"):
            if data.get(k):
                return str(data[k])
        return str(data)
    return str(data) if data else ""