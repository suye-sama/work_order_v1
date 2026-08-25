"""
飞书事件回调路由 — 接收飞书开放平台推送的消息事件

关键设计：
  1. 收到回调后立即返回（满足飞书 3 秒超时限制）
  2. 业务逻辑通过 asyncio.create_task 异步执行
  3. 限流使用内存字典（本地开发无 Redis）
  4. 手动解析 V2 事件体，不依赖 lark_oapi SDK
"""
import asyncio
import json
import re
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.integrations.feishu_client import send_text_message
from app.tasks.agent_tasks import handle_log_parse, handle_similarity_search

router = APIRouter(prefix="/feishu", tags=["飞书回调"])

# ==================== 内存限流器（本地开发，无 Redis） ====================

_rate_limit_store: dict[str, list[float]] = {}
_RATE_LIMIT_WINDOW = 60   # 窗口 60 秒
_RATE_LIMIT_MAX = 10       # 上限 10 次
_RATE_LIMIT_CLEAN_INTERVAL = 300  # 每 5 分钟全量清理一次过期用户


def check_rate_limit(user_id: str) -> bool:
    """内存限流检查：同一用户每分钟最多 10 次请求"""
    now = time.time()

    # 定期全量清理过期条目（防止内存泄漏）
    if not hasattr(check_rate_limit, "_last_clean"):
        check_rate_limit._last_clean = now  # type: ignore
    if now - check_rate_limit._last_clean > _RATE_LIMIT_CLEAN_INTERVAL:  # type: ignore
        expired_users = [
            uid for uid, timestamps in _rate_limit_store.items()
            if all(t <= now - _RATE_LIMIT_WINDOW for t in timestamps)
        ]
        for uid in expired_users:
            del _rate_limit_store[uid]
        check_rate_limit._last_clean = now  # type: ignore

    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = []

    # 清理当前用户过期记录
    window_start = now - _RATE_LIMIT_WINDOW
    _rate_limit_store[user_id] = [
        t for t in _rate_limit_store[user_id] if t > window_start
    ]

    if len(_rate_limit_store[user_id]) >= _RATE_LIMIT_MAX:
        return False

    _rate_limit_store[user_id].append(now)
    return True


# ==================== 路由 ====================


@router.post("/event")
async def feishu_event_callback(request: Request):
    """
    飞书事件回调入口

    URL 验证：手动处理
    消息事件：手动解析 V2 事件体
    """
    try:
        body_dict = await request.json()

        # ---- URL 验证 ----
        if body_dict.get("type") == "url_verification":
            return JSONResponse(content={"challenge": body_dict.get("challenge", "")})

        # ---- V2 消息事件 ----
        event_type = body_dict.get("header", {}).get("event_type", "")
        if event_type != "im.message.receive_v1":
            return JSONResponse(content={"code": 0})

        event_data = body_dict.get("event", {})
        message = event_data.get("message", {})
        msg_type = message.get("message_type", "")

        if msg_type != "text":
            return JSONResponse(content={"code": 0})

        # 解析文本内容
        content_str = message.get("content", "{}")
        try:
            content_obj = json.loads(content_str)
            text = content_obj.get("text", "").strip()
        except (json.JSONDecodeError, TypeError):
            return JSONResponse(content={"code": 0})

        if not text:
            return JSONResponse(content={"code": 0})

        # 去掉 @机器人 前缀（群聊中消息格式为 "@_user_1 实际内容"）
        text = re.sub(r'^@\S+\s*', '', text).strip()
        if not text:
            return JSONResponse(content={"code": 0})

        # 提取用户和会话 ID
        sender_id = event_data.get("sender", {}).get("sender_id", {})
        user_id = sender_id.get("user_id", "unknown")
        chat_id = message.get("chat_id", "")

        # 限流检查
        if not check_rate_limit(user_id):
            asyncio.create_task(
                send_text_message(chat_id, "操作频繁，请稍候再试（限 10 次/分钟）")
            )
            return JSONResponse(content={"code": 0})

        # 意图路由
        if text.startswith("搜索:") or text.startswith("搜索：") or text.startswith("查找"):
            asyncio.create_task(handle_similarity_search(user_id, chat_id, text))
        else:
            asyncio.create_task(handle_log_parse(user_id, chat_id, text))

        return JSONResponse(content={"code": 0})

    except Exception:
        return JSONResponse(content={"code": 0})


@router.get("/event")
async def feishu_event_get():
    """GET 请求（cpolar 健康检查等）"""
    return {"status": "feishu event endpoint ready"}
