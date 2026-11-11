import os
import re
import tempfile
import time
import unittest
from unittest.mock import patch

from app.api.custom_groups import apply_group_defaults, append_custom_groups
from app.api.transform_config import (
    DEFAULT_CUSTOM_GROUPS,
    DEFAULT_GROUP_DEFAULTS,
    load_custom_groups,
    load_group_defaults,
)

CDN_SPEC = {
    "name": "🏷️ CDN/低倍率节点",
    "filter": r"(?i)(?:cdn|低倍率|\b0(?:\.\d+)?\s*[x×倍]|[x×]\s*0(?:\.\d+)?\b)",
    "type": "select",
    "attach_to": (),
    "attach_with": (
        "🇭🇰 香港节点",
        "🇺🇸 美国节点",
        "🇯🇵 日本节点",
        "🇸🇬 新加坡节点",
        "🇼🇸 台湾节点",
        "🇰🇷 韩国节点",
    ),
    "exclusive": True,
    "keep_in": (
        "♻️ 自动选择",
        "🚀 手动选择",
        "🐟 漏网之鱼",
        "📹 YouTube",
        "🇭🇰 香港节点",
        "🇺🇸 美国节点",
        "🇯🇵 日本节点",
        "🇸🇬 新加坡节点",
        "🇼🇸 台湾节点",
        "🇰🇷 韩国节点",
    ),
}


