"""
工单生成 LangGraph 工作流 — 多视角并行 + 质量校验回调

流程：
  Stage 1: 故障现象提取 → fault_phenomenon
  Stage 2: 排查过程梳理 → troubleshooting
  Stage 3: 多视角并行生成（故障专家 + 方案专家 + 摘要专家）
  Stage 4: 综合校验 → root_cause + solution + summary_info
  Stage 5: 质量校验 → 不合格回退 Stage 3 重试
  Stage 6: 结构化组装 → 完整工单 JSON

优化要点：
  - 数据不足 → 降级到 fallback_summary，跳过 Stage 3-4
  - 质量不合格 → 回退到 parallel_specialists 重试（最多2次）
"""
import json
import re
import concurrent.futures
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from app.llm.factory import get_llm
from app.prompts.ticket_generate import (
    FAULT_PHENOMENON_PROMPT,
    TROUBLESHOOTING_PROMPT,
    ROOT_CAUSE_PROMPT,
    SOLUTION_PROMPT,
    SUMMARY_PROMPT,
    FAULT_SPECIALIST_PROMPT,
    SOLUTION_SPECIALIST_PROMPT,
    SUMMARY_SPECIALIST_PROMPT,
    SYNTHESIZER_PROMPT,
)


# ====== State 定义 ======


class GenerateState(TypedDict):
    """工单生成工作流状态"""

    # 输入
    title: str
    description: str
    customer_info: str
    timeline_json: Optional[list]
    raw_log: str
    engineer_notes: str

    # Stage 1-5 中间结果
    fault_phenomenon: dict
    troubleshooting: list[dict]
    root_cause: dict
    solution: dict
    summary_info: dict

    # 质量校验与重试
    retry_count: int
    _quality_issues: list[str]

    # 最终输出
    result: dict
    error: Optional[str]


# ====== 节点函数 ======


def _safe_llm_invoke(prompt: str, fallback: dict | list) -> dict | list:
    """安全调用 LLM，失败返回降级结果"""
    try:
        llm = get_llm(temperature=0.3)
        response = llm.invoke(prompt)
        content = response.content

        # 1. 尝试提取 markdown 代码块
        md_json = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if md_json:
            try:
                return json.loads(md_json.group(1))
            except json.JSONDecodeError:
                pass
        md_arr = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.DOTALL)
        if md_arr:
            try:
                return json.loads(md_arr.group(1))
            except json.JSONDecodeError:
                pass

        # 2. 尝试直接提取 JSON
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        arr_match = re.search(r"\[.*\]", content, re.DOTALL)
        if arr_match:
            try:
                return json.loads(arr_match.group(0))
            except json.JSONDecodeError:
                pass

        return fallback
    except Exception as e:
        print(f"[Agent] LLM 调用失败，使用降级: {e}")
        return fallback


def extract_fault(state: GenerateState) -> GenerateState:
    """Stage 1: 提取故障现象"""
    log_text = state.get("raw_log", "") or ""
    timeline = state.get("timeline_json") or []

    # 构建上下文字段
    timeline_text = ""
    if timeline:
        timeline_text = "\n".join(
            f"{t.get('step','')}. [{t.get('phase','')}] {t.get('command','')} → {t.get('summary','')}"
            for t in timeline
        )[:2000]

    if log_text or timeline_text:
        prompt = FAULT_PHENOMENON_PROMPT.format(
            title=state["title"],
            description=state.get("description", "") or "无",
            customer_info=state.get("customer_info", "") or "未知",
            log_text=(log_text + "\n时间线:\n" + timeline_text)[:3000],
        )
        result = _safe_llm_invoke(prompt, {"phenomenon": state["title"], "impact_scope": "待确认"})
    else:
        result = {
            "phenomenon": state["title"],
            "impact_scope": "待确认（缺少操作日志数据）",
            "occurrence_time": None,
        }

    if isinstance(result, list):
        result = result[0] if result else {"phenomenon": state["title"], "impact_scope": "待确认"}
    state["fault_phenomenon"] = result
    return state


