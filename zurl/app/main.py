from typing import Union
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 导入路由
from app.routers.routers import router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.middleware.click import update_click_counts
from fastapi.staticfiles import StaticFiles
from app.utils.migration import run_migrations

# 导入数据库模型
from app.models.sessions import Sessions
from app.models.urls import Urls
from app.models.conn import engine, Base, get_db
from app.config import init

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    init()
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_click_counts, 'interval', minutes=10)
    scheduler.start()
    print("🕒 调度器已启动，定时任务已添加")
    
    yield
    
    # 关闭时执行（可选）
    scheduler.shutdown()
    print("🛑 调度器已关闭")

# 创建 FastAPI 应用实例
app = FastAPI(lifespan=lifespan)

# 挂载静态文件目录（管理后台前端为可选产物，dist 不存在时不挂载，避免启动崩溃；
# 本项目 zurl 仅作 API 使用，后台前端不是必需的）
import os
if os.path.isdir("app/templates/dist"):
    app.mount("/dist", StaticFiles(directory="app/templates/dist"), name="static")


# 注册中间件
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 将路由添加到应用中
app.include_router(router)

print("🕒 启动调度器...")