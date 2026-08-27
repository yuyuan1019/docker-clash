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
import tempfile
import time
from urllib.parse import parse_qs, quote, urlparse

import aiohttp
import yaml
from fastapi import Request, Response

from app.api.provider_regions import (
    expand_provider_region_groups,
    fix_region_name_compatibility,
    prefix_duplicate_provider_nodes,
)
from app.api.smart_groups import convert_smart_groups, smart_request_error
from app.api.subscription_headers import build_subscription_response_headers
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
MIHOMO_LATEST_CONFIG_FILE = os.environ.get("MIHOMO_LATEST_CONFIG_FILE", "/mihomo-config/latest.yaml")
# SubConverter 容器内网地址（把 /subapi/ 公网地址映射成内网直连，避免域名回环）
SUBCONVERTER_INTERNAL = os.environ.get("SUBCONVERTER_INTERNAL", "http://subconverter:25500")
# Docker 控制接口（用于启停 mihomo 容器）
DOCKER_SOCKET = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")
MIHOMO_CONTAINER = os.environ.get("MIHOMO_CONTAINER", "mihomo")
# 转换应用后自动写入 mihomo 的管理端口与密钥
MIHOMO_EXTERNAL_CONTROLLER = os.environ.get("MIHOMO_EXTERNAL_CONTROLLER", "0.0.0.0:9090")
MIHOMO_SECRET = os.environ.get("MIHOMO_SECRET", "yuan")

PROVIDER_REGION_CONFIG_HOSTS = {
    "testingcf.jsdelivr.net",
    "cdn.jsdelivr.net",
    "raw.githubusercontent.com",
}
PROVIDER_REGION_CONFIG_NAME = "Custom_Clash_Full.ini"


def _resp(code: int, message: str, short_url: str = ""):
    # 前端按 res.data.Code === 1 && res.data.ShortUrl !== "" 判断成功，
    # 失败时展示 res.data.Message，因此始终返回 HTTP 200 + 该结构。
    return {"Code": code, "Message": message, "ShortUrl": short_url}


