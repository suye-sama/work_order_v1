"""
报表服务：统计、工作量、Excel 导出
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.ticket import Ticket


def ticket_summary(db: Session) -> dict:
    """工单状态概览"""
    total = db.query(func.count(Ticket.id)).filter(Ticket.deleted == False).scalar() or 0
    by_status = {}
    for status in range(1, 6):
        cnt = db.query(func.count(Ticket.id)).filter(
            Ticket.deleted == False, Ticket.status == status
        ).scalar() or 0
        by_status[status] = cnt

    by_priority = {}
    for p in range(1, 4):
        cnt = db.query(func.count(Ticket.id)).filter(
            Ticket.deleted == False, Ticket.priority == p
        ).scalar() or 0
        by_priority[p] = cnt

    # 超时工单（超过7天未完成，状态仍为1或2）
    week_ago = datetime.now() - timedelta(days=7)
    overdue = db.query(func.count(Ticket.id)).filter(
        Ticket.deleted == False,
        Ticket.status.in_([1, 2]),
        Ticket.create_time < week_ago,
    ).scalar() or 0

    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue": overdue,
    }


def category_stats(db: Session) -> list[dict]:
    """问题分类统计"""
    rows = (
        db.query(Ticket.category, func.count(Ticket.id))
        .filter(Ticket.deleted == False, Ticket.category.isnot(None))
        .group_by(Ticket.category)
        .all()
    )
    return [{"category": r[0] or "未分类", "count": r[1]} for r in rows]


def workload_stats(db: Session, period: str = "week") -> list[dict]:
    """工作量统计（按处理人）"""
    now = datetime.now()
    if period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        start = now - timedelta(days=1)

    # 按处理人分组
    rows = (
        db.query(
            Ticket.handler_id,
            func.count(Ticket.id),
            func.avg(Ticket.duration),
        )
        .filter(
            Ticket.deleted == False,
            Ticket.finish_time >= start,
            Ticket.status.in_([4, 5]),
        )
        .group_by(Ticket.handler_id)
        .all()
    )

    result = []
    for handler_id, cnt, avg_dur in rows:
        # 获取处理人名字
        from app.models.user import User
        user = db.query(User).filter(User.id == handler_id).first()
        result.append({
            "handler_id": handler_id,
            "handler_name": user.real_name if user else f"用户{handler_id}",
            "completed": cnt,
            "avg_duration_minutes": round(avg_dur) if avg_dur else 0,
        })
    result.sort(key=lambda x: x["completed"], reverse=True)
    return result


def trend_stats(db: Session, days: int = 7) -> list[dict]:
    """每日趋势（最近 N 天）"""
    now = datetime.now()
    result = []
    for i in range(days, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0)
        day_end = day.replace(hour=23, minute=59, second=59)

        created = db.query(func.count(Ticket.id)).filter(
            Ticket.deleted == False,
            Ticket.create_time.between(day_start, day_end),
        ).scalar() or 0

        completed = db.query(func.count(Ticket.id)).filter(
            Ticket.deleted == False,
            Ticket.finish_time.between(day_start, day_end),
        ).scalar() or 0

        result.append({
            "date": day.strftime("%m-%d"),
            "created": created,
            "completed": completed,
        })
    return result


def export_tickets(db: Session, status: int | None = None) -> list[dict]:
    """导出工单数据"""
    q = db.query(Ticket).filter(Ticket.deleted == False)
    if status:
        q = q.filter(Ticket.status == status)

    tickets = q.order_by(Ticket.create_time.desc()).all()
    return [t.to_dict() for t in tickets]
