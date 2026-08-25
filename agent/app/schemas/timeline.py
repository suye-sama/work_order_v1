"""
时间线数据结构 — 日志解析 Agent 的输出 Schema
"""
from typing import Optional
from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    """单条时间线条目"""

    step: int = Field(..., description="步骤序号")
    time: Optional[str] = Field(None, description="操作时间 (ISO格式)")
    phase: str = Field(..., description="阶段名称: 环境检查/日志分析/故障定位/修复操作/验证测试")
    operation: str = Field(..., description="操作描述")
    command: Optional[str] = Field(None, description="执行的命令")
    summary: str = Field(..., description="一句话摘要（中文）")
    result: Optional[str] = Field(None, description="操作结果")


class LogParseInput(BaseModel):
    """日志解析请求"""

    log_text: str = Field(..., description="原始终端日志文本")
    ticket_id: Optional[int] = Field(None, description="关联工单ID")


class LogParseOutput(BaseModel):
    """日志解析响应"""

    timeline: list[TimelineEntry] = Field(default_factory=list, description="生成的时间线")
    phase_count: int = Field(0, description="识别的阶段数")
    total_steps: int = Field(0, description="总步骤数")
    raw_log_length: int = Field(0, description="原始日志字符数")
    error: Optional[str] = Field(None, description="错误信息（如有）")
