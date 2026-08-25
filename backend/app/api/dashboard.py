"""
工作台接口：待办、进行中、已完成
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.models.ticket import Ticket
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["工作台"])


@router.get("/todo", response_model=ApiResponse)
def get_todo(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """我的待办 — 状态为新建(1)或已指派给当前用户的工单"""
    q = db.query(Ticket).filter(
        Ticket.deleted == False,  # noqa: E712
        Ticket.status == 1,  # 新建/待处理
    )
    total = q.count()
    records = (
        q.order_by(Ticket.priority.asc(), Ticket.create_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ApiResponse(
        code=200,
        message="success",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "records": [r.to_dict() for r in records],
        },
    )


@router.get("/doing", response_model=ApiResponse)
def get_doing(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """我的进行中 — 当前用户正在处理的工单"""
    q = db.query(Ticket).filter(
        Ticket.deleted == False,  # noqa: E712
        Ticket.handler_id == user.id,
        Ticket.status.in_([2, 3]),  # 处理中 或 待确认
    )
    total = q.count()
    records = (
        q.order_by(Ticket.update_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ApiResponse(
        code=200,
        message="success",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "records": [r.to_dict() for r in records],
        },
    )


@router.get("/completed", response_model=ApiResponse)
def get_completed(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """本周已完成 — 当前用户本周完成的工单"""
    from datetime import datetime, timedelta

    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())

    q = db.query(Ticket).filter(
        Ticket.deleted == False,  # noqa: E712
        Ticket.handler_id == user.id,
        Ticket.status.in_([4, 5]),  # 已完成 或 已归档
        Ticket.finish_time >= week_start,
    )
    total = q.count()
    records = (
        q.order_by(Ticket.finish_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ApiResponse(
        code=200,
        message="success",
        data={
            "total": total,
            "page": page,
            "page_size": page_size,
            "records": [r.to_dict() for r in records],
        },
    )


@router.post("/quick-ticket", response_model=ApiResponse)
def quick_create_ticket(
    title: str = Query(..., description="工单标题"),
    description: str = Query("", description="问题描述"),
    customer_id: int | None = Query(None, description="客户ID"),
    priority: int = Query(2, ge=1, le=3, description="优先级"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """快速创建工单（仅填写最核心字段）"""
    from app.services.ticket_service import create_ticket, generate_ticket_no
    from app.schemas.ticket import TicketCreate

    data = TicketCreate(
        title=title,
        customer_id=customer_id,
        priority=priority,
        description=description,
    )
    ticket = create_ticket(db, data, user.id)
    return ApiResponse(
        code=200,
        message="快速创建成功",
        data=ticket.to_dict(include_timeline=True),
    )
