"""
客户服务：CRUD
"""
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


def create_customer(db: Session, data: CustomerCreate, user_id: int) -> Customer:
    """创建客户"""
    customer = Customer(
        name=data.name,
        region=data.region,
        product_version=data.product_version,
        deploy_type=data.deploy_type,
        os=data.os,
        db_type=data.db_type,
        description=data.description,
        create_by=user_id,
        update_by=user_id,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int) -> Customer | None:
    """获取客户详情"""
    return db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.deleted == False,  # noqa: E712
    ).first()


def query_customers(
    db: Session,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """查询客户列表"""
    q = db.query(Customer).filter(Customer.deleted == False)  # noqa: E712

    if keyword:
        q = q.filter(Customer.name.like(f"%{keyword}%"))

    total = q.count()
    records = (
        q.order_by(desc(Customer.create_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": [r.to_dict() for r in records],
    }


def update_customer(
    db: Session, customer_id: int, data: CustomerUpdate, user_id: int
) -> Customer | None:
    """更新客户"""
    customer = get_customer(db, customer_id)
    if not customer:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    customer.update_by = user_id
    customer.update_time = datetime.now()

    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int, user_id: int) -> bool:
    """逻辑删除客户"""
    customer = get_customer(db, customer_id)
    if not customer:
        return False
    customer.deleted = True
    customer.update_by = user_id
    customer.update_time = datetime.now()
    db.commit()
    return True
