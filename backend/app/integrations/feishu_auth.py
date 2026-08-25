"""
飞书事件解密与签名验证工具

当前调试阶段未开启加密，本模块作为预留骨架。
正式上线开启加密后，优先使用 lark_oapi 提供的官方解密方法：
    from lark_oapi.event import decrypt_event
"""
import os
from typing import Optional


def get_encrypt_key() -> Optional[str]:
    """获取飞书加密 Key（为空表示未开启加密）"""
    key = os.getenv("FEISHU_ENCRYPT_KEY", "").strip()
    return key if key else None
