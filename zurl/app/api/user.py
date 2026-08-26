from fastapi import FastAPI, Form,Request

from app.utils.helper import *
import time
from app.models.sessions import Sessions
from app.models.conn import get_db, get_db_session
from pydantic import BaseModel,EmailStr
import re
from app.config import get_config,save_config

class UserItem(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserAPI:
    # 用户初始化
    def init(self,item:UserItem):
        username = item.username.strip().lower()
        passwort = item.password.strip()

        # 获取环境变量里面的用户名和密码
        env_username = get_config()["user"]["USERNAME"]
        env_password = get_config()["user"]["PASSWORD"]

        # 如果其中一个不为空，则视为已经初始化过了
        if env_username or env_password:
            return show_json(400, "no.repeat.init")

        # 正则限制用户名只能是字母或数字组合，且长度大于3
        if not re.match(r"^[a-z0-9]{3,}$", username):
            return show_json(400, "user.name.invalid")
        # 正则限制密码只能是字母或数字或部分特殊字符，且长度大于6
        if not re.match(r"^[a-zA-Z0-9!@#$%^&*()_+={}\[\]:;\"'<>,.?/\\-]{6,}$", passwort):
            return show_json(400, "password.not.allow")

        # 加密后的密码
        en_password = md5(username + passwort)
        
        # 写入环境变量
        get_config()["user"]["USERNAME"] = username
        get_config()["user"]["PASSWORD"] = en_password
        get_config()["user"]["EMAIL"] = item.email
        # 保存配置文件
        save_config()
        # 返回初始化成功信息
        return show_json(200, "success", {
            "username": username,
            "email": item.email
        })
    
    # 修改密码
    def change_password(self,old_password: str = Form(...), new_password: str = Form(...)):
        # 获取配置文件中的用户名和密码
        env_username = get_config()["user"]["USERNAME"]
        env_password = get_config()["user"]["PASSWORD"]

        # 如果旧密码是空的
        if not old_password:
            return show_json(400, "oldpass.notallow.empty")
        
        # 如果新密码是空的
        if not new_password:
            return show_json(400, "newpass.notallow.empty")
        
        # 加密旧密码
        md5_old_password = md5(env_username + old_password)

        # 判断旧密码是否正确
        if env_password != md5_old_password:
            return show_json(400, "oldpass.error")
        
        # 正则限制新密码只能是字母或数字或部分特殊字符，且长度大于6
        if not re.match(r"^[a-zA-Z0-9!@#$%^&*()_+={}\[\]:;\"'<>,.?/\\-]{6,}$", new_password):
            return show_json(400, "password.not.allow")
        
        # 加密新密码
        md5_new_password = md5(env_username + new_password)

        # 更新配置文件中的密码
        get_config()["user"]["PASSWORD"] = md5_new_password
        save_config()
        
        return show_json(200, "success")

    # 用户登录
    def login(self,username: str, password: str,request: Request):
        # 获取配置文件中的用户名和密码
        env_username = get_config()["user"]["USERNAME"]
        env_password = get_config()["user"]["PASSWORD"]

        # 如果用户名不正确
        if username != env_username:
            return show_json(400, "username.error")
        
        # 如果密码是空的
        if not password:
            return show_json(400, "password.not.allow.empty")
        
        # 加密密码
        md5_password = md5(username + password)

        # 判断密码是否正确
        if env_password != md5_password:
            return show_json(400, "password.error")
        
        # 登录成功
        token = "web-" + random_string(28)
        # 获取客户端 IP 地址
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "Unknown")
        # 获取当前时间戳
        current_time = int(time.time())
        created_at = current_time
        updated_at = current_time
        expires_at = current_time + 3600 * 24 * 30  # 设置过期时间为30天
        is_active = 1  # 设置为1表示活跃状态
        # 写入数据库中
        with get_db_session() as db:
            session = Sessions(
                username=username,
                token=token,
                ip=ip,
                user_agent=user_agent,
                created_at=created_at,
                updated_at=updated_at,
                expires_at=expires_at,
                is_active=is_active
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            # 返回登录成功信息
            return show_json(200, "success", {
                "token": session.token,
                "expires_at": session.expires_at,
                "username": session.username,
                "ip": session.ip,
                "user_agent": session.user_agent
            })
    
    # 用户登录状态
    def is_login(self):
        return show_json(200,"success","")
    
    # 用户退出登录，删除数据库中的session
    async def logout(self,request: Request):
        # 获取请求头中的 token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return show_json(400, "no.session.token")
        
        # 提取 token 部分
        if not auth_header.startswith("Bearer "):
            return show_json(400, "invalid.session.token")
        
        token = auth_header.split(" ")[1]
        
        # 从数据库中删除对应的 session
        with get_db_session() as db:
            session = db.query(Sessions).filter(Sessions.token == token).first()
            if not session:
                return show_json(400, "session.expired")
            
            db.delete(session)
            db.commit()
        
        return show_json(200, "success")
    
    # 创建token
    async def create_token(self,request: Request):
        # 获取IP
        ip = get_client_ip(request)
        # 获取User-Agent
        user_agent = request.headers.get("User-Agent", "Unknown")
        token = "sk-" + random_string(29)
        # 获取当前时间戳
        current_time = int(time.time())
        expires_at = current_time + 3600 * 24 * 30 * 365 * 50  # 设置50年过期
        # 写入sessions表中
        with get_db_session() as db:
            # 检查数据库中是否存在username为"system"的记录，且token为sk-开头的记录
            existing_session = db.query(Sessions).filter(
                Sessions.username == "system",
                Sessions.token.startswith("sk-")
            ).first()
            if existing_session:
                db.delete(existing_session)
                db.commit()
                return show_json(400, "token.already.exists")
            
            session = Sessions(
                username="system",
                token=token,
                ip=ip,
                user_agent=user_agent,
                created_at=current_time,
                updated_at=current_time,
                expires_at=expires_at,
                is_active=1
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return show_json(200, "success", {
                "token": token
            })
    
    # 更换token
    async def change_token(self,request: Request):
        # 获取IP
        ip = get_client_ip(request)
        # 获取User-Agent
        user_agent = request.headers.get("User-Agent", "Unknown")
        token = "sk-" + random_string(29)
        # 获取当前时间戳
        current_time = int(time.time())
        expires_at = current_time + 3600 * 24 * 30 * 365 * 50  # 设置50年过期
        # 写入sessions表中
        with get_db_session() as db:
            # 检查数据库中是否存在username为"system"的记录，且token为sk-开头的记录
            existing_session = db.query(Sessions).filter(
                Sessions.username == "system",
                Sessions.token.startswith("sk-")
            ).first()
            if not existing_session:
                return show_json(400, "token.not.exist")
            
            # 更新现有记录
            existing_session.token = token
            existing_session.ip = ip
            existing_session.user_agent = user_agent
            existing_session.updated_at = current_time
            existing_session.expires_at = expires_at
            db.commit()
            db.refresh(existing_session)
            return show_json(200, "success", {
                "token": token
            })
    
    # 获取token
    async def get_token(self,request: Request):
        # 从数据库中查询对应的 session,要求username为"system"且token以"sk-"开头
        with get_db_session() as db:
            session = db.query(Sessions).filter(
                Sessions.username == "system",
                Sessions.token.startswith("sk-")
            ).first()
            if not session:
                return show_json(404, "token.not.exist")
            return show_json(200, "success", {
                "token": session.token,
                "expires_at": session.expires_at,
                "ip": session.ip,
                "user_agent": session.user_agent
            })
        