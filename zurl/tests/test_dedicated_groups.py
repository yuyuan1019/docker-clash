"""专属节点组端到端：流媒体节点 / 塔菲美国节点（含订阅级排他）。

覆盖 transform.yaml 的两个专属组语义：
- 专属组只在指定策略组里可选；
- 其它分组看不到专属组的节点（名称排他）与该订阅的任何节点（订阅级排他）。
"""

import asyncio
import os
import re
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode

import yaml
from fastapi import Request

from app.api.compat import CompatAPI

STREAMING_GROUP = "流媒体节点"
TAFFY_GROUP = "塔菲美国节点"
TAFFY_PROVIDER = "永雏塔菲的魔法卷轴"
OTHER_PROVIDER = "机场A"
VIDEO_SERVICES = (
    "🎶 TikTok", "📹 YouTube", "🎥 Netflix", "🎥 DisneyPlus", "🎥 HBO",
    "🎥 PrimeVideo", "🎥 AppleTV+", "🎥 Emby", "📺 Bahamut", "🌎 国外媒体",
)
AI_SERVICES = ("🤖 ChatGPT", "🤖 AI服务")
TAFFY_US_NODES = (
    "🇺🇸美国 Premium | 0.28",
    "🇺🇸美国 Pulse | 0.28",
    "🇺🇸美国 | 0.25",
    "🇺🇸美国 01 | 0.25",
    "🇺🇸美国 02 | 0.26",
)
TAFFY_OTHER_NODES = (
    "🇸🇬新加坡 B | 0.28",
    "🇭🇰香港 01 | 0.23",
    "🇯🇵日本 AB | 0.26",
    "🔥欠费后可用 应急 0.35",
)


def transform_settings():
    return {
        "group_defaults": [],
        "custom_groups": [
            {
                "name": STREAMING_GROUP,
                "filter": "流媒体",
                "type": "url-test",
                "exclude_providers": [TAFFY_PROVIDER],
                "exclusive": True,
                "attach_index": 1,
                "attach_to": list(VIDEO_SERVICES),
            },
            {
                "name": TAFFY_GROUP,
                "providers": [TAFFY_PROVIDER],
                "filter": r"(?i)(美国|(?<![a-z])us(?![a-z])|united[ _-]*states|🇺🇸)",
                "type": "select",
                "exclusive_providers": [TAFFY_PROVIDER],
                "attach_index": 1,
                "attach_to": list(AI_SERVICES),
            },
        ],
    }


def provider_config(providers=(OTHER_PROVIDER, TAFFY_PROVIDER)):
    use = list(providers)
    region_groups = (
        "🇭🇰 香港节点", "🇺🇸 美国节点", "🇯🇵 日本节点",
        "🇸🇬 新加坡节点", "🇼🇸 台湾节点", "🇰🇷 韩国节点",
    )
    return {
        "proxy-providers": {
            name: {"type": "http", "url": f"https://{index}.invalid/sub"}
            for index, name in enumerate(providers)
        },
        "proxy-groups": [
            {
                "name": "🚀 手动选择",
                "type": "select",
                "use": use,
                "filter": ".*",
                "proxies": ["♻️ 自动选择", *region_groups],
            },
            {"name": "♻️ 自动选择", "type": "url-test", "use": use, "filter": ".*"},
            {
                "name": "💬 即时通讯",
                "type": "select",
                "proxies": ["🚀 手动选择", "♻️ 自动选择", "🎯 全球直连"],
            },
            *(
                {
                    "name": name,
                    "type": "select",
                    "use": use,
                    "filter": ".*",
                    "proxies": ["🚀 手动选择", "♻️ 自动选择", "🎯 全球直连"],
                }
                for name in (*VIDEO_SERVICES, *AI_SERVICES[1:], "🐟 漏网之鱼")
            ),
            {
                "name": "🤖 ChatGPT",
                "type": "select",
                "use": use,
                "filter": ".*",
                "proxies": ["🚀 手动选择", "♻️ 自动选择", "🇺🇸 美国节点"],
            },
            *(
                {"name": name, "type": "url-test", "use": use, "filter": pattern}
                for name, pattern in (
                    ("🇭🇰 香港节点", "(?i)(香港|HK)"),
                    ("🇺🇸 美国节点", "(?i)(美国|US)"),
                    ("🇯🇵 日本节点", "(?i)(日本|JP)"),
                    ("🇸🇬 新加坡节点", "(?i)(新加坡|SG)"),
                    ("🇼🇸 台湾节点", "(?i)(台湾|TW)"),
                    ("🇰🇷 韩国节点", "(?i)(韩国|KR)"),
                )
            ),
            {"name": "🎯 全球直连", "type": "select", "proxies": ["DIRECT"]},
        ],
    }


