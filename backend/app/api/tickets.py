"""
工单接口：CRUD + 状态流转 + 日志追加 + 报告导出
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ticket import Ticket
from app.models.customer import Customer
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketStatusUpdate,
    TicketAssign,
)
from app.services import ticket_service
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/tickets", tags=["工单"])


@router.post("", response_model=ApiResponse)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """创建工单"""
    ticket = ticket_service.create_ticket(db, data, user.id)
    return ApiResponse(
        code=200,
        message="工单创建成功",
        data=ticket.to_dict(include_timeline=True),
    )


@router.get("", response_model=ApiResponse)
def list_tickets(
    status: int | None = Query(None, description="工单状态"),
    customer_id: int | None = Query(None, description="客户ID"),
    keyword: str | None = Query(None, description="关键词搜索"),
    priority: int | None = Query(None, description="优先级"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询工单列表（分页）"""
    from app.schemas.ticket import TicketQuery

    query = TicketQuery(
        status=status,
        customer_id=customer_id,
        handler_id=None,
        keyword=keyword,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    result = ticket_service.query_tickets(db, query)
    return ApiResponse(code=200, message="success", data=result)


@router.get("/my", response_model=ApiResponse)
def list_my_tickets(
    status: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """查询我的工单"""
    from app.schemas.ticket import TicketQuery

    query = TicketQuery(
        status=status,
        handler_id=user.id,
        page=page,
        page_size=page_size,
    )
    result = ticket_service.query_tickets(db, query)
    return ApiResponse(code=200, message="success", data=result)


@router.get("/{ticket_id}", response_model=ApiResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取工单详情（含时间线）"""
    ticket = ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse(
        code=200,
        message="success",
        data=ticket.to_dict(include_timeline=True),
    )


@router.put("/{ticket_id}", response_model=ApiResponse)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """更新工单"""
    ticket = ticket_service.update_ticket(db, ticket_id, data, user.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse(
        code=200,
        message="更新成功",
        data=ticket.to_dict(),
    )


@router.delete("/{ticket_id}", response_model=ApiResponse)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """删除工单（逻辑删除）"""
    ok = ticket_service.delete_ticket(db, ticket_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse(code=200, message="删除成功")


@router.post("/{ticket_id}/status", response_model=ApiResponse)
def update_status(
    ticket_id: int,
    data: TicketStatusUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """工单状态流转"""
    success, msg = ticket_service.update_status(db, ticket_id, data.status, user.id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ApiResponse(code=200, message=msg)


@router.post("/{ticket_id}/assign", response_model=ApiResponse)
def assign_ticket(
    ticket_id: int,
    data: TicketAssign,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """指派工单"""
    success, msg = ticket_service.assign_ticket(db, ticket_id, data.handler_id, user.id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return ApiResponse(code=200, message=msg)


@router.post("/{ticket_id}/log", response_model=ApiResponse)
def add_log(
    ticket_id: int,
    log_text: str = Query(..., description="操作日志文本"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """为工单追加操作日志（后续 Agent 解析的数据源）"""
    ticket = ticket_service.add_log(db, ticket_id, log_text, user.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse(
        code=200,
        message="日志已追加",
        data=ticket.to_dict(include_timeline=True),
    )


def _extract_key_commands(raw_log: str, max_lines: int = 25) -> str:
    """从原始日志中提取关键命令和输出，去噪声"""
    if not raw_log:
        return "（无操作日志）"

    lines = raw_log.strip().split("\n")
    key_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            key_lines.append("")
            continue
        # 保留命令提示符行、错误行、关键输出行
        is_cmd = stripped.startswith(("#", "$", ">", "["))
        is_error = any(kw in stripped.lower() for kw in ["error", "fail", "active:", "listen", "notafter", "not before"])
        is_important = any(kw in stripped for kw in ["curl", "kill", "restart", "start", "stop", "netstat", "ps ", "df", "du", "mysql", "certbot", "openssl"])
        if is_cmd or is_error or is_important:
            key_lines.append(stripped[:120])  # 截断过长的行

    if len(key_lines) > max_lines:
        key_lines = key_lines[:max_lines]
        key_lines.append("...（完整日志已存档，此处仅保留关键操作）")

    return "\n".join(key_lines)


@router.get("/{ticket_id}/report", response_class=PlainTextResponse)
def ticket_report(
    ticket_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """生成工单 Markdown 售后处理报告"""
    ticket = ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.status not in (3, 4, 5):
        raise HTTPException(status_code=400, detail="仅待确认/已完成/已归档的工单可以生成报告")

    customer = db.query(Customer).filter(Customer.id == ticket.customer_id).first()
    handler = db.query(User).filter(User.id == ticket.handler_id).first()

    cn = customer.name if customer else "未知"
    cv = customer.product_version if customer else "未知"
    cd = f"{customer.deploy_type or '未知'} / {customer.os or '未知'}" if customer else "未知"
    hn = handler.real_name if handler else "未指派"
    st = ticket.start_time.strftime("%Y-%m-%d %H:%M") if ticket.start_time else "未知"
    ft = ticket.finish_time.strftime("%Y-%m-%d %H:%M") if ticket.finish_time else "未知"
    dur = f"{ticket.duration} 分钟" if ticket.duration else "未知"
    cat = ticket.category or "未分类"
    prio = {1: "高", 2: "中", 3: "低"}.get(ticket.priority, "-")
    src = ticket.source or "-"

    fault = ticket.fault_summary or ticket.description or "待补充"
    root_cause = ticket.root_cause or "待补充"
    solution = ticket.solution or "待补充"
    ai_summary = ticket.ai_summary or ""
    troubleshooting = ticket.troubleshooting or ""

    # 排查过程：优先用 AI 生成的 troubleshooting，否则降级
    if troubleshooting:
        t_lines = troubleshooting.strip().split("\n")
        process_text = "\n".join(f"   {l.strip()}" for l in t_lines if l.strip())
    else:
        process_text = "（排查过程待补充，请查看工单时间线获取操作记录）"

    # 关键命令提取
    key_log = _extract_key_commands(ticket.raw_log or "")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    md = f"""# 售后故障处理报告

> 工单编号：{ticket.ticket_no} ｜ 报告生成时间：{now}

---

### 基本信息

| 项目 | 内容 |
|------|------|
| 工单标题 | {ticket.title} |
| 客户名称 | {cn} |
| 产品版本 | {cv} |
| 部署环境 | {cd} |
| 问题分类 | {cat} |
| 优先级 | {prio} |
| 来源 | {src} |

| 项目 | 内容 |
|------|------|
| 处理工程师 | {hn} |
| 开始处理 | {st} |
| 处理完成 | {ft} |
| 处理时长 | 约 {dur} |

---

### 一、故障现象

{fault}

---

### 二、排查过程

{process_text}

---

### 三、根因分析

{root_cause}

**定性分类**：{cat}

---

### 四、解决方案

{solution}

---

### 五、关键操作记录

> 以下为本次排查中执行的核心命令及关键输出摘录，完整操作日志已存档。

```
{key_log}
```

---

*本报告由轻量化售后工单系统自动生成。*
*报告生成时间：{now}*
*若需修改报告内容，请在工单详情页「Agent 智能分析」区编辑对应字段后重新生成。*
"""

    return md
