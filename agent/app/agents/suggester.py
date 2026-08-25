"""
排查方向建议 Agent — 检索相似案例 + LLM 推理，生成排查建议
"""
import json
import re
import time

from app.llm.factory import get_llm
from app.prompts.suggest import SUGGEST_PROMPT
from app.memory.vector_store import search_similar


def _safe_json(text: str, fallback: dict) -> dict:
    """安全解析 JSON"""
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if md:
        try:
            return json.loads(md.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return fallback


def suggest_checks(
    title: str = "",
    description: str = "",
    category: str = "",
    customer_info: str = "",
) -> dict:
    """
    根据工单描述，生成排查方向建议。

    Args:
        title: 工单标题
        description: 问题描述（可以模糊）
        category: 问题分类（可选）
        customer_info: 客户环境信息（可选）

    Returns:
        {
            "success": bool,
            "possible_causes": [...],
            "suggested_checks": [...],
            "similar_cases": [...],
            "brief_analysis": str,
            "duration_ms": int,
        }
    """
    start = time.time()

    # Step 1: 语义检索相似知识
    query = f"{title} {description}"[:300]
    try:
        similar_cases = search_similar(query, top_k=5)
    except Exception:
        similar_cases = []

    # Step 2: 构建相似案例文本
    if similar_cases:
        cases_lines = []
        for i, c in enumerate(similar_cases, 1):
            sim_pct = f"{c.get('similarity', 0) * 100:.0f}%"
            cases_lines.append(
                f"案例{i}（相似度{sim_pct}）：\n"
                f"  标题：{c.get('title', '')}\n"
                f"  摘要：{c.get('summary', c.get('problem_description', ''))[:200]}"
            )
        cases_text = "\n\n".join(cases_lines)
    else:
        cases_text = "（知识库中暂无相似案例，请基于通用运维经验给出建议）"

    # Step 3: LLM 推理
    fallback = {
        "possible_causes": [
            "服务进程异常（未启动/已崩溃/端口被占用）",
            "依赖组件故障（数据库/缓存/消息队列不可用）",
            "配置变更导致（近期有修改但未充分测试）",
        ],
        "suggested_checks": [
            {
                "direction": "检查核心服务状态",
                "why": "大部分故障源于核心服务异常",
                "command": "systemctl status <service> 或 ps aux | grep <process>",
                "expected_if_problem": "服务状态为 inactive/failed，或进程不存在",
            },
            {
                "direction": "检查系统资源",
                "why": "CPU/内存/磁盘/网络瓶颈导致服务不可用",
                "command": "top -bn1 | head -20 && df -h && free -m",
                "expected_if_problem": "CPU > 90% 或磁盘使用率 > 95% 或内存耗尽",
            },
            {
                "direction": "检查应用日志",
                "why": "错误日志直接反映故障原因",
                "command": "tail -100 /var/log/<app>/error.log",
                "expected_if_problem": "日志中出现 ERROR/FATAL/Exception 等关键字",
            },
        ],
        "brief_analysis": "由于缺少详细操作日志和相似案例，建议从服务状态检查入手，逐步排查系统资源和应用日志。建议工程师先执行 'systemctl status' 和 'top' 快速判断是否为服务宕机或资源耗尽，再根据初步结果深入排查。",
    }

    try:
        llm = get_llm(temperature=0.3)
        prompt = SUGGEST_PROMPT.format(
            title=title or "未知",
            description=description or "无详细描述",
            category=category or "待分类",
            customer_info=customer_info or "未知",
            similar_cases_text=cases_text,
        )
        resp = llm.invoke(prompt)
        result = _safe_json(resp.content, fallback)
    except Exception as e:
        print(f"[Suggest] LLM 推理失败，使用降级建议: {e}")
        result = fallback

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "success": True,
        "possible_causes": result.get("possible_causes", fallback["possible_causes"]),
        "suggested_checks": result.get("suggested_checks", fallback["suggested_checks"]),
        "similar_cases": [
            {
                "title": c.get("title", ""),
                "summary": c.get("summary", c.get("problem_description", ""))[:150],
                "similarity": c.get("similarity", 0),
                "id": c.get("id", ""),
            }
            for c in similar_cases[:5]
        ],
        "brief_analysis": result.get("brief_analysis", fallback["brief_analysis"]),
        "duration_ms": elapsed_ms,
    }