class AppendCustomGroupsTest(unittest.TestCase):
    def test_attach_with_inserts_after_region_anchors_in_business_groups(self):
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["♻️ 自动选择", "🇭🇰 香港节点", "🇺🇸 美国节点"],
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "proxies": [
                        "🚀 手动选择",
                        "♻️ 自动选择",
                        "🇭🇰 香港节点",
                        "🇺🇸 美国节点",
                        "🎯 全球直连",
                    ],
                },
                {
                    "name": "🐟 漏网之鱼",
                    "type": "select",
                    "proxies": ["🚀 手动选择", "♻️ 自动选择", "🎯 全球直连"],
                },
            ],
        }

        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        # 手动选择与业务组：紧跟最后一个地区组插入
        self.assertEqual(
            ["♻️ 自动选择", "🇭🇰 香港节点", "🇺🇸 美国节点", "🏷️ CDN/低倍率节点"],
            groups["🚀 手动选择"]["proxies"],
        )
        self.assertEqual(
            [
                "🚀 手动选择",
                "♻️ 自动选择",
                "🇭🇰 香港节点",
                "🇺🇸 美国节点",
                "🏷️ CDN/低倍率节点",
                "🎯 全球直连",
            ],
            groups["📹 YouTube"]["proxies"],
        )
        # 不含地区组的分组不受影响
        self.assertEqual(
            ["🚀 手动选择", "♻️ 自动选择", "🎯 全球直连"],
            groups["🐟 漏网之鱼"]["proxies"],
        )

    def test_provider_based_config_gets_filter_group(self):
        config = {
            "proxy-providers": {
                "机场A": {"type": "http", "url": "https://a.invalid/sub"},
                "机场B": {"type": "http", "url": "https://b.invalid/sub"},
            },
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["♻️ 自动选择", "🇭🇰 香港节点", "🇺🇸 美国节点"],
                }
            ],
        }

        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        group = groups["🏷️ CDN/低倍率节点"]
        self.assertEqual("select", group["type"])
        self.assertEqual(["机场A", "机场B"], group["use"])
        self.assertEqual(CDN_SPEC["filter"], group["filter"])
        self.assertNotIn("proxies", group)
        self.assertEqual(
            ["♻️ 自动选择", "🇭🇰 香港节点", "🇺🇸 美国节点", "🏷️ CDN/低倍率节点"],
            groups["🚀 手动选择"]["proxies"],
        )

    def test_static_proxies_are_matched_case_insensitively(self):
        config = {
            "proxies": [
                {"name": "香港 cdn 01"},
                {"name": "日本 低倍率 02"},
                {"name": "美国 普通节点"},
            ],
            "proxy-groups": [],
        }

        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))

        group = config["proxy-groups"][0]
        self.assertEqual(["香港 cdn 01", "日本 低倍率 02"], group["proxies"])
        self.assertNotIn("use", group)
        self.assertNotIn("filter", group)

    def test_low_rate_multiplier_names_are_matched(self):
        matched = ["香港 0.5x", "JP x0.25", "SG 0.1X", "US 0.3倍", "台湾 CDN"]
        unmatched = ["HK 1x", "JP 2倍", "美国 10.5x", "普通节点", "SG x2"]
        pattern = re.compile(CDN_SPEC["filter"])
        for name in matched:
            self.assertTrue(pattern.search(name), name)
        for name in unmatched:
            self.assertFalse(pattern.search(name), name)

    def test_exclusive_removes_static_matches_from_other_groups(self):
        config = {
            "proxies": [
                {"name": "香港 CDN 01"},
                {"name": "日本 0.5x 02"},
                {"name": "美国 普通节点"},
            ],
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["♻️ 自动选择", "🇭🇰 香港节点", "香港 CDN 01", "日本 0.5x 02", "美国 普通节点"],
                },
                {
                    "name": "♻️ 自动选择",
                    "type": "url-test",
                    "proxies": ["香港 CDN 01", "日本 0.5x 02", "美国 普通节点"],
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "proxies": ["🚀 手动选择", "香港 CDN 01", "美国 普通节点"],
                },
            ],
        }

        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        # 手动选择在豁免列表：保留全部节点，专属组紧跟地区组插入
        self.assertEqual(
            [
                "♻️ 自动选择",
                "🇭🇰 香港节点",
                "🏷️ CDN/低倍率节点",
                "香港 CDN 01",
                "日本 0.5x 02",
                "美国 普通节点",
            ],
            groups["🚀 手动选择"]["proxies"],
        )
        # 自动选择在豁免列表，保留全部节点
        self.assertEqual(
            ["香港 CDN 01", "日本 0.5x 02", "美国 普通节点"],
            groups["♻️ 自动选择"]["proxies"],
        )
        # YouTube 在豁免列表：保留全部节点（含单个 CDN 节点，可直接选任意节点）
        self.assertEqual(
            ["🚀 手动选择", "香港 CDN 01", "美国 普通节点"],
            groups["📹 YouTube"]["proxies"],
        )

    def test_exclusive_keeps_youtube_node_list_drops_other_business_groups(self):
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": ".*",
                    "proxies": ["♻️ 自动选择", "🇭🇰 香港节点"],
                },
                {"name": "♻️ 自动选择", "type": "url-test", "use": ["机场A"]},
                {
                    "name": "🇭🇰 香港节点",
                    "type": "url-test",
                    "use": ["机场A"],
                    "filter": "(?i)(香港|HK)",
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": ".*",
                    "proxies": ["🚀 手动选择", "♻️ 自动选择", "🇸🇬 新加坡节点"],
                },
                {
                    "name": "🐙 GitHub",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": ".*",
                    "proxies": ["🚀 手动选择", "♻️ 自动选择", "🇸🇬 新加坡节点"],
                },
                {
                    "name": "🔎 纯节点组",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": ".*",
                },
            ],
        }

        append_custom_groups(config, [CDN_SPEC])

        groups = {g["name"]: g for g in config["proxy-groups"]}
        # 豁免组（keep_in）：节点来源与过滤条件都不动
        manual = groups["🚀 手动选择"]
        self.assertEqual(["机场A"], manual["use"])
        self.assertEqual(".*", manual["filter"])
        self.assertEqual(
            ["♻️ 自动选择", "🇭🇰 香港节点", "🏷️ CDN/低倍率节点"], manual["proxies"]
        )
        self.assertNotIn("exclude-filter", groups["♻️ 自动选择"])
        self.assertEqual("(?i)(香港|HK)", groups["🇭🇰 香港节点"]["filter"])
        youtube = groups["📹 YouTube"]
        self.assertEqual(["机场A"], youtube["use"])
        self.assertEqual(".*", youtube["filter"])
        self.assertEqual(
            [
                "🚀 手动选择",
                "♻️ 自动选择",
                "🇸🇬 新加坡节点",
                "🏷️ CDN/低倍率节点",
            ],
            youtube["proxies"],
        )

        # 非豁免组：provider 节点来源保留，用 filter 负向前瞻隐藏匹配节点
        # （exclude-filter 会连显式成员一起过滤，把挂进去的专属组也滤掉）
        for name in ("🐙 GitHub", "🔎 纯节点组"):
            with self.subTest(group=name):
                group = groups[name]
                self.assertEqual(["机场A"], group["use"])
                self.assertNotIn("exclude-filter", group)
                self.assertTrue(group["filter"].startswith("^(?!"), group["filter"])
                # 原 filter 必须保留下来（开头 (?i) 会转成作用域写法 (?i:...)）
                self.assertIn("(?:cdn|低倍率|", group["filter"])
                self.assertTrue(group["filter"].endswith(".*"), group["filter"])
        # 有组引用的组：成员引用原样保留（专属组不会被自己滤掉），
        # 且仍按 attach_with 地区锚点插入（新加坡节点在锚点表内）
        self.assertEqual(
            ["🚀 手动选择", "♻️ 自动选择", "🇸🇬 新加坡节点", "🏷️ CDN/低倍率节点"],
            groups["🐙 GitHub"]["proxies"],
        )
        # 纯节点组：没有显式成员列表
        self.assertNotIn("proxies", groups["🔎 纯节点组"])

        # 幂等：重复调用不重复插入、不重复叠加负向前瞻
        append_custom_groups(config, [CDN_SPEC])
        self.assertEqual(1, groups["📹 YouTube"]["proxies"].count("🏷️ CDN/低倍率节点"))
        self.assertTrue(groups["🐙 GitHub"]["filter"].startswith("^(?!"))
        self.assertEqual(
            1, groups["🐙 GitHub"]["filter"].count("^(?!"), groups["🐙 GitHub"]["filter"]
        )

    def test_exclusive_keeps_original_filter_matching_anywhere(self):
        # 回归：机场节点会带 [提供商] 前缀（同源多账号时由 addprovide 前缀生成），
        # 地区组的 filter 必须仍能匹配任意位置；只用 ^ 锚定前瞻会把这些节点全部滤掉。
        streaming = {
            "name": "流媒体节点",
            "filter": "流媒体",
            "type": "url-test",
            "exclusive": True,
        }
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {
                    "name": "🇭🇰 香港节点",
                    "type": "url-test",
                    "use": ["机场A"],
                    "filter": "(?i)(香港|HK)",
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": ".*",
                    "proxies": [],
                },
            ],
        }

        append_custom_groups(config, [streaming], template_name="")

        groups = {g["name"]: g for g in config["proxy-groups"]}
        region = re.compile(groups["🇭🇰 香港节点"]["filter"])
        self.assertIsNotNone(region.search("🇭🇰 香港 普通 01"))
        self.assertIsNotNone(region.search("[喵喵 - Lite] 🇭🇰 [CDN/0.2x] HK 电信"))
        self.assertIsNone(region.search("[喵喵 - Lite] 🇭🇰 HK 流媒体 01"))
        self.assertIsNone(region.search("🇺🇸 美国 普通 02"))
        # .* 组保持简单形式，行为不变
        self.assertEqual("^(?!.*(?:(?:流媒体))).*", groups["📹 YouTube"]["filter"])
        self.assertIsNone(re.compile(groups["📹 YouTube"]["filter"]).search("🇭🇰 香港 流媒体 01"))

    def test_multiple_groups_and_attach_targets(self):
        iplc_spec = {
            "name": "IPLC 专线",
            "filter": "(?i)(iplc|专线)",
            "type": "url-test",
            "attach_to": ("🚀 手动选择", "📹 YouTube"),
        }
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {"name": "🚀 手动选择", "type": "select", "proxies": ["🇭🇰 香港节点"]},
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "proxies": ["🚀 手动选择", "🇭🇰 香港节点"],
                },
            ],
        }

        self.assertEqual(2, append_custom_groups(config, [CDN_SPEC, iplc_spec]))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertEqual("url-test", groups["IPLC 专线"]["type"])
        # CDN 走锚点紧跟地区组；IPLC 走 attach_to 追加末尾
        self.assertEqual(
            ["🇭🇰 香港节点", "🏷️ CDN/低倍率节点", "IPLC 专线"],
            groups["🚀 手动选择"]["proxies"],
        )
        self.assertEqual(
            ["🚀 手动选择", "🇭🇰 香港节点", "🏷️ CDN/低倍率节点", "IPLC 专线"],
            groups["📹 YouTube"]["proxies"],
        )

    def test_attach_after_places_group_after_anchor_in_targets_only(self):
        # attach_after：仅对 attach_to 目标组生效，紧跟锚点成员插入
        # （默认项置顶后即第二顺位）；无锚点的目标组退化为追加末尾；
        # 非目标组即使含锚点也不处理。
        streaming_spec = {
            "name": "🎬 流媒体",
            "filter": "流媒体",
            "type": "select",
            "attach_to": ("📹 YouTube", "🎶 TikTok", "📺 Bahamut"),
            "attach_with": (),
            "attach_after": "🇺🇸 美国节点",
            "exclusive": False,
            "keep_in": (),
        }
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": ".*",
                    "proxies": ["🇺🇸 美国节点", "🚀 手动选择", "♻️ 自动选择"],
                },
                {
                    "name": "🎶 TikTok",
                    "type": "select",
                    "proxies": ["🚀 手动选择", "🇺🇸 美国节点", "♻️ 自动选择"],
                },
                {
                    "name": "📺 Bahamut",
                    "type": "select",
                    "proxies": ["🇼🇸 台湾节点", "🚀 手动选择", "🎯 全球直连"],
                },
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["🇺🇸 美国节点", "♻️ 自动选择"],
                },
                {
                    "name": "🇺🇸 美国节点",
                    "type": "url-test",
                    "use": ["机场A"],
                    "filter": "(?i)(美国|US)",
                },
            ],
        }

        self.assertEqual(1, append_custom_groups(config, [streaming_spec]))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        # YouTube：紧跟美国节点 → 第二顺位
        self.assertEqual(
            ["🇺🇸 美国节点", "🎬 流媒体", "🚀 手动选择", "♻️ 自动选择"],
            groups["📹 YouTube"]["proxies"],
        )
        # TikTok：紧跟美国节点
        self.assertEqual(
            ["🚀 手动选择", "🇺🇸 美国节点", "🎬 流媒体", "♻️ 自动选择"],
            groups["🎶 TikTok"]["proxies"],
        )
        # Bahamut：无美国节点 → 追加末尾
        self.assertEqual(
            ["🇼🇸 台湾节点", "🚀 手动选择", "🎯 全球直连", "🎬 流媒体"],
            groups["📺 Bahamut"]["proxies"],
        )
        # 非目标组（手动选择）即使含锚点也不插入
        self.assertEqual(
            ["🇺🇸 美国节点", "♻️ 自动选择"], groups["🚀 手动选择"]["proxies"]
        )
        # 幂等：重复调用不重复插入
        self.assertEqual(1, append_custom_groups(config, [streaming_spec]))
        self.assertEqual(1, groups["📹 YouTube"]["proxies"].count("🎬 流媒体"))

    def test_group_without_matching_source_is_skipped_and_not_attached(self):
        spec = {
            "name": "IPLC 专线",
            "filter": "(?i)iplc",
            "type": "select",
            "attach_to": ("🚀 手动选择",),
        }
        config = {
            "proxies": [{"name": "普通节点"}],
            "proxy-groups": [{"name": "🚀 手动选择", "type": "select", "proxies": []}],
        }

        self.assertEqual(0, append_custom_groups(config, [spec]))
        self.assertEqual(1, len(config["proxy-groups"]))
        self.assertEqual([], config["proxy-groups"][0]["proxies"])

    def test_is_idempotent(self):
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {"name": "🚀 手动选择", "type": "select", "proxies": ["♻️ 自动选择", "🇭🇰 香港节点"]}
            ],
        }

        append_custom_groups(config, [CDN_SPEC])
        group_count = len(config["proxy-groups"])

        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))
        self.assertEqual(group_count, len(config["proxy-groups"]))
        names = [g["name"] for g in config["proxy-groups"]]
        self.assertEqual(1, names.count("🏷️ CDN/低倍率节点"))
        manual = next(g for g in config["proxy-groups"] if g["name"] == "🚀 手动选择")
        self.assertEqual(1, manual["proxies"].count("🏷️ CDN/低倍率节点"))

    def test_exclusive_keeps_static_cdn_nodes_in_region_groups(self):
        config = {
            "proxies": [
                {"name": "香港 CDN 01"},
                {"name": "美国 0.5x 02"},
                {"name": "香港 普通节点"},
            ],
            "proxy-groups": [
                {
                    "name": "🇭🇰 香港节点",
                    "type": "url-test",
                    "proxies": ["香港 CDN 01", "香港 普通节点"],
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "proxies": ["香港 CDN 01", "美国 0.5x 02", "香港 普通节点"],
                },
            ],
        }

        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        # 地区组保留 CDN 节点（CDN 节点同时属于该地区）
        self.assertEqual(
            ["香港 CDN 01", "香港 普通节点"], groups["🇭🇰 香港节点"]["proxies"]
        )
        # YouTube 在豁免列表：保留全部节点，可直接选任意单个节点
        self.assertEqual(
            ["香港 CDN 01", "美国 0.5x 02", "香港 普通节点"],
            groups["📹 YouTube"]["proxies"],
        )


