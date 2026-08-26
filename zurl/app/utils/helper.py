import hashlib
from fastapi import Request,Header

from ipaddress import ip_address, IPv4Address, IPv6Address

# 返回json信息
def show_json(code:int, msg:str, data=None):
    return {
        "code": code,
        "msg": msg,
        "data": data
    }

# 写一个函数，对字符串进行MD5加密，然后返回字符串
def md5(text: str) -> str:
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    return md5.hexdigest()

# 根据参数长度随机生成一个指定长度的字符串，然后返回
def random_string(length: int) -> str:
    import random
    import string
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_client_ip(request:Request) -> str:
    """
    获取客户端 IP 地址，处理 X-Forwarded-For 和 X-Real-IP 头的情况。
    如果 IP 地址格式不正确，则返回 "0.0.0.0"。
    """
    # headers = Headers(raw=request.headers.raw)
    # 尝试通过 X-Forwarded-For 获取
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # 取第一个 IP 地址（通常是客户端原始 IP）
        ip = xff.split(",")[0].strip()
    else:
        # 如果 X-Forwarded-For 不存在，则尝试通过 X-Real-IP 获取
        ip = request.headers.get("X_Real_IP")
        # 取第一个
        if ip:
            ip = ip.split(",")[0].strip()

    # 如果以上两个头都不存在，则直接从请求中获取客户端 IP
    if not ip:
        ip = request.client.host

    # 验证 IP 地址格式是否正确
    try:
        # 使用 ipaddress 模块验证 IP 地址
        parsed_ip = ip_address(ip)
        if not isinstance(parsed_ip, (IPv4Address, IPv6Address)):
            ip = "0.0.0.0"
    except ValueError:
        # 如果 IP 地址格式不正确，则返回默认值
        ip = "0.0.0.0"

    return ip

# 使用正则表达式验证短链接，只能是字母或数字或中横线或下划线
def validate_short_link(short_link: str) -> bool:
    import re
    pattern = r'^[a-z0-9_-]{1,32}$'
    return re.match(pattern, short_link) is not None