import os
import toml  # for Python < 3.11; use tomllib in 3.11+
from fastapi import Depends, HTTPException
import redis.asyncio as redis
from fastapi.templating import Jinja2Templates
from app.models.conn import DB_FILE_PATH
from alembic.config import Config
from alembic import command


# 指定模板目录
templates = Jinja2Templates(directory="app/templates")

# 获取当前文件目录（项目根目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "data/config.toml")

config = None
# 获取配置
def get_config():
    global config
    """安全地获取配置，如果未初始化则抛出异常"""
    if config is None:
        # 如果配置文件存在，直接加载
        with open(CONFIG_PATH, "r") as f:
            config = toml.load(f)
    return config

# 保存配置文件
def save_config():
    with open(CONFIG_PATH, "w") as f:
        toml.dump(config, f)

# 全局 Redis 连接池（单例）
_redis_pool = None

async def get_redis_pool():
    """获取 Redis 连接池（单例模式）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=config["redis"]["REDIS_HOST"],
            port=config["redis"]["REDIS_PORT"],
            db=config["redis"]["REDIS_DB"],
            password=config["redis"].get("REDIS_PASSWORD", None),
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
            socket_timeout=5,
            health_check_interval=30
        )
    return _redis_pool

async def get_redis():
    """获取 Redis 客户端"""
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)

# 初始化操作
def init():
    global config
    print("Initializing configuration...")
    # print(f"配置文件路径: {DB_FILE_PATH}")
    # 检查data/config.toml文件是否存在，如果不存在，则复制站点下的config.simple.toml
    if not os.path.exists(CONFIG_PATH):
        simple_config_path = os.path.join(BASE_DIR, "config.simple.toml")  # 修正路径
        if os.path.exists(simple_config_path):
            with open(simple_config_path, "r") as f:
                config = toml.load(f)
            save_config()
        else:
            raise FileNotFoundError("The config.simple.toml configuration file does not exist!")
        
        
    print("Initialization complete.")


