import os
import re
import tempfile
import unittest
from unittest.mock import patch

from app.api.custom_groups import append_custom_groups
from app.api.transform_config import (
    DEFAULT_CUSTOM_GROUPS,
    load_custom_groups,
)

CDN_SPEC = {
    "name": "CDN/低倍率节点",
    "filter": r"(?i)(?:cdn|低倍率|\b0(?:\.\d+)?\s*[x×倍]|[x×]\s*0(?:\.\d+)?\b)",
    "type": "select",
    "attach_to": ("🚀 手动选择",),
    "exclusive": True,
    "keep_in": ("♻️ 自动选择",),
}


class AppendCustomGroupsTest(unittest.TestCase):
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
                    "proxies": ["♻️ 自动选择", "🇭🇰 香港节点"],
                }
            ],
        }

        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        group = groups["CDN/低倍率节点"]
        self.assertEqual("select", group["type"])
        self.assertEqual(["机场A", "机场B"], group["use"])
        self.assertEqual(CDN_SPEC["filter"], group["filter"])
        self.assertNotIn("proxies", group)
        self.assertEqual(
            ["♻️ 自动选择", "🇭🇰 香港节点", "CDN/低倍率节点"],
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
                    "proxies": ["♻️ 自动选择", "香港 CDN 01", "日本 0.5x 02", "美国 普通节点"],
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
        # 手动选择：CDN 节点被剔除，但保留挂载的专属组引用
        self.assertEqual(
            ["♻️ 自动选择", "美国 普通节点", "CDN/低倍率节点"],
            groups["🚀 手动选择"]["proxies"],
        )
        # 自动选择在 keep_in 豁免列表，保留全部节点
        self.assertEqual(
            ["香港 CDN 01", "日本 0.5x 02", "美国 普通节点"],
            groups["♻️ 自动选择"]["proxies"],
        )
        # 业务组同样剔除了 CDN 节点
        self.assertEqual(
            ["🚀 手动选择", "美国 普通节点"], groups["📹 YouTube"]["proxies"]
        )

    def test_exclusive_adds_exclude_filter_to_provider_groups(self):
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "use": ["机场A"],
                    "proxies": ["♻️ 自动选择"],
                },
                {"name": "♻️ 自动选择", "type": "url-test", "use": ["机场A"]},
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "use": ["机场A"],
                    "filter": "(?i)(youtube|yt)",
                    "proxies": ["🚀 手动选择"],
                },
            ],
        }

        append_custom_groups(config, [CDN_SPEC])

        groups = {g["name"]: g for g in config["proxy-groups"]}
        for name in ("🚀 手动选择", "📹 YouTube"):
            self.assertEqual(CDN_SPEC["filter"], groups[name].get("exclude-filter"))
        self.assertNotIn("exclude-filter", groups["♻️ 自动选择"])
        self.assertNotIn("exclude-filter", groups["CDN/低倍率节点"])

        # 幂等：重复执行不会重复拼接 exclude-filter
        append_custom_groups(config, [CDN_SPEC])
        self.assertEqual(CDN_SPEC["filter"], groups["📹 YouTube"].get("exclude-filter"))

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
                {"name": "🚀 手动选择", "type": "select", "proxies": []},
                {"name": "📹 YouTube", "type": "select", "proxies": ["🚀 手动选择"]},
            ],
        }

        self.assertEqual(2, append_custom_groups(config, [CDN_SPEC, iplc_spec]))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        self.assertEqual("url-test", groups["IPLC 专线"]["type"])
        self.assertEqual(
            ["CDN/低倍率节点", "IPLC 专线"], groups["🚀 手动选择"]["proxies"]
        )
        self.assertEqual(
            ["🚀 手动选择", "IPLC 专线"], groups["📹 YouTube"]["proxies"]
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
                {"name": "🚀 手动选择", "type": "select", "proxies": ["♻️ 自动选择"]}
            ],
        }

        append_custom_groups(config, [CDN_SPEC])
        group_count = len(config["proxy-groups"])

        self.assertEqual(1, append_custom_groups(config, [CDN_SPEC]))
        self.assertEqual(group_count, len(config["proxy-groups"]))
        names = [g["name"] for g in config["proxy-groups"]]
        self.assertEqual(1, names.count("CDN/低倍率节点"))
        manual = next(g for g in config["proxy-groups"] if g["name"] == "🚀 手动选择")
        self.assertEqual(1, manual["proxies"].count("CDN/低倍率节点"))


class TransformConfigLoaderTest(unittest.TestCase):
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
            path=None, mtime=None, groups=transform_config.DEFAULT_CUSTOM_GROUPS
        )

    def write(self, text: str):
        with open(self.path, "w", encoding="utf-8") as file:
            file.write(text)
        os.utime(self.path)  # 确保 mtime 变化触发重载

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
