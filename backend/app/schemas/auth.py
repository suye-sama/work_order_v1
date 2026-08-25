"""
认证相关 Schema
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """登录请求"""

    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""

    token: str
    token_type: str = "Bearer"
    expire_seconds: int
    user: dict


class UserInfo(BaseModel):
    """用户信息"""

    id: int
    username: str
    real_name: str | None
    role: int
    role_name: str

    @staticmethod
    def role_to_name(role: int) -> str:
        mapping = {1: "超级管理员", 2: "运维管理员", 3: "售后工程师", 4: "查看人员"}
        return mapping.get(role, "未知")
