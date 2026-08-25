"""
工单相关 Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    """创建工单"""

    title: str = Field(..., min_length=1, max_length=200, description="工单标题")
    customer_id: int | None = Field(None, description="客户ID")
    contact_id: int | None = Field(None, description="联系人ID")
    category: str | None = Field(None, description="问题分类")
    priority: int = Field(2, ge=1, le=3, description="优先级: 1=高 2=中 3=低")
    source: str = Field("手动录入", description="来源")
    description: str | None = Field(None, description="问题描述")
    raw_log: str | None = Field(None, description="原始操作日志")


class TicketUpdate(BaseModel):
    """更新工单"""

    title: str | None = Field(None, max_length=200)
    customer_id: int | None = None
    contact_id: int | None = None
    category: str | None = None
    priority: int | None = Field(None, ge=1, le=3)
    description: str | None = None
    raw_log: str | None = None
    fault_summary: str | None = None
    troubleshooting: str | None = None
    solution: str | None = None
    root_cause: str | None = None
    ai_summary: str | None = None


class TicketStatusUpdate(BaseModel):
    """工单状态变更"""

    status: int = Field(..., ge=1, le=5, description="1=新建 2=处理中 3=待确认 4=已完成 5=已归档")


class TicketAssign(BaseModel):
    """指派工单"""

    handler_id: int = Field(..., description="处理人ID")


class TicketQuery(BaseModel):
    """工单查询参数"""

    status: int | None = None
    customer_id: int | None = None
    handler_id: int | None = None
    keyword: str | None = None
    priority: int | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
