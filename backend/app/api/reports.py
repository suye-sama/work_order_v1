"""
报表 API：统计、趋势、导出
"""
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from openpyxl import Workbook

from app.database import get_db
from app.schemas.common import ApiResponse
from app.middleware.auth import get_current_user
from app.services import report_service

router = APIRouter(prefix="/api/v1/reports", tags=["报表"])


@router.get("/summary", response_model=ApiResponse)
def get_summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """工单概览统计"""
    data = report_service.ticket_summary(db)
    return ApiResponse(code=200, message="success", data=data)


@router.get("/categories", response_model=ApiResponse)
def get_categories(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """问题分类统计"""
    data = report_service.category_stats(db)
    return ApiResponse(code=200, message="success", data=data)


@router.get("/workload", response_model=ApiResponse)
def get_workload(
    period: str = Query("week", description="week/month/day"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """工作量统计"""
    data = report_service.workload_stats(db, period)
    return ApiResponse(code=200, message="success", data=data)


@router.get("/trend", response_model=ApiResponse)
def get_trend(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """每日趋势"""
    data = report_service.trend_stats(db, days)
    return ApiResponse(code=200, message="success", data=data)


@router.get("/export", response_model=ApiResponse)
def export_excel(
    status: int | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """导出工单 Excel"""
    tickets = report_service.export_tickets(db, status)

    wb = Workbook()
    ws = wb.active
    ws.title = "工单数据"

    # 表头
    headers = ["编号", "标题", "客户", "分类", "优先级", "状态", "处理人",
               "故障现象", "根因分析", "解决方案", "创建时间", "完成时间"]
    ws.append(headers)

    status_names = {1: "新建", 2: "处理中", 3: "待确认", 4: "已完成", 5: "已归档"}
    priority_names = {1: "高", 2: "中", 3: "低"}

    for t in tickets:
        ws.append([
            t.get("ticket_no"),
            t.get("title"),
            t.get("customer_name") or "",
            t.get("category") or "",
            priority_names.get(t.get("priority", 2), ""),
            status_names.get(t.get("status", 1), ""),
            t.get("handler_name") or "",
            t.get("fault_summary") or "",
            t.get("root_cause") or "",
            t.get("solution") or "",
            t.get("create_time") or "",
            t.get("finish_time") or "",
        ])

    # 调整列宽
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 18

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    from datetime import datetime as dt
    from urllib.parse import quote
    filename = f"tickets_export_{dt.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded_filename = quote(filename)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