class AttachIndexTest(unittest.TestCase):
    """attach_index：把自定义组钉在目标分组的指定顺位（与成员名无关）。"""

    def config(self):
        return {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": ".*",
                    "proxies": ["🚀 手动选择", "♻️ 自动选择", "🇭🇰 香港节点"],
                },
                {
                    "name": "📺 Bahamut",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": ".*",
                    "proxies": ["🇼🇸 台湾节点", "🇭🇰 香港节点", "🎯 全球直连"],
                },
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["♻️ 自动选择", "🇭🇰 香港节点"],
                },
            ],
        }

    def spec(self, **overrides):
        spec = {
            "name": "流媒体节点",
            "filter": "流媒体",
            "type": "url-test",
            "attach_index": 1,
            "attach_to": ("📹 YouTube", "📺 Bahamut"),
        }
        spec.update(overrides)
        return spec

    def test_inserts_at_second_position_regardless_of_first_member(self):
        config = self.config()
        self.assertEqual(1, append_custom_groups(config, [self.spec()]))
        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertEqual(
            ["🚀 手动选择", "流媒体节点", "♻️ 自动选择", "🇭🇰 香港节点"],
            groups["📹 YouTube"]["proxies"],
        )
        # Bahamut 首位不是手动选择，仍然固定在第二顺位
        self.assertEqual(
            ["🇼🇸 台湾节点", "流媒体节点", "🇭🇰 香港节点", "🎯 全球直连"],
            groups["📺 Bahamut"]["proxies"],
        )
        # 非目标组不受影响
        self.assertEqual(
            ["♻️ 自动选择", "🇭🇰 香港节点"], groups["🚀 手动选择"]["proxies"]
        )

    def test_idempotent_and_repositions_when_needed(self):
        config = self.config()
        append_custom_groups(config, [self.spec()])
        # 第二次调用不重复插入
        self.assertEqual(1, append_custom_groups(config, [self.spec()]))
        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertEqual(1, groups["📹 YouTube"]["proxies"].count("流媒体节点"))
        # 已存在于首位（例如被 group_defaults 提前置顶）时移回第二顺位
        groups["📹 YouTube"]["proxies"].remove("流媒体节点")
        groups["📹 YouTube"]["proxies"].insert(0, "流媒体节点")
        append_custom_groups(config, [self.spec()])
        self.assertEqual(1, groups["📹 YouTube"]["proxies"].index("流媒体节点"))

    def test_index_beyond_length_appends_at_tail(self):
        config = self.config()
        append_custom_groups(config, [self.spec(attach_index=99)])
        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertEqual("流媒体节点", groups["📹 YouTube"]["proxies"][-1])


