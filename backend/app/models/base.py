"""
模型基类 - 公共字段 Mixin
"""
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, Boolean, Text

from app.database import Base


class TimestampMixin:
    """时间戳公共字段（SQLite 使用 Integer 主键，切 PostgreSQL 后改为 BigInt）"""

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    create_time = Column(
        DateTime, default=datetime.now, nullable=False, comment="创建时间"
    )
    update_time = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
        comment="更新时间",
    )
    create_by = Column(Integer, nullable=True, comment="创建人ID")
    update_by = Column(Integer, nullable=True, comment="修改人ID")
    deleted = Column(Boolean, default=False, nullable=False, comment="逻辑删除")
    remark = Column(Text, nullable=True, comment="备注")
