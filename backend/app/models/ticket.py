"""
工单主表
"""
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    SmallInteger,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Ticket(Base, TimestampMixin):
    __tablename__ = "ticket"

    # ---- 基本信息 ----
    ticket_no = Column(
        String(32), unique=True, nullable=False, index=True, comment="工单编号"
    )
    title = Column(String(200), nullable=False, comment="工单标题")
    customer_id = Column(
        Integer, ForeignKey("customer.id"), nullable=True, comment="客户ID"
    )
    contact_id = Column(Integer, nullable=True, comment="联系人ID")
    category = Column(String(50), nullable=True, comment="问题分类")
    priority = Column(
        SmallInteger, default=2, nullable=False, comment="优先级: 1=高 2=中 3=低"
    )
    status = Column(
        SmallInteger,
        default=1,
        nullable=False,
        comment="状态: 1=新建 2=处理中 3=待确认 4=已完成 5=已归档",
    )
    source = Column(
        String(30),
        default="手动录入",
        nullable=True,
        comment="来源: 电话/微信/钉钉/手动录入",
    )

    # ---- 故障信息 ----
    description = Column(Text, nullable=True, comment="原始问题描述")
    fault_summary = Column(Text, nullable=True, comment="故障现象（Agent填充）")
    troubleshooting = Column(Text, nullable=True, comment="排查过程（Agent填充）")
    solution = Column(Text, nullable=True, comment="解决方案（Agent填充）")
    root_cause = Column(Text, nullable=True, comment="根因分析（Agent填充）")
    ai_summary = Column(Text, nullable=True, comment="AI生成摘要")
    raw_log = Column(Text, nullable=True, comment="原始操作日志")

    # ---- 处理信息 ----
    handler_id = Column(
        Integer, ForeignKey("sys_user.id"), nullable=True, comment="处理人ID"
    )
    start_time = Column(DateTime, nullable=True, comment="开始处理时间")
    finish_time = Column(DateTime, nullable=True, comment="完成时间")
    duration = Column(Integer, nullable=True, comment="处理时长（分钟）")

    # ---- 扩展与二期预留 ----
    knowledge_id = Column(Integer, nullable=True, comment="关联知识条目ID（二期）")
    extra = Column(JSON, nullable=True, comment="扩展字段（JSONB）")

    # 关联
    customer = relationship("Customer", lazy="select")
    handler = relationship("User", lazy="select")
    timeline = relationship(
        "TicketTimeline",
        back_populates="ticket",
        lazy="select",
        order_by="TicketTimeline.node_time",
    )

    def to_dict(self, include_timeline=False):
        data = {
            "id": self.id,
            "ticket_no": self.ticket_no,
            "title": self.title,
            "customer_id": self.customer_id,
            "customer_name": self.customer.name if self.customer else None,
            "contact_id": self.contact_id,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "source": self.source,
            "description": self.description,
            "fault_summary": self.fault_summary,
            "troubleshooting": self.troubleshooting,
            "solution": self.solution,
            "root_cause": self.root_cause,
            "ai_summary": self.ai_summary,
            "raw_log": self.raw_log,
            "handler_id": self.handler_id,
            "handler_name": self.handler.real_name if self.handler else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "finish_time": self.finish_time.isoformat() if self.finish_time else None,
            "duration": self.duration,
            "knowledge_id": self.knowledge_id,
            "extra": self.extra,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
        }
        if include_timeline:
            data["timeline"] = [t.to_dict() for t in (self.timeline or [])]
        return data
