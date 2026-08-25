"""
飞书卡片模板构建器

卡片类型：
  1. 日志解析结果卡片 — 展示 AI 分析后的工单草稿
  2. 相似检索结果卡片 — 展示 Top-5 历史案例列表
"""


def build_log_parse_card(result: dict) -> dict:
    """
    构建「日志解析结果」飞书卡片

    卡片内容：
      - 标题：🔍 日志分析结果
      - 故障现象摘要
      - 排查步骤（1. 2. 3. 编号）
      - 建议根因
      - 底部按钮：📋 一键创建工单
    """
    timeline = result.get("timeline", [])
    phase_count = result.get("phase_count", 0)
    total_steps = result.get("total_steps", 0)

    # 从时间线中提取摘要信息
    phases: list[str] = []
    steps: list[str] = []
    for entry in timeline[:10]:
        phase = entry.get("phase", "")
        if phase and phase not in phases:
            phases.append(phase)
        operation = entry.get("operation", "")
        command = entry.get("command", "")
        result_text = entry.get("result", "")
        if operation or command:
            steps.append(f"`{command}` → {operation or result_text}")

    phase_text = " → ".join(phases) if phases else "暂无"
    steps_text = "\n".join(steps) if steps else "暂无详细步骤"

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🔍 日志分析结果"},
            "template": "blue",
        },
        "elements": [
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**故障阶段**\n{phase_text}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**总步数**\n{total_steps} 步 / {phase_count} 阶段"}},
                ],
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**📋 排查步骤**\n{steps_text}"},
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**💡 分析耗时：** {result.get('duration_ms', 0) / 1000:.1f} 秒"},
            },
        ],
    }

    # 如果 Agent 返回了 error，添加提示
    if result.get("error"):
        card["elements"].insert(0, {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"⚠️ 解析警告：{result['error']}"},
        })

    return card


def build_search_result_card(results: list[dict], keyword: str) -> dict:
    """
    构建「相似检索结果」飞书卡片

    卡片内容：
      - 标题：📚 相关历史案例
      - Top-5 列表，每条显示标题和匹配度
      - 简要原因
    """
    # 生成案例列表
    case_elements: list[dict] = []

    for i, item in enumerate(results[:5]):
        title = item.get("title", "未知案例")
        similarity = item.get("similarity", 0)
        summary = item.get("summary", "")
        tags = item.get("tags", [])

        percent = f"{similarity * 100:.0f}%" if isinstance(similarity, (int, float)) and similarity <= 1 else f"{similarity}%"
        tag_text = f"  `{' / '.join(tags)}`" if tags else ""

        case_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**{i + 1}. {title}**  `{percent}`{tag_text}\n"
                    f"{summary or '暂无摘要'}"
                ),
            },
        })
        if i < min(len(results), 5) - 1:
            case_elements.append({"tag": "hr"})

    if not case_elements:
        case_elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "😕 未找到相关案例，请尝试其他关键词"},
        })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "📚 相关历史案例"},
            "template": "purple",
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"搜索关键词：**{keyword}**，共找到 {len(results)} 条结果"},
            },
            {"tag": "hr"},
            *case_elements,
        ],
    }

    return card


def build_error_card(error_msg: str) -> dict:
    """
    构建错误提示卡片
    """
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "⚠️ 服务提示"},
            "template": "red",
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": error_msg},
            },
        ],
    }


