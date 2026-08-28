import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import yaml

from app.api.compat import CompatAPI
from app.api.smart_groups import (
    SMART_CONFIG_NAMES,
    convert_smart_groups,
    custom_clash_request_error,
    smart_request_error,
)


def make_request(query: str):
    return SimpleNamespace(
        url=SimpleNamespace(query=query),
        headers={"user-agent": "mihomo-smart"},
    )


class SmartRequestValidationTest(unittest.TestCase):
    def test_all_page_clash_versions_are_allowlisted(self):
        self.assertEqual(
            {
                "Custom_Clash.ini",
                "Custom_Clash_Full.ini",
                "Custom_Clash_Lite.ini",
                "Custom_Clash_GFW.ini",
                "Custom_Clash_Mainland.ini",
                "Custom_Clash_Fallback.ini",
                "Custom_Clash_Full_Fallback.ini",
                "Custom_Clash_Lite_Fallback.ini",
                "Custom_Clash_GFW_Fallback.ini",
            },
            SMART_CONFIG_NAMES,
        )

    def test_accepts_supported_github_config(self):
        for config_url in (
            "https://testingcf.jsdelivr.net/gh/Aethersailor/"
            "Custom_OpenClash_Rules@refs/heads/main/cfg/Custom_Clash.ini",
            "https://raw.githubusercontent.com/Aethersailor/"
            "Custom_OpenClash_Rules/refs/heads/main/cfg/Custom_Clash.ini",
        ):
            with self.subTest(config_url=config_url):
                query = {"target": ["clash"], "config": [config_url]}
                self.assertEqual("", smart_request_error(query))

    def test_provider_region_mode_accepts_every_page_clash_version(self):
        for config_name in SMART_CONFIG_NAMES:
            with self.subTest(config_name=config_name):
                query = {
                    "target": ["clash"],
                    "config": [
                        "https://testingcf.jsdelivr.net/gh/Aethersailor/"
                        "Custom_OpenClash_Rules@refs/heads/main/cfg/"
                        + config_name
                    ],
                }
                self.assertEqual(
                    "",
                    custom_clash_request_error(
                        query, "香港/日本提供商复写版"
                    ),
                )

    def test_rejects_non_clash_and_untrusted_config(self):
        self.assertIn(
            "仅支持 Clash",
            smart_request_error({"target": ["surge"], "config": [""]}),
        )
        self.assertIn(
            "页面内置",
            smart_request_error(
                {
                    "target": ["clash"],
                    "config": ["https://evil.invalid/Custom_Clash.ini"],
                }
            ),
        )
        self.assertIn(
            "页面内置",
            smart_request_error(
                {
                    "target": ["clash"],
                    "config": [
                        "https://cdn.jsdelivr.net/gh/other/repo@main/"
                        "Custom_Clash.ini"
                    ],
                }
            ),
        )


class SmartGroupConversionTest(unittest.TestCase):
    def test_converts_automatic_groups_and_preserves_fallback(self):
        config = {
            "proxy-groups": [
                {
                    "name": "♻️ 自动选择",
                    "type": "url-test",
                    "use": ["A", "B"],
                    "url": "https://cp.cloudflare.com/generate_204",
                    "interval": 300,
                    "tolerance": 50,
                    "lazy": True,
                },
                {
                    "name": "下载均衡",
                    "type": "load-balance",
                    "use": ["A", "B"],
                    "strategy": "consistent-hashing",
                    "persistent": True,
                },
                {
                    "name": "🚀 故障转移",
                    "type": "fallback",
                    "proxies": ["♻️ 自动选择", "下载均衡"],
                },
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["🚀 故障转移"],
                },
            ]
        }

        changed = convert_smart_groups(config)

        self.assertEqual(2, changed)
        auto, balance, fallback, manual = config["proxy-groups"]
        self.assertEqual("smart", auto["type"])
        self.assertEqual(50, auto["tolerance"])
        self.assertEqual(300, auto["interval"])
        self.assertTrue(auto["uselightgbm"])
        self.assertFalse(auto["collectdata"])
        self.assertEqual("smart", balance["type"])
        self.assertNotIn("strategy", balance)
        self.assertNotIn("persistent", balance)
        self.assertEqual("fallback", fallback["type"])
        self.assertEqual("select", manual["type"])

    def test_normalizes_existing_smart_group_and_is_idempotent(self):
        config = {
            "proxy-groups": [
                {
                    "name": "Smart",
                    "type": "smart",
                    "collectdata": True,
                    "sample-rate": 0.5,
                }
            ]
        }

        self.assertEqual(0, convert_smart_groups(config))
        self.assertEqual(0, convert_smart_groups(config))
        group = config["proxy-groups"][0]
        self.assertTrue(group["uselightgbm"])
        self.assertFalse(group["collectdata"])
        self.assertNotIn("sample-rate", group)

    def test_missing_groups_is_unchanged(self):
        config = {"rules": ["MATCH,DIRECT"]}

        self.assertEqual(0, convert_smart_groups(config))
        self.assertEqual({"rules": ["MATCH,DIRECT"]}, config)


