"""
飞书 SDK 封装 — Tenant Token 缓存 + 消息发送

注意：本地开发环境无 Redis，使用内存字典做缓存。
"""
import asyncio
import json
import os
import time

import httpx

# ==================== 配置 ====================

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"

# ==================== 内存缓存（无 Redis 时的降级方案） ====================

_token_cache: dict = {}
_token_lock = asyncio.Lock()


async def get_tenant_access_token() -> str:
    """
    获取并缓存 tenant_access_token（内存缓存，TTL=7000 秒，
    使用异步锁防止并发请求重复获取）
    """
    global _token_cache
    async with _token_lock:
        now = time.time()
        if _token_cache and _token_cache.get("expires_at", 0) > now + 60:
            return _token_cache["token"]

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{FEISHU_BASE_URL}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": FEISHU_APP_ID,
                    "app_secret": FEISHU_APP_SECRET,
                },
            )
            data = resp.json()

        if data.get("code") != 0:
            raise Exception(f"获取 tenant_access_token 失败: {data}")

        _token_cache = {
            "token": data["tenant_access_token"],
            "expires_at": now + data.get("expire", 7200) - 200,
        }
        return _token_cache["token"]


# ==================== 消息发送 ====================


async def _send_message(receive_id: str, msg_type: str, content: str) -> dict:
    """发送飞书消息（底层通用方法）"""
    token = await get_tenant_access_token()

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{FEISHU_BASE_URL}/im/v1/messages",
            params={"receive_id_type": "chat_id"},
            json={
                "receive_id": receive_id,
                "msg_type": msg_type,
                "content": content,
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        result = resp.json()
        if result.get("code") != 0:
            raise Exception(f"发送消息失败: {result.get('msg', result)}")
        return result


async def send_text_message(chat_id: str, text: str) -> dict:
    """发送飞书文本消息"""
    content = json.dumps({"text": text})
    result = await _send_message(chat_id, "text", content)
    if result.get("code") == 0:
        return {"message_id": result.get("data", {}).get("message_id", "")}
    return {"error": result.get("msg", "发送失败")}


async def send_card_message(chat_id: str, card_json: dict) -> dict:
    """发送飞书交互卡片消息"""
    content = json.dumps(card_json)
    result = await _send_message(chat_id, "interactive", content)
    if result.get("code") == 0:
        return {"message_id": result.get("data", {}).get("message_id", "")}
    return {"error": result.get("msg", "发送失败")}
