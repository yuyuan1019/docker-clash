# myurls/suo.yt 风格的短链接兼容 API
# 供 sub-web-modify 前端直接调用：
#   POST /short  (form-data: longUrl=<base64(长链接)>, shortKey=<可选自定义后缀>)
#   返回 {"Code": 1, "Message": "success", "ShortUrl": "https://域名/s/xxxx"}
# 短链域名动态从请求头（X-Forwarded-Proto / X-Forwarded-Host / Host）获取，
# 不写死任何地址，配合 nginx 反代即可做到“当前访问域名是什么，短链就是什么”。
import asyncio
import base64
import json
import os
import re
import time
from urllib.parse import urlparse, parse_qs

import aiohttp
import yaml
from fastapi import Request

from app.api.url import DENY_SHORT_URLS
from app.models.conn import get_db_session
from app.models.urls import Urls
from app.utils.helper import random_string, validate_short_link, get_client_ip

# 内部令牌：docker-compose 中通过环境变量 ZURL_SHORT_TOKEN 下发，
# nginx 反代 /short 时注入 X-Short-Token 头，浏览器端不可见。
# 留空字符串则不校验（不推荐公网环境留空）。
SHORT_TOKEN = os.environ.get("ZURL_SHORT_TOKEN", "")
# 对外短链的路径前缀（nginx 将 /s/ 反代到 zurl 根路径做 302 跳转）
SHORT_PREFIX = os.environ.get("ZURL_SHORT_PREFIX", "/s/")
# mihomo 控制 API（容器内网地址）与共享挂载的配置文件路径
MIHOMO_API = os.environ.get("MIHOMO_API", "http://mihomo:9090")
MIHOMO_CONFIG_FILE = os.environ.get("MIHOMO_CONFIG_FILE", "/mihomo-config/config.yaml")
MIHOMO_CONFIG_PATH_IN_CONTAINER = "/root/.config/mihomo/config.yaml"
# SubConverter 容器内网地址（把 /subapi/ 公网地址映射成内网直连，避免域名回环）
SUBCONVERTER_INTERNAL = os.environ.get("SUBCONVERTER_INTERNAL", "http://subconverter:25500")
# Docker 控制接口（用于启停 mihomo 容器）
DOCKER_SOCKET = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")
MIHOMO_CONTAINER = os.environ.get("MIHOMO_CONTAINER", "mihomo")
# 转换应用后自动写入 mihomo 的管理端口与密钥
MIHOMO_EXTERNAL_CONTROLLER = os.environ.get("MIHOMO_EXTERNAL_CONTROLLER", "0.0.0.0:9090")
MIHOMO_SECRET = os.environ.get("MIHOMO_SECRET", "yuan")


def _resp(code: int, message: str, short_url: str = ""):
    # 前端按 res.data.Code === 1 && res.data.ShortUrl !== "" 判断成功，
    # 失败时展示 res.data.Message，因此始终返回 HTTP 200 + 该结构。
    return {"Code": code, "Message": message, "ShortUrl": short_url}