def convert(config=None, settings=None, template="Custom_Clash.ini"):
    config = deepcopy(config if config is not None else provider_config())
    query = urlencode({"target": "clash", "config": "https://example.invalid/cfg/" + template})
    request = Request({
        "type": "http", "method": "GET", "path": "/subapi/sub",
        "query_string": query.encode(), "headers": [],
    })
    fetch = AsyncMock(return_value=(200, yaml.safe_dump(config, allow_unicode=True), {}))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as file:
        yaml.safe_dump(settings if settings is not None else transform_settings(), file, allow_unicode=True)
        file.flush()
        with patch.dict(os.environ, {"TRANSFORM_CONFIG_FILE": file.name}):
            with patch.object(CompatAPI, "_fetch_subconverter", fetch):
                response = asyncio.run(CompatAPI().subscription_compat(request))
    return yaml.safe_load(bytes(response.body))


def groups_of(result):
    return {group["name"]: group for group in result["proxy-groups"]}


class DedicatedGroupsTest(unittest.TestCase):
    def test_both_groups_are_created_with_expected_sources(self):
        groups = groups_of(convert())
        self.assertEqual("url-test", groups[STREAMING_GROUP]["type"])
        self.assertEqual("流媒体", groups[STREAMING_GROUP]["filter"])
        self.assertEqual([OTHER_PROVIDER], groups[STREAMING_GROUP]["use"])
        self.assertEqual("select", groups[TAFFY_GROUP]["type"])
        self.assertEqual([TAFFY_PROVIDER], groups[TAFFY_GROUP]["use"])
        self.assertIn("美国", groups[TAFFY_GROUP]["filter"])

    def test_groups_are_selectable_only_in_their_own_policy_groups(self):
        groups = groups_of(convert())
        for name in VIDEO_SERVICES:
            self.assertIn(STREAMING_GROUP, groups[name]["proxies"])
            self.assertNotIn(TAFFY_GROUP, groups[name]["proxies"])
        for name in AI_SERVICES:
            self.assertIn(TAFFY_GROUP, groups[name]["proxies"])
            self.assertNotIn(STREAMING_GROUP, groups[name]["proxies"])
        for name, group in groups.items():
            if name in (*VIDEO_SERVICES, STREAMING_GROUP):
                continue
            self.assertNotIn(STREAMING_GROUP, group.get("proxies", []), name)
        for name, group in groups.items():
            if name in (*AI_SERVICES, TAFFY_GROUP):
                continue
            self.assertNotIn(TAFFY_GROUP, group.get("proxies", []), name)

    def test_groups_sit_in_second_position_not_as_default(self):
        # 第二顺位：不占默认项，其它订阅没有对应节点时也不会变成空选中
        groups = groups_of(convert())
        for name in VIDEO_SERVICES:
            self.assertEqual(1, groups[name]["proxies"].index(STREAMING_GROUP), name)
            self.assertEqual("🚀 手动选择", groups[name]["proxies"][0], name)
        for name in AI_SERVICES:
            self.assertEqual(1, groups[name]["proxies"].index(TAFFY_GROUP), name)
            self.assertEqual("🚀 手动选择", groups[name]["proxies"][0], name)

    def test_other_groups_hide_streaming_nodes_but_keep_provider_nodes(self):
        groups = groups_of(convert())
        # 自定义组自身的过滤条件由配置决定（流媒体组按「流媒体」取节点，
        # 塔菲组按「美国」取节点），不再叠加其它组的隐藏前缀
        exempt = {*VIDEO_SERVICES, STREAMING_GROUP, TAFFY_GROUP}
        for name, group in groups.items():
            if name in exempt or "use" not in group:
                continue
            with self.subTest(group=name):
                self.assertTrue(group["filter"].startswith("^(?!"), group["filter"])
                self.assertIn("流媒体", group["filter"])
                # 负向前瞻不能吃掉整组的节点来源
                self.assertEqual(list(group["use"]), group["use"])
        # 地区组同样要隐藏流媒体节点，且原地区条件仍然保留（仍可匹配任意位置）
        hk_filter = groups["🇭🇰 香港节点"]["filter"]
        self.assertTrue(hk_filter.startswith("^(?!"))
        self.assertIn("(香港|HK)", hk_filter)
        self.assertIn("[\\s\\S]*?", hk_filter)  # 原 filter 仍可匹配任意位置

    def test_ai_groups_hide_taffy_provider_nodes(self):
        groups = groups_of(convert())
        for name, group in groups.items():
            if name == TAFFY_GROUP:
                self.assertEqual([TAFFY_PROVIDER], group["use"])
                continue
            if "use" not in group:
                continue
            with self.subTest(group=name):
                self.assertNotIn(TAFFY_PROVIDER, group["use"])

    def test_region_filters_still_match_prefixed_provider_nodes(self):
        # 同源多账号的订阅会给节点加 [提供商] 前缀，地区组必须仍能匹配到它们。
        # （美国组的 filter 经过地区别名补丁后含内联标志，Python re 不接受非开头
        #  的 (?i)；这类表达式只做字符串保留断言，真正的匹配语义由 mihomo 实测。）
        groups = groups_of(convert())
        hk = re.compile(groups["🇭🇰 香港节点"]["filter"])
        self.assertIsNotNone(hk.search("[喵喵 - Lite] 🇭🇰 [CDN/0.2x] HK 电信"))
        self.assertIsNone(hk.search("[喵喵 - Lite] 🇯🇵 JP 流媒体 01"))
        self.assertIn("California", groups["🇺🇸 美国节点"]["filter"])
        self.assertTrue(groups["🇺🇸 美国节点"]["filter"].startswith("^(?!"))

    def test_streaming_filter_matches_name_only(self):
        config = provider_config()
        config.pop("proxy-providers")
        matching = ["🇯🇵日本-流媒体01", "🇺🇸美国-流媒体02", "流媒体"]
        config["proxies"] = [{"name": name} for name in matching + ["🇯🇵日本-普通03", "🇺🇸美国-普通04"]]
        groups = groups_of(convert(config))
        self.assertEqual(matching, groups[STREAMING_GROUP]["proxies"])
        self.assertNotIn("use", groups[STREAMING_GROUP])

    def test_taffy_group_takes_us_nodes_only(self):
        pattern = re.compile(transform_settings()["custom_groups"][1]["filter"])
        for name in TAFFY_US_NODES:
            self.assertIsNotNone(pattern.search(name), name)
        for name in TAFFY_OTHER_NODES:
            self.assertIsNone(pattern.search(name), name)

    def test_missing_provider_keeps_original_groups_untouched(self):
        # 订阅里没有塔菲订阅时，专属组不生成，也不得把所有分组的 provider 摘掉
        config = provider_config(providers=(OTHER_PROVIDER,))
        groups = groups_of(convert(config))
        self.assertNotIn(TAFFY_GROUP, groups)
        self.assertEqual([OTHER_PROVIDER], groups["🚀 手动选择"]["use"])
        self.assertNotIn(TAFFY_PROVIDER, groups["🚀 手动选择"]["use"])

    def test_repeated_conversion_is_idempotent(self):
        first = convert()
        self.assertEqual(first, convert(first))


if __name__ == "__main__":
    unittest.main()