class ProbeSettingsTest(unittest.TestCase):
    """url / interval / tolerance 写进自定义组，不依赖引擎默认值。"""

    def config(self):
        return {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {"name": "📹 YouTube", "type": "select", "proxies": ["🚀 手动选择"]},
            ],
        }

    def test_sets_probe_fields_and_is_idempotent(self):
        spec = {
            "name": "测速组",
            "filter": "(?i)us",
            "type": "url-test",
            "url": "https://www.gstatic.com/generate_204",
            "interval": 300,
            "tolerance": 50,
            "attach_to": ("📹 YouTube",),
        }
        config = self.config()
        append_custom_groups(config, [spec])
        group = next(g for g in config["proxy-groups"] if g["name"] == "测速组")
        self.assertEqual("url-test", group["type"])
        self.assertEqual("https://www.gstatic.com/generate_204", group["url"])
        self.assertEqual(300, group["interval"])
        self.assertEqual(50, group["tolerance"])
        # 重复应用不重复写入
        append_custom_groups(config, [spec])
        self.assertEqual(300, group["interval"])

    def test_omitted_probe_fields_are_cleared(self):
        spec = {"name": "测速组", "filter": "(?i)us", "type": "select"}
        config = self.config()
        config["proxy-groups"].append(
            {"name": "测速组", "type": "url-test", "url": "https://x.invalid", "interval": 60}
        )
        append_custom_groups(config, [spec])
        group = next(g for g in config["proxy-groups"] if g["name"] == "测速组")
        self.assertNotIn("url", group)
        self.assertNotIn("interval", group)
        self.assertNotIn("tolerance", group)