class SmartSubscriptionTest(unittest.TestCase):
    config_url = (
        "https://testingcf.jsdelivr.net/gh/Aethersailor/"
        "Custom_OpenClash_Rules@refs/heads/main/cfg/Custom_Clash_Full.ini"
    )

    def upstream_config(self):
        return {
            "proxy-providers": {
                "A": {"type": "http", "url": "https://a.invalid/sub"},
                "B": {"type": "http", "url": "https://b.invalid/sub"},
            },
            "proxy-groups": [
                {
                    "name": "🇭🇰 香港节点",
                    "type": "url-test",
                    "use": ["A", "B"],
                    "filter": "香港|HK",
                    "tolerance": 50,
                },
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["🇭🇰 香港节点"],
                },
            ],
        }

    def run_subscription(self, provider_regions: bool = False):
        query = "target=clash&config=" + self.config_url
        fetch = AsyncMock(
            return_value=(
                200,
                yaml.safe_dump(self.upstream_config(), allow_unicode=True),
                {"Content-Disposition": 'attachment; filename="Smart.yaml"'},
            )
        )
        with patch.object(CompatAPI, "_fetch_subconverter", fetch):
            response = asyncio.run(
                CompatAPI().smart_subscription(
                    make_request(query), provider_regions=provider_regions
                )
            )
        return response, fetch

    def test_fetches_latest_upstream_then_converts_to_smart(self):
        response, fetch = self.run_subscription()

        self.assertEqual(200, response.status_code)
        config = yaml.safe_load(response.body)
        group = config["proxy-groups"][0]
        self.assertEqual("smart", group["type"])
        self.assertTrue(group["uselightgbm"])
        self.assertFalse(group["collectdata"])
        self.assertEqual("/sub", fetch.call_args.args[0])
        self.assertIn("Custom_Clash_Full.ini", fetch.call_args.args[1])

    def test_provider_region_mode_derives_smart_groups_per_provider(self):
        response, _ = self.run_subscription(provider_regions=True)

        self.assertEqual(200, response.status_code)
        config = yaml.safe_load(response.body)
        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual("smart", groups["🇭🇰 香港_A"]["type"])
        self.assertEqual(["A"], groups["🇭🇰 香港_A"]["use"])
        self.assertEqual("smart", groups["🇭🇰 香港_B"]["type"])

    def test_gfw_fallback_provider_mode_synthesizes_smart_region_groups(self):
        upstream = {
            "proxy-providers": {
                "A": {"type": "http", "url": "https://a.invalid/sub"},
            },
            "proxy-groups": [
                {
                    "name": "🚀 故障转移",
                    "type": "fallback",
                    "proxies": ["A 节点"],
                    "url": "https://cp.cloudflare.com/generate_204",
                    "interval": 300,
                }
            ],
        }
        query = (
            "target=clash&config=https://testingcf.jsdelivr.net/gh/"
            "Aethersailor/Custom_OpenClash_Rules@refs/heads/main/cfg/"
            "Custom_Clash_GFW_Fallback.ini"
        )
        fetch = AsyncMock(
            return_value=(200, yaml.safe_dump(upstream, allow_unicode=True), {})
        )

        with patch.object(CompatAPI, "_fetch_subconverter", fetch):
            response = asyncio.run(
                CompatAPI().smart_subscription(
                    make_request(query), provider_regions=True
                )
            )

        self.assertEqual(200, response.status_code)
        config = yaml.safe_load(response.body)
        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual("smart", groups["🇭🇰 香港_A"]["type"])
        self.assertEqual("smart", groups["🇯🇵 日本_A"]["type"])
        self.assertIn("🇭🇰 香港_A", groups["🚀 故障转移"]["proxies"])

    def test_rejects_unsupported_remote_config_before_fetch(self):
        request = make_request(
            "target=clash&config=https://evil.invalid/Custom_Clash.ini"
        )
        fetch = AsyncMock()
        with patch.object(CompatAPI, "_fetch_subconverter", fetch):
            response = asyncio.run(CompatAPI().smart_subscription(request))

        self.assertEqual(400, response.status_code)
        fetch.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
