"""
应用配置
"""
import os
from pathlib import Path


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 数据库配置 - 本地学习使用 SQLite，后续改为 PostgreSQL 连接串即可
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'data' / 'work_order.db'}",
)

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = int(os.getenv("JWT_EXPIRE", "7200"))  # 2小时

# Agent 服务地址
AGENT_URL = os.getenv("AGENT_URL", "http://127.0.0.1:5000")

# 分页默认值
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
