"""
工单生成 Schema — 标准化工单 JSON 结构
"""
from typing import Optional
from pydantic import BaseModel, Field


class FaultPhenomenon(BaseModel):
    """Stage 1 输出：故障现象"""

    phenomenon: str = Field(..., description="故障现象描述")
    impact_scope: str = Field(..., description="影响范围")
    occurrence_time: Optional[str] = Field(None, description="故障发生时间")


class TroubleshootingStep(BaseModel):
    """Stage 2 输出：排查步骤"""

    step: int
    action: str = Field(..., description="排查操作")
    finding: str = Field(..., description="该操作发现的结果")


class RootCause(BaseModel):
    """Stage 3 输出：根因分析"""

    root_cause: str = Field(..., description="根本原因一句话概述")
    detail: str = Field(..., description="详细分析")
    category: Optional[str] = Field(None, description="故障分类")


class Solution(BaseModel):
    """Stage 4 输出：解决方案"""

    solution: str = Field(..., description="解决方案概述")
    steps: list[str] = Field(default_factory=list, description="修复步骤")
    suggestion: Optional[str] = Field(None, description="后续建议")


class TicketSummary(BaseModel):
    """Stage 5 输出：工单摘要"""

    summary: str = Field(..., description="工单摘要（100-200字）")
    tags: list[str] = Field(default_factory=list, description="标签")
    estimated_duration_minutes: Optional[int] = Field(None, description="估计处理时长")


class GeneratedTicket(BaseModel):
    """最终输出：完整工单"""

    fault_phenomenon: FaultPhenomenon
    troubleshooting: list[TroubleshootingStep]
    root_cause: RootCause
    solution: Solution
    summary_info: TicketSummary


# ---- API 请求/响应 ----


class TicketGenerateInput(BaseModel):
    """工单生成请求"""

    ticket_id: Optional[int] = Field(None, description="工单 ID")
    title: str = Field(..., description="工单标题")
    customer_info: Optional[str] = Field(None, description="客户环境信息")
    timeline_json: Optional[list] = Field(None, description="时间线数据（来自日志解析）")
    raw_log: Optional[str] = Field(None, description="原始操作日志")
    engineer_notes: Optional[str] = Field(None, description="工程师备注")
    description: Optional[str] = Field(None, description="原始问题描述")


class TicketGenerateOutput(BaseModel):
    """工单生成响应"""

    success: bool = False
    ticket_id: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: int = 0
