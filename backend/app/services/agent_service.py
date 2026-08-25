"""
Agent 调用服务 — 封装 FastAPI → Flask Agent 的 HTTP 调用
"""
import httpx
from app.config import AGENT_URL


# Agent 服务地址
AGENT_BASE = AGENT_URL.rstrip("/")

# 超时配置（Agent 调用 LLM 可能较慢）
AGENT_TIMEOUT = 120  # 120 秒


async def _call_agent(endpoint: str, data: dict, timeout: int = AGENT_TIMEOUT) -> dict:
    """通用 Agent 调用"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{AGENT_BASE}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        return {"error": f"Agent 调用超时（{timeout}秒）", "success": False}
    except httpx.HTTPStatusError as e:
        return {"error": f"Agent 返回错误: {e.response.status_code}", "success": False}
    except Exception as e:
        return {"error": f"Agent 连接失败: {str(e)[:200]}", "success": False}


async def parse_log(log_text: str, ticket_id: int | None = None) -> dict:
    """
    Agent 1: 日志解析
    输入：SSH/堡垒机终端日志
    输出：结构化时间线
    """
    return await _call_agent("/agent/log/parse", {
        "log_text": log_text,
        "ticket_id": ticket_id,
    })


async def generate_ticket(
    ticket_id: int | None = None,
    title: str = "",
    description: str = "",
    customer_info: str = "",
    timeline_json: list | None = None,
    raw_log: str = "",
    engineer_notes: str = "",
) -> dict:
    """
    Agent 2: 工单生成
    输入：售后数据（时间线+日志+备注）
    输出：标准工单 JSON（故障现象/排查过程/根因/解决方案/摘要）
    """
    return await _call_agent("/agent/ticket/generate", {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "customer_info": customer_info,
        "timeline_json": timeline_json or [],
        "raw_log": raw_log,
        "engineer_notes": engineer_notes,
    })


async def extract_knowledge(
    ticket_id: int | None = None,
    title: str = "",
    fault_phenomenon: dict | None = None,
    root_cause: dict | None = None,
    solution: dict | None = None,
    summary_info: dict | None = None,
    tags: list[str] | None = None,
    category: str = "",
) -> dict:
    """
    Agent 3: 知识提取
    输入：工单完整数据
    输出：知识条目 + 向量存储
    """
    return await _call_agent("/agent/knowledge/extract", {
        "ticket_id": ticket_id,
        "title": title,
        "fault_phenomenon": fault_phenomenon or {},
        "root_cause": root_cause or {},
        "solution": solution or {},
        "summary_info": summary_info or {},
        "tags": tags or [],
        "category": category,
    })


async def search_similar(query: str, top_k: int = 5) -> dict:
    """
    Agent 4: 相似工单检索
    输入：故障描述
    输出：Top-K 相似工单
    """
    return await _call_agent("/agent/search", {
        "query": query,
        "top_k": top_k,
    })


async def list_knowledge(
    keyword: str = "",
    category: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    知识库列表 — 分页获取知识条目，支持搜索
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{AGENT_BASE}/agent/knowledge/list",
                params={
                    "keyword": keyword,
                    "category": category,
                    "page": page,
                    "page_size": page_size,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": f"Agent 连接失败: {str(e)[:200]}", "items": [], "total": 0}


async def get_knowledge_detail(knowledge_id: str) -> dict:
    """
    知识条目详情
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{AGENT_BASE}/agent/knowledge/{knowledge_id}",
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": f"Agent 连接失败: {str(e)[:200]}"}


async def analyze_fault(
    ticket_id: int | None = None,
    title: str = "",
    fault_phenomenon: dict | None = None,
    root_cause: dict | None = None,
    solution: dict | None = None,
    category: str = "",
    customer_info: str = "",
) -> dict:
    """
    Agent 5: 故障分析
    输入：工单完整数据
    输出：深度分析报告（风险评估+改进建议）
    """
    return await _call_agent("/agent/fault/analyze", {
        "ticket_id": ticket_id,
        "title": title,
        "fault_phenomenon": fault_phenomenon or {},
        "root_cause": root_cause or {},
        "solution": solution or {},
        "category": category,
        "customer_info": customer_info,
    })


async def suggest_checks(
    title: str = "",
    description: str = "",
    category: str = "",
    customer_info: str = "",
) -> dict:
    """
    Agent 6: 排查方向建议
    输入：工单标题和模糊描述
    输出：可能原因、排查方向、建议命令、相似案例
    """
    return await _call_agent("/agent/ticket/suggest", {
        "title": title,
        "description": description,
        "category": category,
        "customer_info": customer_info,
    }, timeout=60)