class ProviderScopeTest(unittest.TestCase):
    """providers / exclude_providers / exclusive_providers：订阅级节点范围控制。"""

    def base_config(self):
        return {
            "proxy-providers": {
                "机场A": {"type": "http", "url": "https://a.invalid/sub"},
                "塔菲": {"type": "http", "url": "https://t.invalid/sub"},
            },
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "use": ["机场A", "塔菲"],
                    "filter": ".*",
                    "proxies": ["♻️ 自动选择", "🇺🇸 美国节点"],
                },
                {
                    "name": "♻️ 自动选择",
                    "type": "url-test",
                    "use": ["机场A", "塔菲"],
                    "filter": ".*",
                },
                {
                    "name": "🤖 ChatGPT",
                    "type": "select",
                    "use": ["机场A", "塔菲"],
                    "filter": ".*",
                    "proxies": ["🚀 手动选择", "🇺🇸 美国节点"],
                },
                {
                    "name": "🇺🇸 美国节点",
                    "type": "url-test",
                    "use": ["机场A", "塔菲"],
                    "filter": "(?i)(美国|US)",
                },
            ],
        }

    def spec(self, **overrides):
        spec = {
            "name": "塔菲美国节点",
            "filter": "(?i)(美国|US)",
            "type": "select",
            "providers": ("塔菲",),
            "exclusive_providers": ("塔菲",),
            "attach_to": ("🤖 ChatGPT",),
        }
        spec.update(overrides)
        return spec

    def test_providers_whitelist_limits_group_source(self):
        config = self.base_config()
        self.assertEqual(1, append_custom_groups(config, [self.spec()]))
        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertEqual(["塔菲"], groups["塔菲美国节点"]["use"])
        self.assertEqual("(?i)(美国|US)", groups["塔菲美国节点"]["filter"])

    def test_exclude_providers_removes_source_from_group(self):
        config = self.base_config()
        spec = {
            "name": "流媒体节点",
            "filter": "流媒体",
            "type": "url-test",
            "exclude_providers": ("塔菲",),
        }
        self.assertEqual(1, append_custom_groups(config, [spec]))
        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertEqual(["机场A"], groups["流媒体节点"]["use"])

    def test_exclusive_providers_is_removed_from_every_other_group(self):
        config = self.base_config()
        self.assertEqual(1, append_custom_groups(config, [self.spec()]))
        groups = {g["name"]: g for g in config["proxy-groups"]}
        # 专属组保留该订阅
        self.assertEqual(["塔菲"], groups["塔菲美国节点"]["use"])
        # 其它分组（含地区组、自动选择）都不再挂它
        for name in ("🚀 手动选择", "♻️ 自动选择", "🤖 ChatGPT", "🇺🇸 美国节点"):
            with self.subTest(group=name):
                self.assertEqual(["机场A"], groups[name]["use"])
        # 专属组名只出现在 attach 目标里
        self.assertIn("塔菲美国节点", groups["🤖 ChatGPT"]["proxies"])
        self.assertNotIn("塔菲美国节点", groups["🚀 手动选择"]["proxies"])

    def test_exclusive_providers_keeps_sources_in_keep_in_groups(self):
        config = self.base_config()
        spec = self.spec(keep_in=("🇺🇸 美国节点",))
        append_custom_groups(config, [spec])
        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertEqual(["机场A", "塔菲"], groups["🇺🇸 美国节点"]["use"])
        self.assertEqual(["机场A"], groups["🚀 手动选择"]["use"])

    def test_exclusive_providers_falls_back_to_direct_when_use_empties(self):
        config = {
            "proxy-providers": {"塔菲": {"type": "http", "url": "https://t.invalid/sub"}},
            "proxy-groups": [
                {
                    "name": "♻️ 自动选择",
                    "type": "url-test",
                    "use": ["塔菲"],
                    "filter": ".*",
                },
                {
                    "name": "🤖 ChatGPT",
                    "type": "select",
                    "use": ["塔菲"],
                    "filter": ".*",
                    "proxies": ["♻️ 自动选择"],
                },
            ],
        }
        append_custom_groups(config, [self.spec()])
        groups = {g["name"]: g for g in config["proxy-groups"]}
        auto = groups["♻️ 自动选择"]
        self.assertNotIn("use", auto)
        self.assertNotIn("filter", auto)
        self.assertEqual(["DIRECT"], auto["proxies"])
        # 有组引用的组只丢 use/filter，组引用与挂入的专属组保留
        self.assertEqual(
            ["♻️ 自动选择", "塔菲美国节点"], groups["🤖 ChatGPT"]["proxies"]
        )

    def test_exclusive_providers_skipped_when_group_not_created(self):
        config = self.base_config()
        config["proxy-providers"].pop("塔菲")
        spec = self.spec(providers=("不存在的订阅",), exclusive_providers=("机场A",))
        self.assertEqual(0, append_custom_groups(config, [spec]))
        groups = {g["name"]: g for g in config["proxy-groups"]}
        # 专属组没建成，绝不能把 provider 从其它分组摘掉
        self.assertEqual(["机场A", "塔菲"], groups["🚀 手动选择"]["use"])


