"""
统一响应格式
"""
from typing import Any, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一 API 响应"""

    code: int = 200
    message: str = "success"
    data: Any = None


class PaginatedData(BaseModel):
    """分页数据"""

    total: int
    page: int
    page_size: int
    records: list


class ApiError(BaseModel):
    """错误响应"""

    code: int
    message: str
    detail: Optional[str] = None
