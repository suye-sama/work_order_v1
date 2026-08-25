"""
知识提取 LangGraph 工作流

流程：三元组提取 → 知识条目生成 → Embedding → Chroma 存储 → 去重检查
"""
import json
import re
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from app.llm.factory import get_llm
from app.prompts.knowledge import TRIPLET_EXTRACTION_PROMPT, KNOWLEDGE_ENTRY_PROMPT
from app.memory.vector_store import add_knowledge, search_similar


class KnowledgeState(TypedDict):
    """知识提取工作流状态"""

    # 输入
    ticket_id: Optional[int]
    title: str
    fault_phenomenon: str
    root_cause: str
    solution: str
    tags: list[str]
    category: str
    summary: str

    # 中间结果
    triplet: dict
    knowledge_entry: dict

    # 质量校验
    retry_count: int
    _entry_issues: list[str]

    # 最终输出
    result: dict
    knowledge_id: str
    error: Optional[str]


def _safe_json_parse(text: str, fallback: dict) -> dict:
    """安全解析 JSON，支持 markdown 代码块"""
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


def extract_triplet(state: KnowledgeState) -> KnowledgeState:
    """Node 1: 三元组提取（LLM）"""
    fp = state.get("fault_phenomenon", "") or ""
    rc = state.get("root_cause", "") or ""
    sol = state.get("solution", "") or ""

    if not fp and not rc:
        state["triplet"] = {
            "phenomenon": state["title"],
            "root_cause": "待分析",
            "solution": "待总结",
        }
        return state

    try:
        llm = get_llm(temperature=0.2)
        prompt = TRIPLET_EXTRACTION_PROMPT.format(
            title=state["title"],
            fault_phenomenon=fp[:500],
            root_cause=rc[:500],
            solution=sol[:500],
        )
        resp = llm.invoke(prompt)
        triplet = _safe_json_parse(resp.content, {
            "phenomenon": fp[:100] if isinstance(fp, str) else state["title"],
            "root_cause": rc[:100] if isinstance(rc, str) else "待分析",
            "solution": sol[:100] if isinstance(sol, str) else "待总结",
        })
    except Exception as e:
        print(f"[Knowledge] 三元组提取失败: {e}")
        triplet = {"phenomenon": state["title"], "root_cause": "提取失败", "solution": "提取失败"}

    state["triplet"] = triplet
    return state


def generate_entry(state: KnowledgeState) -> KnowledgeState:
    """Node 2: 知识条目生成（LLM）—— 输出四段式结构化知识"""
    triplet = state["triplet"]
    tags = state.get("tags", [])
    category = state.get("category", "系统故障")

    try:
        llm = get_llm(temperature=0.3)

        # 如果上次校验有缺失字段, 把反馈拼入 prompt
        feedback = state.get("_entry_issues", [])
        extra_ctx = ""
        if feedback:
            extra_ctx = "\n\n【上次生成缺失以下必要内容，请补充完整】\n" + "\n".join(f"- {f}" for f in feedback)

        prompt = KNOWLEDGE_ENTRY_PROMPT.format(
            phenomenon=triplet.get("phenomenon", ""),
            root_cause=triplet.get("root_cause", ""),
            solution=triplet.get("solution", ""),
            tags=", ".join(tags) if tags else "待分类",
            category=category,
        ) + extra_ctx
        resp = llm.invoke(prompt)
        entry = _safe_json_parse(resp.content, {
            "title": state["title"][:50],
            "category": category,
            "tags": tags,
            "difficulty": "中等",
            "problem_description": state.get("summary", triplet.get("phenomenon", ""))[:200],
            "root_cause": triplet.get("root_cause", "待分析"),
            "symptoms": triplet.get("phenomenon", ""),
            "solution": triplet.get("solution", "待总结"),
            "steps": [],
            "prevention": "建议完善监控和自动化巡检",
        })
    except Exception as e:
        print(f"[Knowledge] 知识条目生成失败: {e}")
        entry = {
            "title": state["title"][:50],
            "category": category,
            "tags": tags,
            "difficulty": "中等",
            "problem_description": state.get("summary", triplet.get("phenomenon", ""))[:200],
            "root_cause": triplet.get("root_cause", "待分析"),
            "symptoms": triplet.get("phenomenon", ""),
            "solution": triplet.get("solution", "待总结"),
            "steps": [],
            "prevention": "",
        }

    state["knowledge_entry"] = entry
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["_entry_issues"] = []
    return state


