# migrations/utils.py
from alembic.config import Config
from alembic import command
import os


def run_migrations():
    # 获取项目根目录（假设 alembic.ini 在项目根目录）
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 打印 BASE_DIR 以确认路径
    BASE_DIR = BASE_DIR + "/../"
    ALEMBIC_INI_PATH = os.path.join(BASE_DIR, "alembic.ini")

    # 检查 alembic.ini 是否存在
    if not os.path.exists(ALEMBIC_INI_PATH):
        raise FileNotFoundError(f"找不到 alembic.ini 文件: {ALEMBIC_INI_PATH}")

    # 创建 Alembic 配置对象
    alembic_cfg = Config(ALEMBIC_INI_PATH)
    alembic_cfg.set_main_option("script_location", "alembic")  # 指向你的迁移脚本目录

    # 执行 upgrade to head
    command.upgrade(alembic_cfg, "head")
    print(f"✅ 数据库迁移脚本已成功应用到最新版本")
    return True