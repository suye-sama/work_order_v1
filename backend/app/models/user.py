"""
用户表
"""
from sqlalchemy import Column, String, Integer, SmallInteger

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "sys_user"

    username = Column(String(100), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(100), nullable=True, comment="真实姓名")
    phone = Column(String(50), nullable=True, comment="手机号")
    email = Column(String(100), nullable=True, comment="邮箱")
    role = Column(
        SmallInteger,
        default=3,
        nullable=False,
        comment="角色: 1=超级管理员 2=运维管理员 3=售后工程师 4=查看人员",
    )
    status = Column(
        SmallInteger, default=1, nullable=False, comment="状态: 1=启用 0=禁用"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "real_name": self.real_name,
            "phone": self.phone,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "create_time": self.create_time.isoformat() if self.create_time else None,
        }
