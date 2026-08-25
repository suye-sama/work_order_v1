"""
轻量化售后工单系统 - Flask Agent 智能服务
"""
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

# 加载 .env 文件（项目根目录）
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(env_path)

app = Flask(__name__)
CORS(app)


# ==================== 基础接口 ====================


@app.route("/")
def root():
    """根路径 - 服务信息"""
    return jsonify({
        "service": "售后工单系统 - Flask Agent 智能服务",
        "version": "0.1.0",
        "status": "running",
    })


@app.route("/agent/health")
def health_check():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "flask-agent",
    })


@app.route("/agent/info")
def agent_info():
    """获取 Agent 配置信息"""
    from app.llm.factory import get_llm_info
    return jsonify({
        "llm": get_llm_info(),
        "available_agents": [
            "process_recorder (日志解析)",
            "ticket_generator (工单生成)",
            "knowledge_extractor (知识提取)",
            "ticket_search (相似检索)",
            "fault_analyzer (故障分析)",
            "ticket_suggester (排查建议)",
        ],
    })


# ==================== Agent 1: 日志解析 ====================


@app.route("/agent/log/parse", methods=["POST"])
def log_parse():
    """
    日志解析接口 — 将终端操作日志转换为结构化时间线

    请求: { "log_text": "...", "ticket_id": 1 }
    响应: { "timeline": [...], "phase_count": 3, "total_steps": 10, ... }
    """
    data = request.get_json(silent=True) or {}
    log_text = data.get("log_text", "")
    ticket_id = data.get("ticket_id")

    if not log_text:
        return jsonify({"error": "log_text 不能为空", "timeline": []}), 400

    from app.agents.process_recorder import parse_log

    result = parse_log(log_text, ticket_id)
    return jsonify(result)


# ==================== Agent 2: 工单生成 ====================


@app.route("/agent/ticket/generate", methods=["POST"])
def ticket_generate():
    """
    工单生成接口 — 汇总售后数据，自动生成标准工单

    请求: {
        "ticket_id": 1,
        "title": "...",
        "description": "...",
        "customer_info": "...",
        "timeline_json": [...],
        "raw_log": "...",
        "engineer_notes": "..."
    }
    响应: {
        "success": true,
        "ticket_id": 1,
        "result": { fault_phenomenon, troubleshooting, root_cause, solution, summary_info },
        "duration_ms": 1234
    }
    """
    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    if not title:
        return jsonify({"success": False, "error": "工单标题不能为空"}), 400

    from app.agents.ticket_generator import generate_ticket

    result = generate_ticket(
        title=title,
        description=data.get("description", ""),
        customer_info=data.get("customer_info", ""),
        timeline_json=data.get("timeline_json"),
        raw_log=data.get("raw_log", ""),
        engineer_notes=data.get("engineer_notes", ""),
        ticket_id=data.get("ticket_id"),
    )
    return jsonify(result)


# ==================== Agent 3: 知识提取 ====================


@app.route("/agent/knowledge/extract", methods=["POST"])
def knowledge_extract():
    """
    知识提取接口 — 从工单中提取知识条目并存入向量库

    请求: {
        "ticket_id": 1,
        "title": "...",
        "fault_phenomenon": {...},
        "root_cause": {...},
        "solution": {...},
        "summary_info": {...}
    }
    """
    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    if not title:
        return jsonify({"success": False, "error": "工单标题不能为空"}), 400

    from app.agents.knowledge_extractor import extract_knowledge

    result = extract_knowledge(
        ticket_id=data.get("ticket_id"),
        title=title,
        fault_phenomenon=data.get("fault_phenomenon"),
        root_cause=data.get("root_cause"),
        solution=data.get("solution"),
        summary_info=data.get("summary_info"),
        tags=data.get("tags", []),
        category=data.get("category", ""),
        customer_info=data.get("customer_info", ""),
    )
    return jsonify(result)


# ==================== Agent 4: 相似工单检索 ====================


@app.route("/agent/search", methods=["POST"])
def search_tickets():
    """
    相似工单检索 — 输入故障描述，返回最相似的历史工单

    请求: { "query": "Nginx 502 错误", "top_k": 5 }
    """
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    top_k = data.get("top_k", 5)

    if not query:
        return jsonify({"items": [], "error": "查询文本不能为空"}), 400

    from app.agents.knowledge_extractor import search_knowledge

    result = search_knowledge(query, top_k)
    return jsonify(result)


