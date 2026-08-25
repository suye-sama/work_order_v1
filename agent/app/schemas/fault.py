"""
故障分析 Schema
"""
from typing import Optional
from pydantic import BaseModel, Field


class FaultAnalysisInput(BaseModel):
    """故障分析请求"""

    ticket_id: Optional[int] = Field(None)
    title: str = Field(..., description="工单标题")
    fault_phenomenon: dict = Field(default_factory=dict)
    root_cause: dict = Field(default_factory=dict)
    solution: dict = Field(default_factory=dict)
    category: str = Field("", description="问题分类")
    customer_info: str = Field("", description="客户环境")


class SimilarCase(BaseModel):
    """相似案例"""

    ticket_id: Optional[int]
    title: str
    similarity: float
    root_cause: Optional[str] = None
    solution: Optional[str] = None


class FaultAnalysisOutput(BaseModel):
    """故障分析输出"""

    is_known_issue: bool = Field(False, description="是否为已知问题")
    similar_cases: list = Field(default_factory=list, description="相似案例")
    fault_category: str = Field("", description="故障分类")
    severity: str = Field("中", description="严重程度: 高/中/低")
    recurrence_risk: str = Field("中", description="复发风险: 高/中/低")
    affected_versions: list[str] = Field(default_factory=list, description="影响版本")
    comparison: str = Field("", description="与历史案例的对比分析")
    risk_detail: str = Field("", description="风险详细分析")
    prevention: str = Field("", description="预防措施")
    long_term_advice: str = Field("", description="长期优化建议")
    error: Optional[str] = Field(None)