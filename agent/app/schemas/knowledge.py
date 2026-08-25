"""
知识条目 Schema
"""
from typing import Optional
from pydantic import BaseModel, Field


class KnowledgeTriplet(BaseModel):
    """故障知识三元组"""

    phenomenon: str = Field(..., description="故障现象")
    root_cause: str = Field(..., description="根因")
    solution: str = Field(..., description="解决方案")


class KnowledgeEntry(BaseModel):
    """标准化知识条目"""

    title: str = Field(..., description="知识标题")
    category: str = Field(..., description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")
    summary: str = Field(..., description="AI 摘要")
    steps: list[str] = Field(default_factory=list, description="解决步骤")
    applicable_versions: Optional[str] = Field(None, description="适用产品版本")
    difficulty: Optional[str] = Field(None, description="难度: 简单/中等/复杂")
    source_ticket_id: Optional[int] = Field(None, description="来源工单ID")


class KnowledgeExtractInput(BaseModel):
    """知识提取请求"""

    ticket_id: Optional[int] = Field(None)
    title: str = Field(..., description="工单标题")
    fault_phenomenon: dict = Field(default_factory=dict, description="故障现象")
    root_cause: dict = Field(default_factory=dict, description="根因分析")
    solution: dict = Field(default_factory=dict, description="解决方案")
    summary_info: dict = Field(default_factory=dict, description="工单摘要")
    customer_info: Optional[str] = Field(None)


class SearchInput(BaseModel):
    """相似工单检索请求"""

    query: str = Field(..., description="查询文本（故障描述/关键词）")
    top_k: int = Field(5, ge=1, le=20, description="返回数量")


class SearchResult(BaseModel):
    """检索结果条目"""

    ticket_id: Optional[int]
    title: str
    summary: str
    tags: list[str]
    similarity: float