class GroupDefaultsTest(unittest.TestCase):
    def test_moves_existing_member_to_front(self):
        config = {
            "proxy-groups": [
                {
                    "name": "🔀 非标端口",
                    "type": "select",
                    "proxies": ["🐟 漏网之鱼", "🎯 全球直连"],
                }
            ]
        }

        changed = apply_group_defaults(
            config, [{"group": "🔀 非标端口", "default": "🎯 全球直连"}]
        )

        self.assertEqual(1, changed)
        self.assertEqual(
            ["🎯 全球直连", "🐟 漏网之鱼"], config["proxy-groups"][0]["proxies"]
        )

    def test_inserts_missing_member_and_is_idempotent(self):
        # 目标组已在配置中定义（append_custom_groups 先于 apply_group_defaults）
        config = {
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["♻️ 自动选择", "🇭🇰 香港节点"],
                },
                {"name": "🏷️ CDN/低倍率节点", "type": "select", "proxies": []},
            ]
        }
        defaults = [{"group": "🚀 手动选择", "default": "🏷️ CDN/低倍率节点"}]

        self.assertEqual(1, apply_group_defaults(config, defaults))
        self.assertEqual(
            ["🏷️ CDN/低倍率节点", "♻️ 自动选择", "🇭🇰 香港节点"],
            config["proxy-groups"][0]["proxies"],
        )
        self.assertEqual(0, apply_group_defaults(config, defaults))

    def test_dangling_reference_is_skipped(self):
        # 回归：远程配置拉取异常时 subconverter 可能生成分组缺失的降级配置，
        # 默认项指向不存在的组时不得插入悬空引用（会导致 mihomo 解析失败）
        config = {
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["♻️ 自动选择"],
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "proxies": ["♻️ 自动选择", "🚀 手动选择"],
                },
                {"name": "♻️ 自动选择", "type": "url-test", "use": ["机场A"]},
            ]
        }
        defaults = [
            {"group": "🚀 手动选择", "default": "🇭🇰 香港节点"},  # 不存在：跳过
            {"group": "📹 YouTube", "default": "🚀 手动选择"},  # 存在：置顶
        ]

        self.assertEqual(1, apply_group_defaults(config, defaults))
        # 手动选择未被插入不存在的香港节点
        self.assertEqual(
            ["♻️ 自动选择"], config["proxy-groups"][0]["proxies"]
        )
        # YouTube 的手动选择被置顶
        self.assertEqual(
            ["🚀 手动选择", "♻️ 自动选择"], config["proxy-groups"][1]["proxies"]
        )

    def test_missing_group_or_without_proxies_is_skipped(self):
        config = {
            "proxy-groups": [
                {"name": "♻️ 自动选择", "type": "url-test", "use": ["机场A"]},
            ]
        }
        defaults = [
            {"group": "不存在", "default": "🎯 全球直连"},
            {"group": "♻️ 自动选择", "default": "🇭🇰 香港节点"},
        ]

        self.assertEqual(0, apply_group_defaults(config, defaults))

    def test_full_flow_with_cocr_composition(self):
        # 按 COCR Custom_Clash.ini 的真实成员结构建模
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["♻️ 自动选择", "🇭🇰 香港节点", "🇺🇸 美国节点"],
                },
                {
                    "name": "📢 谷歌FCM",
                    "type": "select",
                    "proxies": ["🚀 手动选择", "♻️ 自动选择", "🇭🇰 香港节点", "🇼🇸 台湾节点"],
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "proxies": [
                        "🚀 手动选择",
                        "♻️ 自动选择",
                        "🇭🇰 香港节点",
                        "🇺🇸 美国节点",
                        "🎯 全球直连",
                    ],
                    "use": ["机场A"],
                },
                {
                    "name": "🐟 漏网之鱼",
                    "type": "select",
                    "proxies": [
                        "🚀 手动选择",
                        "♻️ 自动选择",
                        "🎯 全球直连",
                        "🇭🇰 香港节点",
                        "🇰🇷 韩国节点",
                    ],
                    "use": ["机场A"],
                },
                {
                    "name": "🔀 非标端口",
                    "type": "select",
                    "proxies": ["🐟 漏网之鱼", "🎯 全球直连"],
                },
            ],
        }

        # 内置默认已置空（不调整任何分组）；这里显式传入默认项验证机制
        explicit_defaults = (
            {"group": "🚀 手动选择", "default": "🇭🇰 香港节点"},
            {"group": "📢 谷歌FCM", "default": "🇭🇰 香港节点"},
            {"group": "📹 YouTube", "default": "🚀 手动选择"},
            {"group": "🔀 非标端口", "default": "🎯 全球直连"},
        )
        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))
        self.assertEqual(3, apply_group_defaults(config, explicit_defaults))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        # 手动选择：香港节点置顶
        self.assertEqual(
            ["🇭🇰 香港节点", "♻️ 自动选择", "🇺🇸 美国节点", "🏷️ CDN/低倍率节点"],
            groups["🚀 手动选择"]["proxies"],
        )
        # 谷歌FCM：香港节点置顶（CDN 组经地区锚点挂在末尾）
        self.assertEqual(
            ["🇭🇰 香港节点", "🚀 手动选择", "♻️ 自动选择", "🇼🇸 台湾节点", "🏷️ CDN/低倍率节点"],
            groups["📢 谷歌FCM"]["proxies"],
        )
        # YouTube：默认已指向手动选择（本就首项，不变）；在豁免列表，保留 use 全量节点（可选任意节点）
        self.assertEqual(["机场A"], groups["📹 YouTube"]["use"])
        self.assertEqual(
            ["🚀 手动选择", "♻️ 自动选择", "🇭🇰 香港节点", "🇺🇸 美国节点", "🏷️ CDN/低倍率节点", "🎯 全球直连"],
            groups["📹 YouTube"]["proxies"],
        )
        # 漏网之鱼：CDN 组已通过地区组锚点挂入（非默认项，不置顶）
        self.assertEqual(
            [
                "🚀 手动选择",
                "♻️ 自动选择",
                "🎯 全球直连",
                "🇭🇰 香港节点",
                "🇰🇷 韩国节点",
                "🏷️ CDN/低倍率节点",
            ],
            groups["🐟 漏网之鱼"]["proxies"],
        )
        # 非标端口：全球直连置顶
        self.assertEqual(
            ["🎯 全球直连", "🐟 漏网之鱼"],
            groups["🔀 非标端口"]["proxies"],
        )
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        self.addCleanup(self._remove_tmp)
        self.addCleanup(self._reset_cache)

    def _remove_tmp(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    @staticmethod
    def _reset_cache():
        from app.api import transform_config

        transform_config._cache.update(
            path=None,
            mtime=None,
            groups=transform_config.DEFAULT_CUSTOM_GROUPS,
            defaults=transform_config.DEFAULT_GROUP_DEFAULTS,
        )

    def write(self, text: str):
        with open(self.path, "w", encoding="utf-8") as file:
            file.write(text)
        # 强制 mtime 严格递增：部分文件系统 mtime 精度较粗（同一秒内两次写入
        # 可能得到相同 mtime），热加载会误判为未变更
        self._tick = getattr(self, "_tick", 0) + 1
        t = time.time() + self._tick
        os.utime(self.path, (t, t))

    def test_loads_group_defaults_from_file(self):
        self.write(
            'custom_groups: []\n'
            'group_defaults:\n'
            '  - group: "🚀 手动选择"\n'
            '    default: "🇯🇵 日本节点"\n'
        )
        groups = load_custom_groups(self.path)
        defaults = load_group_defaults(self.path)
        self.assertEqual((), groups)
        self.assertEqual(
            ({"group": "🚀 手动选择", "default": "🇯🇵 日本节点"},), defaults
        )

    def test_missing_file_falls_back_to_defaults(self):
        with patch.dict(os.environ, {"TRANSFORM_CONFIG_FILE": "/nonexistent/x.yaml"}):
            self.assertEqual(DEFAULT_CUSTOM_GROUPS, load_custom_groups())

    def test_loads_custom_groups_from_file(self):
        self.write(
            'custom_groups:\n'
            '  - name: "IPLC 专线"\n'
            '    filter: "(?i)iplc"\n'
            '    attach_to: ["🚀 手动选择"]\n'
        )
        groups = load_custom_groups(self.path)
        self.assertEqual(1, len(groups))
        self.assertEqual("IPLC 专线", groups[0]["name"])
        self.assertEqual("select", groups[0]["type"])
        self.assertEqual(("🚀 手动选择",), groups[0]["attach_to"])

    def test_empty_list_disables_custom_groups(self):
        self.write("custom_groups: []\n")
        self.assertEqual((), load_custom_groups(self.path))

    def test_invalid_yaml_falls_back_to_defaults(self):
        self.write("custom_groups: [broken\n")
        self.assertEqual(DEFAULT_CUSTOM_GROUPS, load_custom_groups(self.path))

    def test_bad_entry_is_skipped_but_rest_kept(self):
        self.write(
            'custom_groups:\n'
            '  - name: "坏组"\n'
            '    filter: "((("\n'
            '  - name: "IPLC 专线"\n'
            '    filter: "(?i)iplc"\n'
        )
        groups = load_custom_groups(self.path)
        self.assertEqual(("IPLC 专线",), tuple(g["name"] for g in groups))

    def test_mtime_change_triggers_reload(self):
        self.write('custom_groups:\n  - name: "A组"\n    filter: "a"\n')
        self.assertEqual("A组", load_custom_groups(self.path)[0]["name"])
        self.write('custom_groups:\n  - name: "B组"\n    filter: "b"\n')
        self.assertEqual("B组", load_custom_groups(self.path)[0]["name"])

    def test_append_uses_loader_result(self):
        self.write(
            'custom_groups:\n'
            '  - name: "IPLC 专线"\n'
            '    filter: "(?i)iplc"\n'
            '    attach_to: ["🚀 手动选择"]\n'
        )
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [{"name": "🚀 手动选择", "type": "select", "proxies": []}],
        }
        with patch.dict(os.environ, {"TRANSFORM_CONFIG_FILE": self.path}):
            self.assertEqual(1, append_custom_groups(config))
        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertIn("IPLC 专线", groups)
        self.assertEqual(["IPLC 专线"], groups["🚀 手动选择"]["proxies"])

    def test_service_policy_group_defaults(self):
        defaults = (
            {"group": "💬 即时通讯", "default": "🇭🇰 香港节点"},
            {"group": "🌐 社交媒体", "default": "🇭🇰 香港节点"},
            {"group": "🚀 GitHub", "default": "🇭🇰 香港节点"},
            {"group": "🎮 Steam", "default": "🎯 全球直连"},
            {"group": "🎮 游戏平台", "default": "🎯 全球直连"},
            {"group": "📢 谷歌FCM", "default": "🇸🇬 新加坡节点"},
            {"group": "🇬 谷歌服务", "default": "🇺🇸 美国节点"},
            {"group": "🤖 ChatGPT", "default": "🇺🇸 美国节点"},
            {"group": "🤖 AI服务", "default": "🇯🇵 日本节点"},
            {"group": "🤖 国外AI服务", "default": "🇯🇵 日本节点"},
            {"group": "🍎 苹果服务", "default": "🇺🇸 美国节点"},
            {"group": "Ⓜ️ 微软服务", "default": "🇺🇸 美国节点"},
            {"group": "🚀 测速工具", "default": "🚀 手动选择"},
            {"group": "🐟 漏网之鱼", "default": "🚀 手动选择"},
        )
        config = {
            "proxy-groups": [
                {"name": "🚀 手动选择", "type": "select", "proxies": ["🇭🇰 香港节点", "🇸🇬 新加坡节点", "🇺🇸 美国节点"]},
                {"name": "🇭🇰 香港节点", "type": "select", "proxies": ["hk1"]},
                {"name": "🇸🇬 新加坡节点", "type": "select", "proxies": ["sg1"]},
                {"name": "🇺🇸 美国节点", "type": "select", "proxies": ["us1"]},
                {"name": "🎯 全球直连", "type": "select", "proxies": ["DIRECT"]},
                {"name": "💬 即时通讯", "type": "select", "proxies": ["🚀 手动选择", "🇭🇰 香港节点"]},
                {"name": "🌐 社交媒体", "type": "select", "proxies": ["🚀 手动选择", "🇭🇰 香港节点"]},
                {"name": "🚀 GitHub", "type": "select", "proxies": ["🚀 手动选择", "🇭🇰 香港节点"]},
                {"name": "🎮 Steam", "type": "select", "proxies": ["🚀 手动选择", "🎯 全球直连"]},
                {"name": "🎮 游戏平台", "type": "select", "proxies": ["🚀 手动选择", "🎯 全球直连"]},
                {"name": "📢 谷歌FCM", "type": "select", "proxies": ["🚀 手动选择", "🇸🇬 新加坡节点"]},
                {"name": "🇬 谷歌服务", "type": "select", "proxies": ["🚀 手动选择", "🇺🇸 美国节点"]},
                {"name": "🤖 ChatGPT", "type": "select", "proxies": ["🚀 手动选择", "🇺🇸 美国节点"]},
                {"name": "🤖 AI服务", "type": "select", "proxies": ["🚀 手动选择", "🇯🇵 日本节点"]},
                {"name": "🤖 国外AI服务", "type": "select", "proxies": ["🚀 手动选择", "🇯🇵 日本节点"]},
                {"name": "🍎 苹果服务", "type": "select", "proxies": ["🚀 手动选择", "🇺🇸 美国节点"]},
                {"name": "Ⓜ️ 微软服务", "type": "select", "proxies": ["🚀 手动选择", "🇺🇸 美国节点"]},
                {"name": "🚀 测速工具", "type": "select", "proxies": ["🎯 全球直连", "🚀 手动选择"]},
                {"name": "🐟 漏网之鱼", "type": "select", "proxies": ["🎯 全球直连", "🚀 手动选择"]},
            ]
        }
        changed = apply_group_defaults(config, defaults)
        self.assertEqual(14, changed)
        by_name = {g["name"]: g["proxies"][0] for g in config["proxy-groups"]}
        self.assertEqual("🇭🇰 香港节点", by_name["💬 即时通讯"])
        self.assertEqual("🇭🇰 香港节点", by_name["🌐 社交媒体"])
        self.assertEqual("🇭🇰 香港节点", by_name["🚀 GitHub"])
        self.assertEqual("🎯 全球直连", by_name["🎮 Steam"])
        self.assertEqual("🎯 全球直连", by_name["🎮 游戏平台"])
        self.assertEqual("🇸🇬 新加坡节点", by_name["📢 谷歌FCM"])
        self.assertEqual("🇺🇸 美国节点", by_name["🇬 谷歌服务"])
        self.assertEqual("🇺🇸 美国节点", by_name["🤖 ChatGPT"])
        self.assertEqual("🇯🇵 日本节点", by_name["🤖 AI服务"])
        self.assertEqual("🇯🇵 日本节点", by_name["🤖 国外AI服务"])
        self.assertEqual("🇺🇸 美国节点", by_name["🍎 苹果服务"])
        self.assertEqual("🇺🇸 美国节点", by_name["Ⓜ️ 微软服务"])
        self.assertEqual("🚀 手动选择", by_name["🚀 测速工具"])
        self.assertEqual("🚀 手动选择", by_name["🐟 漏网之鱼"])


if __name__ == "__main__":
    unittest.main()
