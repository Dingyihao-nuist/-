"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database.session import engine
from app.database.base import Base
from app.database.seed import seed_admin
from app.routers import auth, kb, chat, stats
from app.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表 + 种子数据"""
    setup_logging()
    logger.info("应用启动中...")

    # 建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")

    # 种子数据
    await seed_admin()

    # 延迟加载 ChromaDB & Embedding 模型（首次使用时才下载）
    # 避免启动时等待模型下载，加快冷启动
    logger.info("应用启动完成（Embedding 模型将在首次上传文档时自动下载）")

    yield

    # 关闭
    await engine.dispose()
    logger.info("应用已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs",
    lifespan=lifespan,
)

# CORS — 仅开放开发环境所需的方法和请求头
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(kb.router)
app.include_router(chat.router)
app.include_router(stats.router)


# 全局异常处理器：记录完整错误日志，向客户端返回安全消息
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常 [{request.method} {request.url.path}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
