"""
客户接口：CRUD
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services import customer_service
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/customers", tags=["客户"])


@router.post("", response_model=ApiResponse)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """新增客户"""
    customer = customer_service.create_customer(db, data, user.id)
    return ApiResponse(
        code=200,
        message="客户创建成功",
        data=customer.to_dict(),
    )


@router.get("", response_model=ApiResponse)
def list_customers(
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询客户列表"""
    result = customer_service.query_customers(db, keyword, page, page_size)
    return ApiResponse(code=200, message="success", data=result)


@router.get("/{customer_id}", response_model=ApiResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取客户详情"""
    customer = customer_service.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return ApiResponse(code=200, message="success", data=customer.to_dict())


@router.put("/{customer_id}", response_model=ApiResponse)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """更新客户"""
    customer = customer_service.update_customer(db, customer_id, data, user.id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return ApiResponse(code=200, message="更新成功", data=customer.to_dict())


@router.delete("/{customer_id}", response_model=ApiResponse)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """删除客户"""
    ok = customer_service.delete_customer(db, customer_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="客户不存在")
    return ApiResponse(code=200, message="删除成功")
