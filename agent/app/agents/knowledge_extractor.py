"""
知识沉淀 Agent — 从工单中提取知识并向量化存储
"""
import time
from app.graphs.knowledge_graph import knowledge_workflow
from app.memory.vector_store import search_similar, get_knowledge_count


def extract_knowledge(
    ticket_id: int | None = None,
    title: str = "",
    fault_phenomenon: dict | None = None,
    root_cause: dict | None = None,
    solution: dict | None = None,
    summary_info: dict | None = None,
    tags: list[str] | None = None,
    category: str = "",
    customer_info: str = "",
) -> dict:
    """
    从工单中提取知识条目并存入向量库。

    Args:
        ticket_id: 来源工单 ID
        title: 工单标题
        fault_phenomenon: 故障现象 dict
        root_cause: 根因分析 dict
        solution: 解决方案 dict
        summary_info: 摘要 dict
        tags: 标签列表
        category: 问题分类
        customer_info: 客户环境信息

    Returns:
        {"success": bool, "knowledge_id": str, "entry": {...}, "duration_ms": int}
    """
    start = time.time()

    try:
        # 处理嵌套结构：如果是从 Agent 2 生成的 JSON 中直接取字段
        fp_text = _extract_text(fault_phenomenon) or title
        rc_text = _extract_text(root_cause) or "待分析"
        sol_text = _extract_text(solution) or "待总结"
        sm_text = _extract_text(summary_info) or ""

        initial_state = {
            "ticket_id": ticket_id,
            "title": title,
            "fault_phenomenon": fp_text,
            "root_cause": rc_text,
            "solution": sol_text,
            "tags": tags or [],
            "category": category or "系统故障",
            "summary": sm_text,
            "triplet": {},
            "knowledge_entry": {},
            "retry_count": 0,
            "_entry_issues": [],
            "result": {},
            "knowledge_id": "",
            "error": None,
        }

        final_state = knowledge_workflow.invoke(initial_state)
        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "success": final_state.get("error") is None,
            "knowledge_id": final_state.get("knowledge_id", ""),
            "entry": final_state.get("knowledge_entry", {}),
            "triplet": final_state.get("triplet", {}),
            "dedup": final_state.get("result", {}).get("dedup_hit", False),
            "knowledge_count": get_knowledge_count(),
            "duration_ms": elapsed_ms,
            "error": final_state.get("error"),
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "success": False,
            "knowledge_id": "",
            "entry": {},
            "triplet": {},
            "knowledge_count": get_knowledge_count(),
            "duration_ms": elapsed_ms,
            "error": str(e)[:500],
        }


def search_knowledge(query: str, top_k: int = 5) -> dict:
    """
    搜索相似知识条目。

    Args:
        query: 查询文本（故障描述/关键词）
        top_k: 返回数量

    Returns:
        {"items": [...], "total_count": int}
    """
    items = search_similar(query, top_k)
    return {
        "items": items,
        "total_count": get_knowledge_count(),
        "query": query,
    }


def _extract_text(data) -> str:
    """从 dict/list/str 中安全提取文本"""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        # 尝试常见的文本字段
        for key in ("phenomenon", "root_cause", "solution", "summary",
                     "detail", "fault_phenomenon"):
            if data.get(key):
                return str(data[key])
        return str(data)
    if isinstance(data, list):
        return "；".join(str(d) for d in data[:3])
    return str(data) if data else ""