def extract_troubleshooting(state: GenerateState) -> GenerateState:
    """Stage 2: 梳理排查过程"""
    log_text = state.get("raw_log", "") or ""
    timeline = state.get("timeline_json") or []
    fault = state.get("fault_phenomenon", {})

    # 优先使用时间线数据进行梳理
    timeline_text = "\n".join(
        f"Step {t.get('step','?')}: [{t.get('phase','')}] {t.get('command','')} → {t.get('summary','')}"
        for t in (timeline or [])
    )[:3000] if timeline else "（无时间线数据）"

    if timeline or log_text:
        prompt = TROUBLESHOOTING_PROMPT.format(
            title=state["title"],
            fault_phenomenon=fault.get("phenomenon", state["title"]),
            timeline_text=timeline_text,
            log_text=(log_text or "")[:2000],
        )
        result = _safe_llm_invoke(prompt, [])
    else:
        result = [{"step": 1, "action": "待补充排查过程", "finding": "缺少日志数据"}]

    if isinstance(result, dict):
        result = [result]
    state["troubleshooting"] = result or []
    return state


def analyze_root_cause(state: GenerateState) -> GenerateState:
    """Stage 3: 根因分析"""
    fault = state.get("fault_phenomenon", {})
    troubleshooting = state.get("troubleshooting", [])
    notes = state.get("engineer_notes", "") or ""

    t_text = "\n".join(
        f"{t.get('step','')}. {t.get('action','')} → {t.get('finding','')}"
        for t in troubleshooting
    )

    prompt = ROOT_CAUSE_PROMPT.format(
        fault_phenomenon=fault.get("phenomenon", state["title"]),
        troubleshooting_text=t_text[:2000] if t_text else "待补充",
        engineer_notes=notes[:500] if notes else "无",
    )
    result = _safe_llm_invoke(prompt, {
        "root_cause": "待分析（需更多数据）",
        "detail": "缺少足够的排查数据，无法完成根因分析。请补充操作日志后重试。",
        "category": "待分类",
    })

    if isinstance(result, list):
        result = result[0] if result else {"root_cause": "待分析"}
    state["root_cause"] = result
    return state


def summarize_solution(state: GenerateState) -> GenerateState:
    """Stage 4: 总结解决方案"""
    root_cause = state.get("root_cause", {})
    troubleshooting = state.get("troubleshooting", [])

    t_text = "\n".join(
        f"{t.get('step','')}. {t.get('action','')} → {t.get('finding','')}"
        for t in troubleshooting
    )

    prompt = SOLUTION_PROMPT.format(
        root_cause=root_cause.get("root_cause", "未知"),
        troubleshooting_text=t_text[:2000] if t_text else "待补充",
    )
    result = _safe_llm_invoke(prompt, {
        "solution": "待总结",
        "steps": [],
        "suggestion": "建议补充完整的操作日志以获取准确的解决方案",
    })

    if isinstance(result, list):
        result = result[0] if result else {"solution": "待总结"}
    state["solution"] = result
    return state


def generate_summary(state: GenerateState) -> GenerateState:
    """Stage 5: 生成工单摘要"""
    fault = state.get("fault_phenomenon", {})
    root_cause = state.get("root_cause", {})
    solution = state.get("solution", {})

    # 将 retry_count 注入 state（如果是第一次生成）
    retry = state.get("retry_count", 0)

    # 如果上次校验有质量问题, 把反馈拼入 prompt
    quality_feedback = state.get("_quality_issues", [])
    extra_context = ""
    if quality_feedback:
        extra_context = "\n\n【上次生成质量问题, 请针对性修正】\n" + "\n".join(f"- {q}" for q in quality_feedback)

    prompt = SUMMARY_PROMPT.format(
        title=state["title"],
        fault_phenomenon=fault.get("phenomenon", state["title"]),
        root_cause=root_cause.get("root_cause", "待分析"),
        solution=solution.get("solution", "待总结"),
        duration="未知",
    ) + extra_context
    result = _safe_llm_invoke(prompt, {
        "summary": f"工单：{state['title']}。故障已修复。",
        "tags": ["待分类"],
        "estimated_duration_minutes": None,
    })

    if isinstance(result, list):
        result = result[0] if result else {}
    state["summary_info"] = result
    state["retry_count"] = retry + 1
    state["_quality_issues"] = []
    return state


