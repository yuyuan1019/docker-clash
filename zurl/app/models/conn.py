from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# 数据库文件路径
DB_FILE_PATH = "app/data/db/zurl.db"
# SQLite连接配置
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600,
)

# 设置SQLite PRAGMA语句以启用WAL模式和性能优化
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA cache_size=-32000")  # 32MB
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()

# 声明基类
Base = declarative_base()

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 提供get_db依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 提供非依赖注入场景下的数据库会话上下文管理器
@contextmanager
def get_db_session():
    db_gen = get_db()
    db = next(db_gen)
    try:
        yield db
    finally:
        db_gen.close()