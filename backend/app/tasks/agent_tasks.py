"""
飞书异步后台任务 — 解决飞书 3 秒超时限制

收到飞书回调后立即返回 {"code": 0}，业务逻辑通过 asyncio.create_task 异步执行。
执行完毕后通过飞书 Send Message API 主动推送结果。
"""
from app.integrations.feishu_client import send_card_message, send_text_message
from app.integrations.feishu_cards import (
    build_log_parse_card,
    build_search_result_card,
    build_error_card,
)
from app.services.agent_service import _call_agent


async def handle_log_parse(user_id: str, chat_id: str, log_text: str) -> None:
    """
    场景一：日志解析

    1. 发送「处理中」提示
    2. 调用 Flask Agent 日志解析接口
    3. 构建卡片并发送
    """
    try:
        await send_text_message(chat_id, "⏳ 正在分析日志，请稍候...")

        # 日志文本截断保护（保留最后 3000 字符）
        if len(log_text) > 3000:
            log_text = log_text[-3000:]
            await send_text_message(chat_id, "⚠️ 日志较长，已截取最后 3000 字符进行分析")

        result = await _call_agent(
            "/agent/log/parse",
            {"log_text": log_text, "user_id": user_id},
            timeout=60,
        )

        if result.get("error") and not result.get("timeline"):
            card = build_error_card(f"日志解析失败：{result['error']}")
        else:
            card = build_log_parse_card(result)

        await send_card_message(chat_id, card)

    except Exception as e:
        await send_text_message(chat_id, f"分析服务暂时不可用，请稍后重试。")


async def handle_similarity_search(user_id: str, chat_id: str, query_text: str) -> None:
    """
    场景二：相似检索

    1. 去掉「搜索」前缀，提取关键词
    2. 调用 Flask Agent 相似检索接口
    3. 构建卡片并发送
    """
    try:
        # 去掉前缀，提取关键词
        keyword = query_text
        for prefix in ["搜索：", "搜索:", "查找：", "查找:", "查找", "搜索"]:
            if keyword.startswith(prefix):
                keyword = keyword[len(prefix):].strip()
                break

        if not keyword:
            await send_text_message(chat_id, "请在「搜索」后输入关键词，如：搜索：Nginx 502 错误")
            return

        result = await _call_agent(
            "/agent/search",
            {"query": keyword, "top_k": 5},
            timeout=15,
        )

        # 适配不同返回格式
        items = result if isinstance(result, list) else result.get("items", result.get("results", []))

        if not items:
            card = build_error_card(f"未找到与「{keyword}」相关的历史案例")
        else:
            card = build_search_result_card(items, keyword)

        await send_card_message(chat_id, card)

    except Exception as e:
        await send_text_message(chat_id, "检索服务暂时不可用，请稍后重试。")
