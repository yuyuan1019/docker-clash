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
        # YouTube 在豁免列表：保留 .* 节点列表，组内可直接选任意单个节点
        youtube = groups["📹 YouTube"]
        self.assertEqual(["机场A"], youtube["use"])
        self.assertEqual(".*", youtube["filter"])
        self.assertNotIn("exclude-filter", youtube)
        self.assertEqual(
            [
                "🚀 手动选择",
                "♻️ 自动选择",
                "🇸🇬 新加坡节点",
                "🏷️ CDN/低倍率节点",
            ],
            youtube["proxies"],
        )
        # 其他业务组：.* 节点列表被去掉，只留组引用；不用 exclude-filter
        github = groups["🐙 GitHub"]
        self.assertNotIn("use", github)
        self.assertNotIn("filter", github)
        self.assertNotIn("exclude-filter", github)
        self.assertEqual(
            [
                "🚀 手动选择",
                "♻️ 自动选择",
                "🇸🇬 新加坡节点",
                "🏷️ CDN/低倍率节点",
            ],
            github["proxies"],
        )
        # 豁免组：手动选择/自动选择/地区组保留节点列表，无 exclude-filter
        manual = groups["🚀 手动选择"]
        self.assertEqual(["机场A"], manual["use"])
        self.assertEqual(".*", manual["filter"])
        self.assertEqual(
            ["♻️ 自动选择", "🇭🇰 香港节点", "🏷️ CDN/低倍率节点"], manual["proxies"]
        )
        self.assertNotIn("exclude-filter", groups["♻️ 自动选择"])
        self.assertNotIn("exclude-filter", groups["🇭🇰 香港节点"])
        self.assertEqual("(?i)(香港|HK)", groups["🇭🇰 香港节点"]["filter"])
        # 纯节点组（无组引用）：exclude-filter 兑底
        self.assertEqual(
            CDN_SPEC["filter"], groups["🔎 纯节点组"].get("exclude-filter")
        )
        self.assertNotIn("exclude-filter", groups["🏷️ CDN/低倍率节点"])

        # 幂等：YouTube 保留节点列表，GitHub 仍去掉，纯节点组仍 exclude-filter 兑底
        append_custom_groups(config, [CDN_SPEC])
        self.assertEqual(["机场A"], groups["📹 YouTube"]["use"])
        self.assertNotIn("use", groups["🐙 GitHub"])
        self.assertEqual(
            CDN_SPEC["filter"], groups["🔎 纯节点组"].get("exclude-filter")
        )

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


if __name__ == "__main__":
    unittest.main()
