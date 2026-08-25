"""
工单服务：CRUD + 状态机流转
"""
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.timeline import TicketTimeline
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketQuery

# 工单编号前缀
TICKET_NO_PREFIX = "TK"

# 状态流转规则：允许从当前状态流转到的目标状态
STATUS_TRANSITIONS = {
    1: [2],           # 新建 → 处理中
    2: [3, 4],        # 处理中 → 待确认 / 已完成
    3: [4],           # 待确认 → 已完成
    4: [5],           # 已完成 → 已归档
    5: [],            # 已归档（终态）
}

STATUS_NAMES = {
    1: "新建",
    2: "处理中",
    3: "待确认",
    4: "已完成",
    5: "已归档",
}


def generate_ticket_no(db: Session) -> str:
    """生成工单编号: TK + 日期 + 序号"""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"{TICKET_NO_PREFIX}{today}"
    # 查询今天已有的最大编号
    last = (
        db.query(Ticket)
        .filter(Ticket.ticket_no.like(f"{prefix}%"))
        .order_by(desc(Ticket.ticket_no))
        .first()
    )
    if last and last.ticket_no:
        seq = int(last.ticket_no[-3:]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:03d}"


def create_ticket(db: Session, data: TicketCreate, user_id: int) -> Ticket:
    """创建工单"""
    ticket = Ticket(
        ticket_no=generate_ticket_no(db),
        title=data.title,
        customer_id=data.customer_id,
        contact_id=data.contact_id,
        category=data.category,
        priority=data.priority,
        source=data.source,
        description=data.description,
        raw_log=data.raw_log,
        status=1,  # 新建
        create_by=user_id,
        update_by=user_id,
    )
    db.add(ticket)
    db.flush()  # 先 flush 拿到 ticket.id

    # 添加创建时间线
    _add_timeline(
        db,
        ticket.id,
        "创建",
        f"工单创建成功: {data.title}",
        user_id,
    )

    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket(db: Session, ticket_id: int) -> Ticket | None:
    """获取工单详情（含时间线）"""
    return db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.deleted == False,  # noqa: E712
    ).first()


def query_tickets(db: Session, query: TicketQuery, user_id: int | None = None):
    """查询工单列表（分页+筛选）"""
    q = db.query(Ticket).filter(Ticket.deleted == False)  # noqa: E712

    if query.status:
        q = q.filter(Ticket.status == query.status)
    if query.customer_id:
        q = q.filter(Ticket.customer_id == query.customer_id)
    if query.handler_id:
        q = q.filter(Ticket.handler_id == query.handler_id)
    if query.keyword:
        kw = f"%{query.keyword}%"
        q = q.filter(Ticket.title.like(kw))
    if query.priority:
        q = q.filter(Ticket.priority == query.priority)

    total = q.count()
    records = (
        q.order_by(desc(Ticket.create_time))
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
        .all()
    )

    return {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "records": [r.to_dict() for r in records],
    }


def update_ticket(db: Session, ticket_id: int, data: TicketUpdate, user_id: int) -> Ticket | None:
    """更新工单"""
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ticket, field, value)
    ticket.update_by = user_id
    ticket.update_time = datetime.now()

    db.commit()
    db.refresh(ticket)
    return ticket


def update_status(db: Session, ticket_id: int, new_status: int, user_id: int) -> tuple[bool, str]:
    """工单状态流转（带规则校验）"""
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return False, "工单不存在"

    old_status = ticket.status
    allowed = STATUS_TRANSITIONS.get(old_status, [])

    if new_status not in allowed:
        old_name = STATUS_NAMES.get(old_status, str(old_status))
        new_name = STATUS_NAMES.get(new_status, str(new_status))
        return False, f"不允许从「{old_name}」直接变更为「{new_name}」"

    ticket.status = new_status
    ticket.update_by = user_id
    ticket.update_time = datetime.now()

    # 状态变更时的特殊处理
    if new_status == 2:  # 开始处理
        ticket.handler_id = user_id
        ticket.start_time = datetime.now()
    elif new_status == 4:  # 完成
        ticket.finish_time = datetime.now()
        if ticket.start_time:
            ticket.duration = int(
                (ticket.finish_time - ticket.start_time).total_seconds() / 60
            )

    # 记录时间线
    _add_timeline(
        db,
        ticket_id,
        "状态变更",
        f"工单状态: {STATUS_NAMES.get(old_status)} → {STATUS_NAMES.get(new_status)}",
        user_id,
    )

    db.commit()
    db.refresh(ticket)
    return True, f"状态变更成功: {STATUS_NAMES.get(new_status)}"


def assign_ticket(db: Session, ticket_id: int, handler_id: int, user_id: int) -> tuple[bool, str]:
    """指派工单"""
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return False, "工单不存在"

    ticket.handler_id = handler_id
    ticket.update_by = user_id
    ticket.update_time = datetime.now()

    _add_timeline(db, ticket_id, "指派", f"工单已指派给工程师", user_id)

    db.commit()
    return True, "指派成功"


def delete_ticket(db: Session, ticket_id: int, user_id: int) -> bool:
    """逻辑删除工单"""
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return False
    ticket.deleted = True
    ticket.update_by = user_id
    ticket.update_time = datetime.now()
    db.commit()
    return True


def add_log(db: Session, ticket_id: int, log_text: str, user_id: int) -> Ticket | None:
    """为工单追加原始日志"""
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        return None

    # 追加日志
    if ticket.raw_log:
        ticket.raw_log += "\n" + log_text
    else:
        ticket.raw_log = log_text
    ticket.update_by = user_id
    ticket.update_time = datetime.now()

    _add_timeline(db, ticket_id, "日志", f"工程师追加了操作日志", user_id)

    db.commit()
    db.refresh(ticket)
    return ticket


# ---- 内部函数 ----


def _add_timeline(
    db: Session,
    ticket_id: int,
    node_type: str,
    content: str,
    user_id: int | None = None,
    ai_generated: bool = False,
):
    """添加时间线条目"""
    tl = TicketTimeline(
        ticket_id=ticket_id,
        node_time=datetime.now(),
        node_type=node_type,
        title=content[:200],
        content=content,
        operator=str(user_id) if user_id else None,
        ai_generated=ai_generated,
    )
    db.add(tl)