def fallback_summary(state: GenerateState) -> GenerateState:
    """降级: 数据不足时跳过排查/根因/方案LLM, 直接生成简单摘要"""
    state["fault_phenomenon"] = state.get("fault_phenomenon") or {
        "phenomenon": state["title"],
        "impact_scope": "待确认（缺少操作日志数据）",
    }
    state["troubleshooting"] = [{"step": 1, "action": "待补充排查过程", "finding": "缺少操作日志"}]
    state["root_cause"] = {
        "root_cause": "待分析（缺少数据）",
        "detail": "缺少日志或时间线数据，无法完成根因分析",
        "category": state.get("root_cause", {}).get("category", "待分类"),
    }
    state["solution"] = {"solution": "待补充", "steps": [], "suggestion": "请补充操作日志后重新生成"}
    state["summary_info"] = {
        "summary": f"工单：{state['title']}。需补充操作日志以完成自动生成。",
        "tags": ["数据待补充"],
        "estimated_duration_minutes": None,
    }
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["_quality_issues"] = []
    return state


def parallel_specialists(state: GenerateState) -> GenerateState:
    """Stage 3: 多视角并行生成 — 3个LLM specialist同时调用"""
    fault_view = state.get("fault_phenomenon", {})
    troubleshooting = state.get("troubleshooting", [])
    notes = state.get("engineer_notes", "") or ""
    quality_feedback = state.get("_quality_issues", [])

    t_text = "\n".join(
        f"{t.get('step','')}. {t.get('action','')} → {t.get('finding','')}"
        for t in troubleshooting
    )
    fp_text = fault_view.get("phenomenon", state["title"]) if isinstance(fault_view, dict) else str(fault_view)

    # 质量反馈上下文
    extra_feedback = ""
    if quality_feedback:
        extra_feedback = "\n\n【上次质量校验未通过，请针对性改进】\n" + "\n".join(f"- {q}" for q in quality_feedback)

    # 故障专家视角
    fault_prompt = FAULT_SPECIALIST_PROMPT.format(
        title=state["title"],
        fault_phenomenon=fp_text,
        troubleshooting_text=t_text[:2000] if t_text else "待补充",
        engineer_notes=notes[:500] if notes else "无",
    ) + extra_feedback

    # 解决方案专家视角
    solution_prompt = SOLUTION_SPECIALIST_PROMPT.format(
        title=state["title"],
        fault_phenomenon=fp_text,
        troubleshooting_text=t_text[:2000] if t_text else "待补充",
    ) + extra_feedback

    # 摘要专家视角
    summary_prompt = SUMMARY_SPECIALIST_PROMPT.format(
        title=state["title"],
        fault_phenomenon=fp_text,
    )

    def call_fault_specialist():
        return _safe_llm_invoke(fault_prompt, state.get("root_cause") or {
            "root_cause": "待分析", "detail": "并行生成失败", "category": "待分类",
        })

    def call_solution_specialist():
        return _safe_llm_invoke(solution_prompt, state.get("solution") or {
            "solution": "待总结", "steps": [], "suggestion": "",
        })

    def call_summary_specialist():
        return _safe_llm_invoke(summary_prompt, state.get("summary_info") or {
            "summary": f"工单：{state['title']}", "tags": ["待分类"],
        })

    # 并行执行
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f1 = pool.submit(call_fault_specialist)
        f2 = pool.submit(call_solution_specialist)
        f3 = pool.submit(call_summary_specialist)
        fault_result = f1.result()
        solution_result = f2.result()
        summary_result = f3.result()

    if isinstance(fault_result, list):
        fault_result = fault_result[0] if fault_result else {}
    if isinstance(solution_result, list):
        solution_result = solution_result[0] if solution_result else {}
    if isinstance(summary_result, list):
        summary_result = summary_result[0] if summary_result else {}

    state["_fault_view"] = fault_result
    state["_solution_view"] = solution_result
    state["_summary_view"] = summary_result
    return state


