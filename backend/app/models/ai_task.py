"""
AI 任务表 - 记录 Agent 调用历史
"""
from datetime import datetime

from sqlalchemy import Column, String, Integer, SmallInteger, Text, DateTime

from app.models.base import Base, TimestampMixin


class AITask(Base, TimestampMixin):
    __tablename__ = "ai_task"

    ticket_id = Column(Integer, nullable=True, comment="关联工单ID")
    task_type = Column(
        String(50),
        nullable=False,
        comment="任务类型: log_parse/ticket_generate/fault_analyze/knowledge_extract",
    )
    status = Column(
        SmallInteger,
        default=1,
        nullable=False,
        comment="状态: 1=待处理 2=处理中 3=已完成 4=失败",
    )
    prompt = Column(Text, nullable=True, comment="发送给 LLM 的 Prompt")
    response = Column(Text, nullable=True, comment="LLM 返回的原始响应")
    result_json = Column(Text, nullable=True, comment="结构化结果 JSON")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    finish_time = Column(DateTime, nullable=True, comment="完成时间")
    duration = Column(Integer, nullable=True, comment="耗时（秒）")
    error_message = Column(Text, nullable=True, comment="错误信息")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "task_type": self.task_type,
            "status": self.status,
            "result_json": self.result_json,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "finish_time": self.finish_time.isoformat() if self.finish_time else None,
            "duration": self.duration,
            "error_message": self.error_message,
        }
