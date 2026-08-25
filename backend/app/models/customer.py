"""
客户表 & 联系人表
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customer"

    name = Column(String(200), nullable=False, comment="客户/学校名称")
    region = Column(String(100), nullable=True, comment="所属地区")
    product_version = Column(String(50), nullable=True, comment="产品版本")
    deploy_type = Column(
        String(50), nullable=True, comment="部署方式: 本地部署/云端部署"
    )
    os = Column(String(50), nullable=True, comment="操作系统: Windows/Linux")
    db_type = Column(String(50), nullable=True, comment="数据库类型")
    description = Column(String(500), nullable=True, comment="客户描述")

    # 关联
    contacts = relationship("CustomerContact", back_populates="customer", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "region": self.region,
            "product_version": self.product_version,
            "deploy_type": self.deploy_type,
            "os": self.os,
            "db_type": self.db_type,
            "description": self.description,
            "create_time": self.create_time.isoformat() if self.create_time else None,
        }


class CustomerContact(Base, TimestampMixin):
    __tablename__ = "customer_contact"

    customer_id = Column(
        Integer,
        ForeignKey("customer.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属客户ID",
    )
    name = Column(String(100), nullable=False, comment="联系人姓名")
    phone = Column(String(50), nullable=True, comment="手机号")
    email = Column(String(100), nullable=True, comment="邮箱")
    wechat = Column(String(100), nullable=True, comment="微信号")
    position = Column(String(100), nullable=True, comment="职务")
    is_primary = Column(Boolean, default=False, comment="是否主要联系人")

    # 关联
    customer = relationship("Customer", back_populates="contacts")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "wechat": self.wechat,
            "position": self.position,
            "is_primary": self.is_primary,
        }
