from sqlalchemy import Column, Integer, String,text
from sqlalchemy.orm import Session
from .conn import Base, get_db_session  # 从同级conn模块导入Base

# 短链接表
class Urls(Base):
    __tablename__ = "zurl_urls"
    
    id = Column(Integer, primary_key=True, index=True)
    short_url = Column(String(32), unique=True,index=True)  # 短链接
    long_url = Column(String(2048), index=True)  # 长链接
    created_at = Column(Integer)  # 创建时间戳
    updated_at = Column(Integer)  # 更新时间戳
    expires_at = Column(Integer, default=0, server_default=text("0"))  # 过期时间戳，0表示不过期
    is_active = Column(Integer, default=1)  # 是否激活，1为激活，0为未激活
    title = Column(String(256),index=True)  # 链接标题
    description = Column(String(512))  # 链接描述
    ip = Column(String(64))  # 创建链接的IP地址
    clicks = Column(Integer, default=0)  # 点击次数

    @classmethod
    def check_short_url_exists(cls, db: Session, short_url: str) -> bool:
        """
        检查短链接是否存在
        
        Args:
            db: 数据库会话
            short_url: 短链接字符串
            
        Returns:
            bool: 如果短链接存在返回True，否则返回False
        """
        result = db.query(cls).filter(cls.short_url == short_url).first()
        return result is not None

    @classmethod
    def get_by_short_url(cls, db: Session, short_url: str):
        """
        根据短链接查询对应的数据记录
        
        Args:
            db: 数据库会话
            short_url: 短链接字符串
            
        Returns:
            Urls: 如果找到则返回Urls对象，否则返回None
        """
        return db.query(cls).filter(cls.short_url == short_url).first()
    
    @classmethod
    def get_by_long_url(cls, db: Session, long_url: str):
        """
        根据长链接查询对应的数据记录
        
        Args:
            db: 数据库会话
            long_url: 长链接字符串
            
        Returns:
            Urls: 如果找到则返回Urls对象，否则返回None
        """
        return db.query(cls).filter(cls.long_url == long_url).first()
    
    #根据ID查询URL信息
    @classmethod
    def get_by_id(cls, db: Session, id: int):
        """
        根据ID获取URL记录
        
        Args:
            db: 数据库会话
            id: URL记录的ID
            
        Returns:
            Urls: 如果找到则返回Urls对象，否则返回None
        """
        return db.query(cls).filter(cls.id == id).first()
    
    # 写一个函数，接收一个字典，字典内是short_url和点击次数的键值对，一次批量更新点击次数
    @classmethod
    def update_click_counts(cls, click_counts: dict):
        """
        批量更新短链接的点击次数

        Args:
            click_counts: 包含短链接和点击次数的字典
        """
        with get_db_session() as db:
            for short_url, clicks in click_counts.items():
                db.query(cls).filter(cls.short_url == short_url).update({"clicks": cls.clicks + clicks})
            db.commit()