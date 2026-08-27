# 普通 /subapi/sub 兼容层的自定义 UA（diyua）传输测试。
# 背景：SubConverter-Extended 只认 /sub 请求的 User-Agent 头，不认 diyua 参数；
# zurl 回源若用 aiohttp 默认 UA，会被写进 proxy-provider header，
# 机场会把它识别成旧客户端而拒绝下发节点。
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import yaml

from app.api.compat import CompatAPI


def make_request(query: str, client_ua: str = ""):
    return SimpleNamespace(
        url=SimpleNamespace(query=query),
        headers={"user-agent": client_ua} if client_ua else {},
    )


def config_with_provider(provider_ua: str):
    return {
        "proxy-providers": {
            "Provider_A": {
                "type": "http",
                "url": "https://a.invalid/sub",
                "path": "./providers/Provider_A.yaml",
                "header": {"User-Agent": [provider_ua]},
            }
        },
        "proxy-groups": [
            {"name": "🚀 手动选择", "type": "select", "use": ["Provider_A"]}
        ],
    }


class UpstreamUserAgentTest(unittest.TestCase):
    def test_diyua_takes_precedence(self):
        ua = CompatAPI._upstream_user_agent(
            {"diyua": ["clash-verge/v2.4.5"]}, make_request("", "clash.meta")
        )
        self.assertEqual("clash-verge/v2.4.5", ua)

    def test_falls_back_to_client_ua(self):
        ua = CompatAPI._upstream_user_agent(
            {"diyua": [""]}, make_request("", "mihomo/v1.18.0")
        )
        self.assertEqual("mihomo/v1.18.0", ua)

    def test_empty_when_nothing_available(self):
        ua = CompatAPI._upstream_user_agent({}, make_request(""))
        self.assertEqual("", ua)


class SubscriptionCompatUserAgentTest(unittest.TestCase):
    def run_compat(self, query: str, client_ua: str = ""):
        api = CompatAPI()
        upstream_cfg = config_with_provider("Python/3.11 aiohttp/3.9.5")
        fetch = AsyncMock(
            return_value=(200, yaml.safe_dump(upstream_cfg, allow_unicode=True), {})
        )
        with patch.object(CompatAPI, "_fetch_subconverter", fetch):
            response = asyncio.run(
                api.subscription_compat(make_request(query, client_ua))
            )
        return response, fetch

    def test_diyua_overrides_provider_header(self):
        response, _ = self.run_compat("target=clash&diyua=clash-verge%2Fv2.4.5")

        self.assertEqual(200, response.status_code)
        config = yaml.safe_load(response.body)
        header = config["proxy-providers"]["Provider_A"]["header"]
        self.assertEqual(["clash-verge/v2.4.5"], header["User-Agent"])

    def test_upstream_fetch_receives_diyua_as_user_agent_header(self):
        _, fetch = self.run_compat("target=clash&diyua=clash-verge%2Fv2.4.5")

        self.assertEqual("clash-verge/v2.4.5", fetch.call_args.args[2])

    def test_upstream_fetch_falls_back_to_client_ua(self):
        response, fetch = self.run_compat("target=clash", "mihomo/v1.18.0")

        self.assertEqual("mihomo/v1.18.0", fetch.call_args.args[2])
        # diyua 为空时不覆写 provider header，由回源透传的客户端 UA 决定。
        config = yaml.safe_load(response.body)
        header = config["proxy-providers"]["Provider_A"]["header"]
        self.assertEqual(["Python/3.11 aiohttp/3.9.5"], header["User-Agent"])

    def test_invalid_diyua_returns_400(self):
        response, _ = self.run_compat("target=clash&diyua=bad%0Aua")

        self.assertEqual(400, response.status_code)

    def test_non_clash_target_passes_through_untouched(self):
        api = CompatAPI()
        raw = "c3M6Ly9leGFtcGxl"
        fetch = AsyncMock(return_value=(200, raw, {}))
        with patch.object(CompatAPI, "_fetch_subconverter", fetch):
            response = asyncio.run(
                api.subscription_compat(make_request("target=surge&diyua=x"))
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(raw, response.body.decode())


if __name__ == "__main__":
    unittest.main()
