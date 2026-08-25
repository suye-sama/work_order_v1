"""
认证服务：密码哈希、JWT 生成与校验
"""
from datetime import datetime, timedelta

from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_SECONDS
from app.models.user import User

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对密码进行哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_token(user_id: int, username: str) -> str:
    """生成 JWT Token"""
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.utcnow() + timedelta(seconds=JWT_EXPIRE_SECONDS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解析 JWT Token，失败返回 None"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def authenticate(db: Session, username: str, password: str) -> User | None:
    """验证用户名密码，返回用户或 None"""
    user = db.query(User).filter(
        User.username == username,
        User.deleted == False,  # noqa: E712
    ).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """根据 ID 获取用户"""
    return db.query(User).filter(
        User.id == user_id,
        User.deleted == False,  # noqa: E712
    ).first()


def create_admin_user(db: Session):
    """创建默认管理员账号（仅首次运行）"""
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            real_name="系统管理员",
            role=1,  # 超级管理员
            status=1,
        )
        db.add(admin)

    # 创建默认工程师账号
    engineer = db.query(User).filter(User.username == "engineer").first()
    if not engineer:
        engineer = User(
            username="engineer",
            password_hash=hash_password("engineer123"),
            real_name="售后工程师",
            role=3,  # 售后工程师
            status=1,
        )
        db.add(engineer)

    db.commit()
