import time

from sqlalchemy import Column, Integer, String
from .conn import Base, get_db_session  # 从同级conn模块导入Base


# 订阅转换页面的「提供商名称 -> 订阅链接」字典表
class SubProvider(Base):
    __tablename__ = "zurl_sub_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), index=True)               # 提供商名称/简称
    url = Column(String(2048), unique=True, index=True)  # 订阅链接（唯一，重复保存视为更新名称）
    created_at = Column(Integer)                         # 创建时间戳
    updated_at = Column(Integer)                         # 更新时间戳

    @classmethod
    def list_all(cls):
        """
        查询全部提供商记录，按最近更新排序。

        Returns:
            list[dict]: 提供商记录列表
        """
        with get_db_session() as db:
            rows = db.query(cls).order_by(cls.updated_at.desc(), cls.id.desc()).all()
            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "url": row.url,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]

    @classmethod
    def count(cls) -> int:
        with get_db_session() as db:
            return db.query(cls).count()

    @classmethod
    def url_exists(cls, url: str) -> bool:
        with get_db_session() as db:
            return db.query(cls).filter(cls.url == url).first() is not None

    @classmethod
    def upsert(cls, name: str, url: str):
        """
        按 url 去重保存：链接已存在则更新名称，不存在则新建。

        Returns:
            dict: 保存后的记录；失败返回 None
        """
        now = int(time.time())
        with get_db_session() as db:
            try:
                obj = db.query(cls).filter(cls.url == url).first()
                if obj:
                    obj.name = name
                    obj.updated_at = now
                else:
                    obj = cls(name=name, url=url, created_at=now, updated_at=now)
                    db.add(obj)
                db.commit()
                return {
                    "id": obj.id,
                    "name": obj.name,
                    "url": obj.url,
                    "created_at": obj.created_at,
                    "updated_at": obj.updated_at,
                }
            except Exception:
                db.rollback()
                return None

    @classmethod
    def delete_by_id(cls, provider_id: int) -> bool:
        """
        按 ID 删除提供商记录。

        Returns:
            bool: 删除成功返回 True，记录不存在或失败返回 False
        """
        with get_db_session() as db:
            try:
                obj = db.query(cls).filter(cls.id == provider_id).first()
                if not obj:
                    return False
                db.delete(obj)
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False
