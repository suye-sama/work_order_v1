"""
LLM 工厂 — 统一管理多种大模型，通过环境变量切换
支持：OpenAI GPT / 阿里百炼 Qwen / Ollama 本地模型
"""
import os
from langchain_openai import ChatOpenAI


def get_llm(temperature: float = 0.3, model: str | None = None):
    """
    获取 LLM 实例。

    通过环境变量配置：
      LLM_PROVIDER     = openai | qwen | ollama  (默认: openai)
      OPENAI_API_KEY   = API 密钥
      OPENAI_BASE_URL  = API 地址（Qwen: https://dashscope.aliyuncs.com/compatible-mode/v1）
      LLM_MODEL        = 模型名称（默认: gpt-4o-mini）
    """
    provider = os.getenv("LLM_PROVIDER", "openai")
    api_key = os.getenv("OPENAI_API_KEY", "sk-placeholder")
    base_url = os.getenv("OPENAI_BASE_URL", None)

    # 模型选择
    if model is None:
        default_models = {
            "openai": "gpt-4o-mini",
            "qwen": "qwen-plus",
            "ollama": "qwen2.5:7b",
        }
        model = os.getenv("LLM_MODEL", default_models.get(provider, "gpt-4o-mini"))

    # 特殊处理：Ollama 不需要 api_key
    if provider == "ollama":
        api_key = "ollama"  # Ollama 不需要真实 key
        if base_url is None:
            base_url = "http://localhost:11434/v1"

    # 特殊处理：Qwen 百炼
    if provider == "qwen" and base_url is None:
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    kwargs = {
        "model": model,
        "api_key": api_key,
        "temperature": temperature,
        "request_timeout": 60,  # 60 秒超时，避免长时间卡住
        "max_retries": 2,
    }
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs)


def get_llm_info() -> dict:
    """获取当前 LLM 配置信息（用于调试）"""
    return {
        "provider": os.getenv("LLM_PROVIDER", "openai"),
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "has_api_key": bool(os.getenv("OPENAI_API_KEY")),
    }
