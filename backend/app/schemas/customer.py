"""
客户相关 Schema
"""
from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    """创建客户"""

    name: str = Field(..., min_length=1, max_length=200, description="客户名称")
    region: str | None = Field(None, description="所属地区")
    product_version: str | None = Field(None, description="产品版本")
    deploy_type: str | None = Field(None, description="部署方式")
    os: str | None = Field(None, description="操作系统")
    db_type: str | None = Field(None, description="数据库类型")
    description: str | None = Field(None, description="描述")


class CustomerUpdate(BaseModel):
    """更新客户"""

    name: str | None = Field(None, max_length=200)
    region: str | None = None
    product_version: str | None = None
    deploy_type: str | None = None
    os: str | None = None
    db_type: str | None = None
    description: str | None = None
