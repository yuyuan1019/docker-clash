# 帮我实现一个依赖注入中间件，通过request获取header中的Authorization: Bearer <token>，并验证token是否有效，有效则放行，无效则返回401 Unauthorized错误
from fastapi import Request, HTTPException, Depends
from app.models.sessions import Sessions
from app.models.conn import get_db_session
import time
from typing import Optional

async def get_current_session(request: Request) -> Sessions:
    # 从请求头中获取Authorization字段
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 验证Bearer token格式
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = auth_header.split(" ")[1]

    # 从数据库中查询会话
    with get_db_session() as db:
        session: Optional[Sessions] = db.query(Sessions).filter(Sessions.token == token).first()
        # 如果会话不存在或已过期，返回401错误
        if session is None or session.expires_at < int(time.time()):
            raise HTTPException(status_code=401, detail="Unauthorized")
        return session