def entry_quality_check(state: KnowledgeState) -> KnowledgeState:
    """校验知识条目四段式内容完整性"""
    entry = state["knowledge_entry"]
    issues = []

    required = {
        "problem_description": "问题描述",
        "root_cause": "根因分析",
        "symptoms": "故障现象",
        "solution": "解决方案参考",
    }
    for field, label in required.items():
        if not entry.get(field):
            issues.append(f"缺少{label}")

    if len(entry.get("problem_description", "")) < 10:
        issues.append("问题描述过短 (<10字符)")

    state["_entry_issues"] = issues
    return state


def should_retry_entry(state: KnowledgeState) -> str:
    """判断是否需要重试生成知识条目"""
    if not state.get("_entry_issues"):
        return "pass"
    if state.get("retry_count", 0) < 2:
        return "retry"
    return "pass"  # 超次数强制通过


def dedup_check(state: KnowledgeState) -> KnowledgeState:
    """Node 3: 去重检查（检索相似知识）"""
    entry = state["knowledge_entry"]
    problem_desc = entry.get("problem_description", "")

    if len(problem_desc) < 20:
        state["result"] = {"dedup_hit": False, "similar_items": []}
        return state

    try:
        similar = search_similar(problem_desc[:300], top_k=3)
        high_sim = [s for s in similar if s["similarity"] > 0.95]
        state["result"] = {
            "dedup_hit": len(high_sim) > 0,
            "similar_items": similar[:3],
        }
    except Exception:
        state["result"] = {"dedup_hit": False, "similar_items": []}

    return state


def store_embedding(state: KnowledgeState) -> KnowledgeState:
    """Node 4: 向量化存储（四段式知识结构）"""
    entry = state["knowledge_entry"]
    ticket_id = state.get("ticket_id")

    knowledge_id = f"kb-{ticket_id}" if ticket_id else f"kb-{hash(state['title']) % 100000}"

    success = add_knowledge(
        knowledge_id=knowledge_id,
        title=entry.get("title", state["title"]),
        problem_description=entry.get("problem_description", ""),
        root_cause=entry.get("root_cause", ""),
        symptoms=entry.get("symptoms", ""),
        solution=entry.get("solution", ""),
        steps=entry.get("steps", []),
        prevention=entry.get("prevention", ""),
        tags=entry.get("tags", []),
        category=entry.get("category", state.get("category", "")),
        difficulty=entry.get("difficulty", ""),
        metadata={
            "ticket_id": ticket_id,
        },
    )

    state["knowledge_id"] = knowledge_id
    state["error"] = None if success else "向量存储失败"
    return state


def build_output(state: KnowledgeState) -> KnowledgeState:
    """Node 5: 组装输出"""
    state["result"] = {
        **state.get("result", {}),
        "knowledge_id": state["knowledge_id"],
        "entry": state["knowledge_entry"],
        "triplet": state["triplet"],
    }
    return state


def create_knowledge_graph() -> StateGraph:
    workflow = StateGraph(KnowledgeState)

    workflow.add_node("extract_triplet", extract_triplet)
    workflow.add_node("generate_entry", generate_entry)
    workflow.add_node("entry_quality_check", entry_quality_check)
    workflow.add_node("dedup_check", dedup_check)
    workflow.add_node("store_embedding", store_embedding)
    workflow.add_node("build_output", build_output)

    workflow.set_entry_point("extract_triplet")
    workflow.add_edge("extract_triplet", "generate_entry")

    # 条件分支: 四段式内容不完整 → 回退到 generate_entry 重试
    workflow.add_edge("generate_entry", "entry_quality_check")
    workflow.add_conditional_edges(
        "entry_quality_check",
        should_retry_entry,
        {"pass": "dedup_check", "retry": "generate_entry"},
    )

    # 条件分支: 去重命中 → 跳过存储节点, 直接到 build_output
    def should_skip_store(state: KnowledgeState) -> str:
        if state.get("result", {}).get("dedup_hit"):
            return "skip"
        return "store"

    workflow.add_conditional_edges(
        "dedup_check",
        should_skip_store,
        {"skip": "build_output", "store": "store_embedding"},
    )
    workflow.add_edge("store_embedding", "build_output")
    workflow.add_edge("build_output", END)

    return workflow.compile()


knowledge_workflow = create_knowledge_graph()
