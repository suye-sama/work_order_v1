"""
轻量化售后工单系统 - FastAPI 主业务服务
"""
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 环境变量（必须在其他导入之前）

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables, SessionLocal
from app.services.auth_service import create_admin_user

# ---- 注册路由 ----
from app.api.auth import router as auth_router
from app.api.tickets import router as tickets_router
from app.api.customers import router as customers_router
from app.api.dashboard import router as dashboard_router
from app.api.agent import router as agent_router
from app.api.reports import router as reports_router
from app.api.feishu_routes import router as feishu_router  # 飞书回调


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和默认数据"""
    # 启动时：创建表 + 默认账号
    create_tables()
    db = SessionLocal()
    try:
        create_admin_user(db)
    finally:
        db.close()
    print("[启动] 数据库表已创建，默认账号已就绪")
    yield
    # 关闭时：清理资源（如有需要）


app = FastAPI(
    title="售后工单系统 API",
    description="轻量化售后工单管理系统 - 主业务服务",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 跨域配置（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册业务路由
app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(customers_router)
app.include_router(dashboard_router)
app.include_router(agent_router)
app.include_router(reports_router)
app.include_router(feishu_router)  # 飞书事件回调


# ==================== 基础接口 ====================


@app.get("/")
async def root():
    """根路径 - 服务信息"""
    return {
        "service": "售后工单系统 - FastAPI 主业务服务",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/api/v1/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "fastapi-backend",
    }


@app.get("/api/v1/ping")
async def ping():
    """简单连通性测试"""
    return {"message": "pong", "timestamp": datetime.now().isoformat()}


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
