from sqlalchemy import Column, Integer, String
from .conn import Base  # 从同级conn模块导入Base

# sessions表模型
class Sessions(Base):
    __tablename__ = "zurl_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(32))
    token = Column(String(64), unique=True)
    ip = Column(String(64))
    user_agent = Column(String(256))
    created_at = Column(Integer)  # 使用整数存储时间戳
    updated_at = Column(Integer)  # 使用整数存储时间戳
    # 过期时间，精确到秒
    expires_at = Column(Integer)  # 使用整数存储时间戳
    is_active = Column(Integer, default=1)  # 使用整数表示布尔值，1为True，0为False