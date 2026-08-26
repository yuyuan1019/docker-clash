from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session
from .conn import Base, get_db_session  # 从同级conn模块导入Base

# 定义Options模型
class Options(Base):
    __tablename__ = "zurl_options"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)
    value = Column(String(4096))

    @classmethod
    def set_option(cls, key: str, value: str) -> bool:
        """
        设置或更新配置项。
        存在则更新，不存在则创建；成功返回 True，失败返回 False。
        """
        # 将非字符串值转为字符串存储（如果调用方传入的不是字符串）
        if not isinstance(value, str):
            value = str(value)

        with get_db_session() as db:
            try:
                obj = db.query(cls).filter_by(key=key).first()
                if obj:
                    obj.value = value
                else:
                    obj = cls(key=key, value=value)
                    db.add(obj)
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

    @classmethod
    # 查询参数值，如果不存在则返回 None
    def get_option(cls, key: str) -> str | None:
        """
        获取配置项的值。
        """
        with get_db_session() as db:
            obj = db.query(cls).filter_by(key=key).first()
            return obj.value if obj else None
            
