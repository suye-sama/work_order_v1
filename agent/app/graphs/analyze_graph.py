"""
故障分析 LangGraph 工作流

流程：相似检索 → 对比分析 → 风险评估 → 改进建议
"""
import json, re
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from app.llm.factory import get_llm
from app.prompts.fault_analyze import COMPARISON_PROMPT, RISK_ASSESSMENT_PROMPT, IMPROVEMENT_PROMPT, CHALLENGER_PROMPT, DEFENDER_PROMPT
from app.memory.vector_store import search_similar


class AnalyzeState(TypedDict):
    # 输入
    ticket_id: Optional[int]
    title: str
    fault_phenomenon: str
    root_cause: str
    solution: str
    category: str
    customer_info: str

    # 中间结果
    similar_cases: list[dict]
    comparison: dict
    risk: dict
    improvement: dict

    # 辩论循环
    debate_round: int
    _challenges: list[str]

    # 输出
    result: dict
    error: Optional[str]


def _safe_json(text: str, fallback: dict) -> dict:
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if md:
        try: return json.loads(md.group(1))
        except: pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group(0))
        except: pass
    return fallback


def search_cases(state: AnalyzeState) -> AnalyzeState:
    """Node 1: 相似案例检索"""
    query = state["title"] + " " + state.get("fault_phenomenon", "")
    try:
        items = search_similar(query[:300], top_k=5)
    except Exception:
        items = []
    state["similar_cases"] = items
    return state


def compare_analysis(state: AnalyzeState) -> AnalyzeState:
    """Node 2: 对比分析（LLM）"""
    similar = state["similar_cases"]

    if similar:
        cases_text = "\n\n".join(
            f"- 案例{i+1}: {c.get('title','')} (相似度:{c.get('similarity',0):.2f})"
            for i, c in enumerate(similar[:3])
        )
    else:
        cases_text = "（无相似历史案例）"

    try:
        llm = get_llm(temperature=0.3)
        prompt = COMPARISON_PROMPT.format(
            title=state["title"],
            fault_phenomenon=state.get("fault_phenomenon", "")[:500],
            root_cause=state.get("root_cause", "")[:500],
            category=state.get("category", "待分类"),
            similar_cases_text=cases_text,
        )
        resp = llm.invoke(prompt)
        state["comparison"] = _safe_json(resp.content, {
            "is_known_issue": len(similar) > 0,
            "comparison": f"发现 {len(similar)} 个相似案例" if similar else "无相似案例",
            "can_reuse_solution": False,
            "primary_reference": similar[0].get("title", "") if similar else "",
        })
    except Exception as e:
        print(f"[Fault] 对比分析失败: {e}")
        state["comparison"] = {"is_known_issue": False, "comparison": "分析失败", "can_reuse_solution": False, "primary_reference": ""}
    return state


def assess_risk(state: AnalyzeState) -> AnalyzeState:
    """Node 3: 风险评估（LLM）"""
    try:
        llm = get_llm(temperature=0.2)
        prompt = RISK_ASSESSMENT_PROMPT.format(
            title=state["title"],
            fault_phenomenon=state.get("fault_phenomenon", "")[:500],
            root_cause=state.get("root_cause", "")[:500],
            solution=state.get("solution", "")[:500],
            comparison=state["comparison"].get("comparison", ""),
        )
        resp = llm.invoke(prompt)
        state["risk"] = _safe_json(resp.content, {
            "severity": "中", "recurrence_risk": "中",
            "affected_versions": [], "risk_detail": "风险评估待补充",
        })
    except Exception as e:
        print(f"[Fault] 风险评估失败: {e}")
        state["risk"] = {"severity": "中", "recurrence_risk": "中", "affected_versions": [], "risk_detail": str(e)[:200]}
    return state


def challenger(state: AnalyzeState) -> AnalyzeState:
    """辩论-质疑方: 审计员视角质疑当前风险评估"""
    risk = state["risk"]
    debate_round = state.get("debate_round", 0)

    try:
        llm = get_llm(temperature=0.4)  # 稍高温度, 鼓励多角度质疑
        prompt = CHALLENGER_PROMPT.format(
            title=state["title"],
            root_cause=state.get("root_cause", "")[:400],
            severity=risk.get("severity", "中"),
            recurrence_risk=risk.get("recurrence_risk", "中"),
            risk_detail=risk.get("risk_detail", ""),
            round=debate_round + 1,
        )
        resp = llm.invoke(prompt)
        result = _safe_json(resp.content, {"has_challenges": False, "challenges": []})
    except Exception as e:
        print(f"[Fault] 质疑生成失败: {e}")
        result = {"has_challenges": False, "challenges": []}

    state["_challenges"] = result.get("challenges", [])
    return state