class CompatAPI:
    # 生成短链接（兼容 myurls 协议）
    async def short_create(self, long_url_b64: str, short_key: str, request: Request):
        # 1. 内部令牌校验（nginx 注入 Header，浏览器拿不到）
        if SHORT_TOKEN:
            if request.headers.get("x-short-token", "") != SHORT_TOKEN:
                return _resp(0, "unauthorized")

        # 2. base64 解码长链接
        try:
            long_url = base64.b64decode(long_url_b64).decode("utf-8").strip()
        except Exception:
            return _resp(0, "longUrl base64 解码失败")

        if not re.match(r"^(http://|https://)", long_url):
            return _resp(0, "长链接必须以 http:// 或 https:// 开头")

        if len(long_url) > 2048:
            return _resp(0, "长链接超过 2048 字符限制")

        # 3. 处理自定义短链后缀
        short_url = (short_key or "").strip().lower()
        if short_url:
            if validate_short_link(short_url) is False:
                return _resp(0, "自定义后缀只能是 1-32 位小写字母/数字/中横线/下划线")
            if short_url in DENY_SHORT_URLS:
                return _resp(0, "该后缀为系统保留字")

        with get_db_session() as db:
            # 长链接已存在则直接返回原短链（幂等，可反复生成）
            row = Urls.get_by_long_url(db, long_url)
            if row:
                return _resp(1, "success", self._build_short_url(request, row.short_url))

            if short_url:
                # 自定义后缀与其他长链接冲突
                if Urls.check_short_url_exists(db, short_url):
                    return _resp(0, "自定义后缀已被占用")
            else:
                # 随机生成不冲突的 4 位后缀
                for _ in range(10):
                    candidate = random_string(4).lower()
                    if candidate not in DENY_SHORT_URLS and not Urls.check_short_url_exists(db, candidate):
                        short_url = candidate
                        break
                if not short_url:
                    return _resp(0, "短链生成失败，请重试")

            current_time = int(time.time())
            url = Urls(
                short_url=short_url,
                long_url=long_url,
                # 写入标题，避免触发 update_url_metadata 去抓取超大订阅链接
                title="订阅转换",
                description="",
                created_at=current_time,
                updated_at=current_time,
                expires_at=0,
                ip=get_client_ip(request),
            )
            db.add(url)
            db.commit()

        return _resp(1, "success", self._build_short_url(request, short_url))

    # 根据请求头动态拼接对外短链（nginx 已透传 Host / X-Forwarded-*）
    @staticmethod
    def _build_short_url(request: Request, short_url: str) -> str:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
        prefix = SHORT_PREFIX if SHORT_PREFIX.startswith("/") else "/" + SHORT_PREFIX
        if not prefix.endswith("/"):
            prefix += "/"
        return f"{proto}://{host}{prefix}{short_url}"

    # 一键启用：把本站生成的 Clash 订阅链接应用为 mihomo 的运行配置
    async def apply_to_mihomo(self, sub_url: str, request: Request):
        # 1. 内部令牌校验（nginx 注入 Header，浏览器拿不到）
        if SHORT_TOKEN:
            if request.headers.get("x-short-token", "") != SHORT_TOKEN:
                return _resp(0, "unauthorized")

        sub_url = (sub_url or "").strip()
        if not sub_url:
            return _resp(0, "订阅链接不能为空")

        # 2. 校验是本站后端生成的 clash 链接，并映射为容器内网地址
        parsed = urlparse(sub_url)
        if not parsed.path.startswith("/subapi/"):
            return _resp(0, "仅支持本站后端（/subapi）生成的订阅链接")
        target = parse_qs(parsed.query).get("target", [""])[0]
        if target != "clash":
            return _resp(0, "仅支持生成类型为 Clash 的订阅链接")
        internal_url = SUBCONVERTER_INTERNAL + parsed.path[len("/subapi"):]
        if parsed.query:
            internal_url += "?" + parsed.query

        # 3. 从内网拉取转换后的完整 mihomo 配置（转换可能拉取远程规则，耗时较长）
        try:
            timeout = aiohttp.ClientTimeout(total=180)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(internal_url) as resp:
                    if resp.status != 200:
                        return _resp(0, f"订阅转换后端返回错误：HTTP {resp.status}")
                    cfg_text = await resp.text()
        except Exception as e:
            return _resp(0, f"拉取转换配置失败：{e}")

        try:
            new_cfg = yaml.safe_load(cfg_text)
        except Exception:
            return _resp(0, "转换结果不是有效的 YAML 配置")
        if not isinstance(new_cfg, dict):
            return _resp(0, "转换结果不是有效的 mihomo 配置")

        # 4. 读取当前配置；当前密钥仅用于本次热重载鉴权，
        #    写入的新配置统一使用固定管理端口与密钥（默认 9090 / yuan）
        old_cfg = {}
        if os.path.exists(MIHOMO_CONFIG_FILE):
            try:
                with open(MIHOMO_CONFIG_FILE, encoding="utf-8") as f:
                    old_cfg = yaml.safe_load(f) or {}
            except Exception:
                old_cfg = {}
        secret = old_cfg.get("secret", "")
        new_cfg["external-controller"] = MIHOMO_EXTERNAL_CONTROLLER
        new_cfg["secret"] = MIHOMO_SECRET
        new_cfg["allow-lan"] = old_cfg.get("allow-lan", True)
        new_cfg["bind-address"] = old_cfg.get("bind-address", "*")

        # 5. 原地写入（保持 inode 不变，mihomo 容器的文件 bind mount 才能读到新内容）
        try:
            with open(MIHOMO_CONFIG_FILE, "w", encoding="utf-8") as f:
                yaml.safe_dump(new_cfg, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            return _resp(0, f"写入 mihomo 配置失败：{e}")

        # 6. 确保 mihomo 容器处于运行状态（之前被关闭过则先启动）
        running = await self._mihomo_running()
        if running is None:
            return _resp(0, "无法访问 Docker 控制接口（docker.sock）")
        if not running:
            status, body = await self._docker_request("POST", f"/containers/{MIHOMO_CONTAINER}/start")
            if status not in (204, 304):
                return _resp(0, f"启动 mihomo 容器失败：HTTP {status} {body[:200]}")
            if not await self._wait_mihomo_api(secret):
                return _resp(0, "mihomo 启动后控制接口未就绪，请稍后在面板查看")
            # 刚启动时已自动读取新配置，无需再热重载
        else:
            # 运行中：通知 mihomo 热重载该配置文件
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                headers = {"Authorization": f"Bearer {secret}"} if secret else {}
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.patch(
                        f"{MIHOMO_API}/configs?force=true",
                        json={"path": MIHOMO_CONFIG_PATH_IN_CONTAINER},
                        headers=headers,
                    ) as resp:
                        if resp.status not in (200, 204):
                            body = await resp.text()
                            return _resp(0, f"mihomo 重载配置失败：HTTP {resp.status} {body[:200]}")
            except Exception as e:
                return _resp(0, f"无法连接 mihomo 控制接口：{e}")

        return _resp(1, "已启用到 mihomo 并重载成功，可打开面板查看节点")

    # 查询 mihomo 容器运行状态（供首页展示，GET）
    async def mihomo_status(self, request: Request):
        if SHORT_TOKEN:
            if request.headers.get("x-short-token", "") != SHORT_TOKEN:
                return _resp(0, "unauthorized")
        running = await self._mihomo_running()
        if running is None:
            return {"Code": 0, "Message": "无法访问 Docker 控制接口", "Running": None}
        return {"Code": 1, "Message": "ok", "Running": running}

    # 启动/关闭 mihomo 容器（经 Docker socket，不依赖 mihomo API，关闭后仍可再启动）
    async def control_mihomo(self, action: str, request: Request):
        if SHORT_TOKEN:
            if request.headers.get("x-short-token", "") != SHORT_TOKEN:
                return _resp(0, "unauthorized")
        if action not in ("start", "stop"):
            return _resp(0, "不支持的操作")

        running = await self._mihomo_running()
        if running is None:
            return _resp(0, "无法访问 Docker 控制接口（docker.sock）")

        if action == "stop":
            if not running:
                return _resp(1, "mihomo 已处于关闭状态")
            status, body = await self._docker_request("POST", f"/containers/{MIHOMO_CONTAINER}/stop?t=5")
            if status in (204, 304):
                return _resp(1, "mihomo 已关闭，代理服务已停止")
            return _resp(0, f"关闭失败：HTTP {status} {body[:200]}")

        # start
        if running:
            return _resp(1, "mihomo 已在运行中")
        status, body = await self._docker_request("POST", f"/containers/{MIHOMO_CONTAINER}/start")
        if status not in (204, 304):
            return _resp(0, f"启动失败：HTTP {status} {body[:200]}")
        if await self._wait_mihomo_api(self._current_secret()):
            return _resp(1, "mihomo 已启动")
        return _resp(1, "mihomo 已启动（控制接口尚未就绪，稍后可在面板查看）")

    # ---------- Docker / mihomo 辅助方法 ----------
    @staticmethod
    async def _docker_request(method: str, path: str):
        connector = aiohttp.UnixConnector(path=DOCKER_SOCKET)
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.request(method, f"http://docker{path}") as resp:
                return resp.status, await resp.text()

    async def _mihomo_running(self):
        """True=运行中 False=已停止 None=无法判断"""
        try:
            status, body = await self._docker_request("GET", f"/containers/{MIHOMO_CONTAINER}/json")
            if status == 200:
                return bool(json.loads(body).get("State", {}).get("Running", False))
        except Exception:
            pass
        return None

    @staticmethod
    def _current_secret() -> str:
        try:
            with open(MIHOMO_CONFIG_FILE, encoding="utf-8") as f:
                return (yaml.safe_load(f) or {}).get("secret", "") or ""
        except Exception:
            return ""

    @staticmethod
    async def _wait_mihomo_api(secret: str, retries: int = 30) -> bool:
        headers = {"Authorization": f"Bearer {secret}"} if secret else {}
        for _ in range(retries):
            try:
                timeout = aiohttp.ClientTimeout(total=2)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f"{MIHOMO_API}/version", headers=headers) as resp:
                        if resp.status == 200:
                            return True
            except Exception:
                pass
            await asyncio.sleep(1)
        return False
