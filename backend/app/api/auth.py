"""
认证接口：登录、获取当前用户
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo
from app.schemas.common import ApiResponse
from app.services.auth_service import (
    authenticate,
    create_token,
)
from app.middleware.auth import get_current_user
from app.config import JWT_EXPIRE_SECONDS

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户名密码登录，返回 JWT Token"""
    user = authenticate(db, req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    token = create_token(user.id, user.username)
    return ApiResponse(
        code=200,
        message="登录成功",
        data={
            "token": token,
            "token_type": "Bearer",
            "expire_seconds": JWT_EXPIRE_SECONDS,
            "user": user.to_dict(),
        },
    )


@router.get("/me", response_model=ApiResponse)
def get_me(user=Depends(get_current_user)):
    """获取当前登录用户信息"""
    return ApiResponse(
        code=200,
        message="success",
        data=user.to_dict(),
    )