def defender(state: AnalyzeState) -> AnalyzeState:
    """辩论-回应方: 根据质疑修正风险评估"""
    challenges = state.get("_challenges", [])
    risk = state["risk"]
    debate_round = state.get("debate_round", 0)

    if not challenges:
        # 无质疑, 直接通过
        return state

    try:
        llm = get_llm(temperature=0.2)
        prompt = DEFENDER_PROMPT.format(
            risk=json.dumps(risk, ensure_ascii=False)[:1500],
            challenges=json.dumps(challenges, ensure_ascii=False)[:1000],
        )
        resp = llm.invoke(prompt)
        revised = _safe_json(resp.content, risk)
    except Exception as e:
        print(f"[Fault] 辩论回应失败: {e}")
        revised = risk

    state["risk"] = {
        "severity": revised.get("severity", risk.get("severity", "中")),
        "recurrence_risk": revised.get("recurrence_risk", risk.get("recurrence_risk", "中")),
        "affected_versions": risk.get("affected_versions", []),
        "risk_detail": revised.get("risk_detail", risk.get("risk_detail", "")),
    }
    state["debate_round"] = debate_round + 1
    return state


def should_continue_debate(state: AnalyzeState) -> str:
    """判断是否继续辩论"""
    if state.get("debate_round", 0) >= 2:
        return "end"
    if state.get("_challenges"):
        return "debate"
    return "end"


def suggest_improvement(state: AnalyzeState) -> AnalyzeState:
    """Node 4: 改进建议（LLM）"""
    risk = state["risk"]
    try:
        llm = get_llm(temperature=0.3)
        prompt = IMPROVEMENT_PROMPT.format(
            title=state["title"],
            root_cause=state.get("root_cause", "")[:400],
            risk_detail=risk.get("risk_detail", ""),
            recurrence_risk=risk.get("recurrence_risk", "中"),
        )
        resp = llm.invoke(prompt)
        state["improvement"] = _safe_json(resp.content, {
            "prevention": "加强监控和自动恢复机制",
            "long_term_advice": "建议完善运维流程",
        })
    except Exception as e:
        print(f"[Fault] 改进建议生成失败: {e}")
        state["improvement"] = {"prevention": "建议待补充", "long_term_advice": "建议待补充"}
    return state


def reuse_result(state: AnalyzeState) -> AnalyzeState:
    """复用历史分析结论 — 已知问题直接跳过LLM分析"""
    case = state["similar_cases"][0]
    sim_pct = f"{case.get('similarity', 0) * 100:.0f}%"

    state["comparison"] = {
        "is_known_issue": True,
        "comparison": f"与历史案例「{case.get('title', '')}」高度匹配（相似度 {sim_pct}），直接复用历史分析结论",
        "can_reuse_solution": True,
        "primary_reference": case.get("title", ""),
    }
    state["risk"] = {
        "severity": "参照历史",
        "recurrence_risk": "参照历史",
        "affected_versions": [],
        "risk_detail": f"该问题为已知历史问题，相似度 {sim_pct}，无需重新评估",
    }
    state["improvement"] = {
        "prevention": "参照历史案例的预防措施",
        "long_term_advice": f"该问题已多次出现，建议参考历史案例「{case.get('title', '')}」的长期方案",
    }
    return state


def assemble(state: AnalyzeState) -> AnalyzeState:
    """Node 5: 组装输出"""
    state["result"] = {
        "is_known_issue": state["comparison"].get("is_known_issue", False),
        "similar_cases": [
            {"title": c.get("title", ""), "similarity": c.get("similarity", 0)}
            for c in state.get("similar_cases", [])[:3]
        ],
        "fault_category": state.get("category", ""),
        "severity": state["risk"].get("severity", "中"),
        "recurrence_risk": state["risk"].get("recurrence_risk", "中"),
        "affected_versions": state["risk"].get("affected_versions", []),
        "comparison": state["comparison"].get("comparison", ""),
        "risk_detail": state["risk"].get("risk_detail", ""),
        "prevention": state["improvement"].get("prevention", ""),
        "long_term_advice": state["improvement"].get("long_term_advice", ""),
    }
    state["error"] = None
    return state


def create_analyze_graph() -> StateGraph:
    workflow = StateGraph(AnalyzeState)
    workflow.add_node("search_cases", search_cases)
    workflow.add_node("reuse_result", reuse_result)
    workflow.add_node("compare_analysis", compare_analysis)
    workflow.add_node("assess_risk", assess_risk)
    workflow.add_node("challenger", challenger)
    workflow.add_node("defender", defender)
    workflow.add_node("suggest_improvement", suggest_improvement)
    workflow.add_node("assemble", assemble)

    workflow.set_entry_point("search_cases")

    # 条件分支1: 搜索路由 — 已知问题/有案例/无案例
    def route_search_result(state: AnalyzeState) -> str:
        cases = state.get("similar_cases", [])
        if cases and cases[0].get("similarity", 0) > 0.98:
            return "reuse"
        if cases:
            return "compare"
        return "risk"

    workflow.add_conditional_edges(
        "search_cases",
        route_search_result,
        {"reuse": "reuse_result", "compare": "compare_analysis", "risk": "assess_risk"},
    )
    workflow.add_edge("compare_analysis", "assess_risk")

    # 辩论循环: assess_risk → challenger → defender → assess_risk (最多2轮)
    workflow.add_edge("assess_risk", "challenger")
    workflow.add_conditional_edges(
        "challenger",
        should_continue_debate,
        {"debate": "defender", "end": "suggest_improvement"},
    )
    workflow.add_edge("defender", "assess_risk")

    workflow.add_edge("suggest_improvement", "assemble")
    workflow.add_edge("reuse_result", "assemble")
    workflow.add_edge("assemble", END)

    return workflow.compile()


analyze_workflow = create_analyze_graph()