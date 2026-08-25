"""
工单时间线表
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class TicketTimeline(Base, TimestampMixin):
    __tablename__ = "ticket_timeline"

    ticket_id = Column(
        Integer,
        ForeignKey("ticket.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="工单ID",
    )
    node_time = Column(
        DateTime, default=datetime.now, nullable=False, comment="节点时间"
    )
    node_type = Column(String(50), nullable=False, comment="节点类型: 创建/受理/日志/命令/Agent/完成等")
    title = Column(String(200), nullable=False, comment="节点标题")
    content = Column(Text, nullable=True, comment="节点内容")
    operator = Column(String(50), nullable=True, comment="操作人")
    ai_generated = Column(Boolean, default=False, comment="是否AI生成")

    # 关联
    ticket = relationship("Ticket", back_populates="timeline")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "node_time": self.node_time.isoformat() if self.node_time else None,
            "node_type": self.node_type,
            "title": self.title,
            "content": self.content,
            "operator": self.operator,
            "ai_generated": self.ai_generated,
        }