def synthesizer(state: GenerateState) -> GenerateState:
    """Stage 4: 综合三方结果，做一致性校验"""
    fault_view = json.dumps(state.get("_fault_view", {}), ensure_ascii=False)
    solution_view = json.dumps(state.get("_solution_view", {}), ensure_ascii=False)
    summary_view = json.dumps(state.get("_summary_view", {}), ensure_ascii=False)

    result = _safe_llm_invoke(
        SYNTHESIZER_PROMPT.format(
            title=state["title"],
            fault_view=fault_view[:1500],
            solution_view=solution_view[:1500],
            summary_view=summary_view[:1500],
        ),
        {
            "root_cause": state.get("_fault_view") or {},
            "solution": state.get("_solution_view") or {},
            "summary_info": state.get("_summary_view") or {},
            "consistency_note": "综合失败，使用 fallback",
        },
    )
    if isinstance(result, list):
        result = result[0] if result else {}

    # 提取各字段；如果 synthetizer 的 JSON 结构不完整则降级
    root_cause = result.get("root_cause") or state.get("_fault_view") or {}
    solution = result.get("solution") or state.get("_solution_view") or {}
    summary_info = result.get("summary_info") or state.get("_summary_view") or {}

    if isinstance(root_cause, list):
        root_cause = root_cause[0] if root_cause else {}
    if isinstance(solution, list):
        solution = solution[0] if solution else {}
    if isinstance(summary_info, list):
        summary_info = summary_info[0] if summary_info else {}

    state["root_cause"] = root_cause
    state["solution"] = solution
    state["summary_info"] = summary_info
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["_quality_issues"] = []
    return state


def quality_check(state: GenerateState) -> GenerateState:
    """校验摘要质量: 过短、未提及标题、结构不完整等"""
    summary_info = state.get("summary_info", {})
    text = summary_info.get("summary", "")
    issues = []

    if len(text) < 20:
        issues.append("摘要过短 (<20字符)")
    if state["title"] not in text and len(text) < 30:
        issues.append("摘要未提及工单标题")
    if not summary_info.get("tags"):
        issues.append("缺少标签")

    state["_quality_issues"] = issues
    return state


def should_retry(state: GenerateState) -> str:
    """判断是否需要重试"""
    issues = state.get("_quality_issues", [])
    if not issues:
        return "pass"
    if state.get("retry_count", 0) < 2:
        return "retry"
    # 超过重试次数, 强制通过
    return "pass"


def assemble_result(state: GenerateState) -> GenerateState:
    """Stage 6: 组装最终工单 JSON（纯代码，不调 LLM）"""
    state["result"] = {
        "fault_phenomenon": state.get("fault_phenomenon", {}),
        "troubleshooting": state.get("troubleshooting", []),
        "root_cause": state.get("root_cause", {}),
        "solution": state.get("solution", {}),
        "summary_info": state.get("summary_info", {}),
    }
    state["error"] = None
    return state


# ====== 构建 LangGraph 工作流 ======


def create_generate_graph() -> StateGraph:
    """创建工单生成 LangGraph 工作流"""
    workflow = StateGraph(GenerateState)

    workflow.add_node("extract_fault", extract_fault)
    workflow.add_node("extract_troubleshooting", extract_troubleshooting)
    workflow.add_node("parallel_specialists", parallel_specialists)
    workflow.add_node("synthesizer", synthesizer)
    workflow.add_node("fallback_summary", fallback_summary)
    workflow.add_node("quality_check", quality_check)
    workflow.add_node("assemble", assemble_result)

    workflow.set_entry_point("extract_fault")

    # 条件分支1: 数据不足 → 降级路径, 跳过LLM
    def has_enough_data(state: GenerateState) -> str:
        has_log = bool(state.get("raw_log", ""))
        has_timeline = bool(state.get("timeline_json"))
        has_desc = bool(state.get("description", ""))
        if has_log or has_timeline or has_desc:
            return "full"
        return "fallback"

    workflow.add_conditional_edges(
        "extract_fault",
        has_enough_data,
        {"full": "extract_troubleshooting", "fallback": "fallback_summary"},
    )
    workflow.add_edge("extract_troubleshooting", "parallel_specialists")
    workflow.add_edge("parallel_specialists", "synthesizer")

    # 条件分支2: 质量不合格 & retry<2 → 回退到 parallel_specialists 重试
    workflow.add_edge("synthesizer", "quality_check")
    workflow.add_edge("fallback_summary", "quality_check")
    workflow.add_conditional_edges(
        "quality_check",
        should_retry,
        {"pass": "assemble", "retry": "parallel_specialists"},
    )
    workflow.add_edge("assemble", END)

    return workflow.compile()


generate_workflow = create_generate_graph()