class CompatAPI:
    @staticmethod
    def _provider_region_request_error(query_args: dict) -> str:
        if query_args.get("target", [""])[0] != "clash":
            return "提供商地区复写仅支持 Clash 配置"
        config_url = query_args.get("config", [""])[0].strip()
        parsed_config = urlparse(config_url)
        if (
            parsed_config.scheme != "https"
            or parsed_config.hostname not in PROVIDER_REGION_CONFIG_HOSTS
            or not parsed_config.path.endswith("/" + PROVIDER_REGION_CONFIG_NAME)
        ):
            return "提供商地区复写仅支持 GitHub 原版 Custom_Clash_Full.ini"
        return ""

    @staticmethod
    def _upstream_user_agent(query_args: dict, request: Request) -> str:
        # SubConverter-Extended 只认 /sub 请求的 User-Agent 头（不认 diyua 参数），
        # 并会把它写进每个 proxy-provider 的 header。回源时优先用页面自定义 UA，
        # 其次透传客户端 UA，避免 aiohttp 默认 UA 被写进 provider 后被机场
        # 识别成旧客户端而拒绝下发节点。
        diyua = query_args.get("diyua", [""])[0].strip()
        return diyua or request.headers.get("user-agent", "")

    @staticmethod
    async def _fetch_subconverter(path: str, query: str, user_agent: str = ""):
        internal_url = SUBCONVERTER_INTERNAL + path
        if query:
            internal_url += "?" + query
        headers = {}
        if user_agent and not any(ch in user_agent for ch in "\r\n\x00"):
            headers["User-Agent"] = user_agent[:256]
        timeout = aiohttp.ClientTimeout(total=180)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(internal_url, headers=headers) as resp:
                return resp.status, await resp.text(), dict(resp.headers)

    @staticmethod
    def _apply_provider_user_agent(config: dict, query_args: dict) -> str:
        provider_user_agent = query_args.get("diyua", [""])[0].strip()
        if len(provider_user_agent) > 256 or any(
            ch in provider_user_agent for ch in "\r\n\x00"
        ):
            return "自定义 User-Agent 不合法"
        providers = config.get("proxy-providers")
        if provider_user_agent and isinstance(providers, dict):
            for provider in providers.values():
                if not isinstance(provider, dict) or provider.get("type") != "http":
                    continue
                headers = provider.get("header")
                if not isinstance(headers, dict):
                    headers = {}
                    provider["header"] = headers
                headers["User-Agent"] = [provider_user_agent]
        return ""

    # 可直接作为订阅地址使用：先取 GitHub FULL 转换结果，再增量生成五地区 provider 组。
    async def provider_region_subscription(self, request: Request):
        query_args = parse_qs(request.url.query)
        error = self._provider_region_request_error(query_args)
        if error:
            return Response(error, status_code=400, media_type="text/plain")

        try:
            status, cfg_text, upstream_headers = await self._fetch_subconverter(
                "/sub", request.url.query, self._upstream_user_agent(query_args, request)
            )
        except Exception as e:
            return Response(
                f"拉取转换配置失败：{e}", status_code=502, media_type="text/plain"
            )
        if status != 200:
            return Response(cfg_text, status_code=status, media_type="text/plain")

        try:
            config = yaml.safe_load(cfg_text)
        except Exception:
            config = None
        if not isinstance(config, dict):
            return Response(
                "转换结果不是有效的 Mihomo YAML 配置",
                status_code=502,
                media_type="text/plain",
            )

        expand_provider_region_groups(config)
        error = self._apply_provider_user_agent(config, query_args)
        if error:
            return Response(error, status_code=400, media_type="text/plain")

        response_headers = build_subscription_response_headers(
            upstream_headers, query_args
        )
        return Response(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
            media_type="text/yaml",
            headers=response_headers,
        )

    # Smart 专版订阅：始终先由 SubConverter 拉取 GitHub 最新远程配置，
    # 再把自动选择组增量复写为 Smart；不保存上游配置副本。
    async def smart_subscription(
        self, request: Request, provider_regions: bool = False
    ):
        query_args = parse_qs(request.url.query)
        error = smart_request_error(query_args)
        if not error and provider_regions:
            error = self._provider_region_request_error(query_args)
        if error:
            return Response(error, status_code=400, media_type="text/plain")

        try:
            status, cfg_text, upstream_headers = await self._fetch_subconverter(
                "/sub", request.url.query, self._upstream_user_agent(query_args, request)
            )
        except Exception as e:
            return Response(
                f"拉取转换配置失败：{e}", status_code=502, media_type="text/plain"
            )
        if status != 200:
            return Response(cfg_text, status_code=status, media_type="text/plain")

        try:
            config = yaml.safe_load(cfg_text)
        except Exception:
            config = None
        if not isinstance(config, dict):
            return Response(
                "转换结果不是有效的 Mihomo YAML 配置",
                status_code=502,
                media_type="text/plain",
            )

        fix_region_name_compatibility(config)
        prefix_duplicate_provider_nodes(config)
        if provider_regions:
            expand_provider_region_groups(config)
        converted = convert_smart_groups(config)
        groups = config.get("proxy-groups")
        if not isinstance(groups, list):
            groups = config.get("Proxy Group", [])
        if converted == 0 and not any(
            isinstance(group, dict) and group.get("type") == "smart"
            for group in groups
        ):
            return Response(
                "GitHub 上游配置中没有可转换的自动策略组",
                status_code=502,
                media_type="text/plain",
            )

        error = self._apply_provider_user_agent(config, query_args)
        if error:
            return Response(error, status_code=400, media_type="text/plain")
        response_headers = build_subscription_response_headers(
            upstream_headers, query_args
        )
        return Response(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
            media_type="text/yaml",
            headers=response_headers,
        )

    # 普通订阅转换兼容层：保留请求参数，只修正遗漏的英文城市地区归属。
    async def subscription_compat(self, request: Request):
        query_args = parse_qs(request.url.query)
        try:
            status, cfg_text, upstream_headers = await self._fetch_subconverter(
                "/sub", request.url.query, self._upstream_user_agent(query_args, request)
            )
        except Exception as e:
            return Response(
                f"拉取转换配置失败：{e}", status_code=502, media_type="text/plain"
            )

        if status != 200 or query_args.get("target", [""])[0] != "clash":
            return Response(cfg_text, status_code=status, media_type="text/plain")

        try:
            config = yaml.safe_load(cfg_text)
        except Exception:
            config = None
        if not isinstance(config, dict):
            return Response(cfg_text, status_code=status, media_type="text/plain")

        fix_region_name_compatibility(config)
        prefix_duplicate_provider_nodes(config)
        # 与五地区复写一致：把 diyua 写入 provider header，防止机场拦截旧 UA。
        error = self._apply_provider_user_agent(config, query_args)
        if error:
            return Response(error, status_code=400, media_type="text/plain")
        response_headers = build_subscription_response_headers(
            upstream_headers, query_args
        )
        return Response(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
            media_type="text/yaml",
            headers=response_headers,
        )

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

    # 生成最新候选配置：只写 latest.yaml，不触碰当前运行的 config.yaml
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
        if parsed.path.startswith(("/smart/", "/smart-provider-regions/")):
            return _resp(
                0,
                "Smart 专版仅供外部 OpenClash Smart 内核订阅，"
                "本站容器使用官方 Mihomo，不能切换为该配置",
            )
        apply_provider_regions = parsed.path.startswith("/provider-regions/")
        if parsed.path.startswith("/subapi/"):
            internal_path = parsed.path[len("/subapi"):]
        elif apply_provider_regions:
            internal_path = parsed.path[len("/provider-regions"):]
        else:
            return _resp(0, "仅支持本站后端生成的订阅链接")
        query_args = parse_qs(parsed.query)
        target = query_args.get("target", [""])[0]
        if target != "clash":
            return _resp(0, "仅支持生成类型为 Clash 的订阅链接")
        if apply_provider_regions:
            error = self._provider_region_request_error(query_args)
            if error:
                return _resp(0, error)

        # 3. 从内网拉取转换后的完整 mihomo 配置（转换可能拉取远程规则，耗时较长）
        try:
            status, cfg_text, _ = await self._fetch_subconverter(
                internal_path, parsed.query, self._upstream_user_agent(query_args, request)
            )
            if status != 200:
                return _resp(0, f"订阅转换后端返回错误：HTTP {status}")
        except Exception as e:
            return _resp(0, f"拉取转换配置失败：{e}")

        try:
            new_cfg = yaml.safe_load(cfg_text)
        except Exception:
            return _resp(0, "转换结果不是有效的 YAML 配置")
        if not isinstance(new_cfg, dict):
            return _resp(0, "转换结果不是有效的 mihomo 配置")

        if apply_provider_regions:
            expand_provider_region_groups(new_cfg)
        else:
            prefix_duplicate_provider_nodes(new_cfg)

        # 4. 从当前配置继承局域网设置；候选配置统一使用管理端口与密钥
        old_cfg = {}
        if os.path.exists(MIHOMO_CONFIG_FILE):
            try:
                with open(MIHOMO_CONFIG_FILE, encoding="utf-8") as f:
                    old_cfg = yaml.safe_load(f) or {}
            except Exception:
                old_cfg = {}
        new_cfg["external-controller"] = MIHOMO_EXTERNAL_CONTROLLER
        new_cfg["secret"] = MIHOMO_SECRET
        new_cfg["allow-lan"] = old_cfg.get("allow-lan", True)
        new_cfg["bind-address"] = old_cfg.get("bind-address", "*")

        # proxy-provider 会由 mihomo 自己再次请求原订阅。若不把页面中的 diyua
        # 写入 provider header，部分机场会把 mihomo 识别成旧客户端，只返回“客户端不支持”提示节点。
        error = self._apply_provider_user_agent(new_cfg, query_args)
        if error:
            return _resp(0, error)

        # 5. 只写入候选文件。只有用户点击“切换当前配置”才会改动 config.yaml。
        candidate_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=os.path.dirname(MIHOMO_LATEST_CONFIG_FILE),
                prefix=".latest-",
                suffix=".yaml.tmp",
                delete=False,
            ) as f:
                candidate_path = f.name
                yaml.safe_dump(new_cfg, f, allow_unicode=True, sort_keys=False)
            os.replace(candidate_path, MIHOMO_LATEST_CONFIG_FILE)
        except Exception as e:
            if candidate_path:
                try:
                    os.unlink(candidate_path)
                except OSError:
                    pass
            return _resp(0, f"写入最新候选配置失败：{e}")

        return _resp(1, "最新配置已生成，当前 mihomo 配置未改动")

    # 查询 mihomo 容器运行状态（供首页展示，GET）
    async def mihomo_status(self, request: Request):
        if SHORT_TOKEN:
            if request.headers.get("x-short-token", "") != SHORT_TOKEN:
                return _resp(0, "unauthorized")
        running = await self._mihomo_running()
        if running is None:
            return {"Code": 0, "Message": "无法访问 Docker 控制接口", "Running": None}
        return {"Code": 1, "Message": "ok", "Running": running}

    # 返回带完整后端地址和环境密钥的面板深链接。
    async def panel_url(self, request: Request):
        if SHORT_TOKEN:
            if request.headers.get("x-short-token", "") != SHORT_TOKEN:
                return _resp(0, "unauthorized")
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
        origin = f"{proto}://{host}"
        backend = f"{origin}/clash"
        panel_url = f"{origin}/xd/?backend={quote(backend, safe='')}&secret={quote(MIHOMO_SECRET, safe='')}"
        return {"Code": 1, "Message": "ok", "PanelUrl": panel_url}

    # 把 latest.yaml 切换为当前 config.yaml，之后才重启/启动 mihomo
    async def activate_latest_config(self, request: Request):
        if SHORT_TOKEN:
            if request.headers.get("x-short-token", "") != SHORT_TOKEN:
                return _resp(0, "unauthorized")

        if not os.path.isfile(MIHOMO_LATEST_CONFIG_FILE):
            return _resp(0, "未找到最新候选配置，请先点击生成最新配置")

        try:
            with open(MIHOMO_LATEST_CONFIG_FILE, encoding="utf-8") as f:
                latest_text = f.read()
            config = yaml.safe_load(latest_text)
        except Exception as e:
            return _resp(0, f"读取最新配置失败：{e}")
        if not isinstance(config, dict):
            return _resp(0, "最新配置文件不是有效的 YAML 配置")

        old_text = ""
        if os.path.isfile(MIHOMO_CONFIG_FILE):
            try:
                with open(MIHOMO_CONFIG_FILE, encoding="utf-8") as f:
                    old_text = f.read()
                yaml.safe_load(old_text)
            except Exception as e:
                return _resp(0, f"读取当前配置失败：{e}")

        running = await self._mihomo_running()
        if running is None:
            return _resp(0, "无法访问 Docker 控制接口（docker.sock）")

        # 原地写入以保持 config.yaml 的 inode，确保 mihomo 的单文件 bind mount 可见。
        try:
            with open(MIHOMO_CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(latest_text)
        except Exception as e:
            return _resp(0, f"切换当前配置文件失败：{e}")

        action = "restart?t=10" if running else "start"
        action_label = "重启" if running else "启动"
        try:
            status, body = await self._docker_request(
                "POST", f"/containers/{MIHOMO_CONTAINER}/{action}"
            )
        except Exception as e:
            self._restore_config(old_text)
            return _resp(0, f"{action_label} mihomo 失败：{e}")
        if status not in (204, 304):
            self._restore_config(old_text)
            return _resp(0, f"{action_label} mihomo 失败：HTTP {status} {body[:200]}")

        if not await self._wait_mihomo_api(config.get("secret", "") or ""):
            # 新配置无法正常启动时，恢复原文件并再重启一次回到旧配置。
            self._restore_config(old_text)
            if old_text:
                try:
                    await self._docker_request(
                        "POST", f"/containers/{MIHOMO_CONTAINER}/restart?t=10"
                    )
                except Exception:
                    pass
            return _resp(0, f"mihomo {action_label}后控制接口未就绪，已回滚原配置")

        return _resp(1, f"已切换当前配置并{action_label} mihomo")

    @staticmethod
    def _restore_config(old_text: str):
        if old_text == "":
            return
        try:
            with open(MIHOMO_CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(old_text)
        except Exception:
            pass

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