# ==================== Agent 5: 知识库管理 ====================


@app.route("/agent/knowledge/list", methods=["GET"])
def knowledge_list():
    """
    知识库列表 — 分页获取所有知识条目，支持关键词搜索

    查询参数:
        keyword  - 搜索关键词（可选）
        category - 分类筛选（可选）
        page     - 页码，默认 1
        page_size - 每页数量，默认 20
    """
    from app.memory.vector_store import list_all_knowledge

    keyword = request.args.get("keyword", "")
    category = request.args.get("category", "")
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    result = list_all_knowledge(
        keyword=keyword,
        category=category,
        page=page,
        page_size=page_size,
    )
    return jsonify(result)


@app.route("/agent/knowledge/<knowledge_id>", methods=["GET"])
def knowledge_detail(knowledge_id):
    """
    知识条目详情 — 根据 ID 获取单条知识

    路径参数:
        knowledge_id - 知识条目 ID（如 kb-1）
    """
    from app.memory.vector_store import get_knowledge_by_id

    item = get_knowledge_by_id(knowledge_id)
    if item is None:
        return jsonify({"error": "知识条目不存在"}), 404
    return jsonify(item)


@app.route("/agent/knowledge/export/all", methods=["GET"])
def knowledge_export():
    """
    知识库全量导出 — 返回所有知识条目（不分页），供 Excel 导出使用

    查询参数:
        keyword - 搜索关键词（可选，过滤标题和问题描述）
        category - 分类筛选（可选）
    """
    from app.memory.vector_store import list_all_knowledge

    keyword = request.args.get("keyword", "")
    category = request.args.get("category", "")

    # 获取全量数据（page_size 设大值）
    result = list_all_knowledge(
        keyword=keyword,
        category=category,
        page=1,
        page_size=10000,
    )
    return jsonify(result)


# ==================== Agent 6: 排查方向建议 ====================


@app.route("/agent/ticket/suggest", methods=["POST"])
def ticket_suggest():
    """
    排查方向建议 — 根据工单描述，检索相似案例 + LLM 推理，生成排查建议

    请求: {
        "title": "教务系统无法登录",
        "description": "教师反馈登录页面一直转圈...",
        "category": "系统故障",
        "customer_info": "Linux CentOS 7.9 / 教务系统 V3.2.0"
    }
    响应: {
        "success": true,
        "possible_causes": [...],
        "suggested_checks": [{direction, why, command, expected_if_problem}, ...],
        "similar_cases": [...],
        "brief_analysis": "...",
        "duration_ms": 1234
    }
    """
    data = request.get_json(silent=True) or {}

    title = data.get("title", "")
    if not title:
        return jsonify({"success": False, "error": "工单标题不能为空"}), 400

    from app.agents.suggester import suggest_checks

    result = suggest_checks(
        title=title,
        description=data.get("description", ""),
        category=data.get("category", ""),
        customer_info=data.get("customer_info", ""),
    )
    return jsonify(result)


# ==================== Agent 5: 故障分析 ====================


@app.route("/agent/fault/analyze", methods=["POST"])
def fault_analyze():
    """
    故障分析接口 — 深度分析工单，评估风险，提出改进建议

    请求: {
        "ticket_id": 1,
        "title": "...",
        "fault_phenomenon": {...},
        "root_cause": {...},
        "solution": {...},
        "category": "系统故障"
    }
    """
    data = request.get_json(silent=True) or {}
    title = data.get("title", "")
    if not title:
        return jsonify({"success": False, "error": "工单标题不能为空"}), 400

    from app.agents.fault_analyzer import analyze_fault

    result = analyze_fault(
        ticket_id=data.get("ticket_id"),
        title=title,
        fault_phenomenon=data.get("fault_phenomenon"),
        root_cause=data.get("root_cause"),
        solution=data.get("solution"),
        category=data.get("category", ""),
        customer_info=data.get("customer_info", ""),
    )
    return jsonify(result)


# ==================== 启动入口 ====================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
