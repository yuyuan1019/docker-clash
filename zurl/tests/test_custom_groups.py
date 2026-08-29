import unittest

from app.api.custom_groups import (
    CDN_LOW_RATE_FILTER,
    CDN_LOW_RATE_GROUP_NAME,
    append_cdn_low_rate_group,
)


class CdnLowRateGroupTest(unittest.TestCase):
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

        self.assertTrue(append_cdn_low_rate_group(config))

        groups = {g["name"]: g for g in config["proxy-groups"]}
        group = groups[CDN_LOW_RATE_GROUP_NAME]
        self.assertEqual("select", group["type"])
        self.assertEqual(["机场A", "机场B"], group["use"])
        self.assertEqual(CDN_LOW_RATE_FILTER, group["filter"])
        self.assertNotIn("proxies", group)
        self.assertEqual(
            ["♻️ 自动选择", "🇭🇰 香港节点", CDN_LOW_RATE_GROUP_NAME],
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

        self.assertTrue(append_cdn_low_rate_group(config))

        group = config["proxy-groups"][0]
        self.assertEqual(
            ["香港 cdn 01", "日本 低倍率 02"],
            group["proxies"],
        )
        self.assertNotIn("use", group)
        self.assertNotIn("filter", group)

    def test_mixed_sources_use_both_use_and_proxies(self):
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxies": [{"name": "静态 CDN 中转"}],
            "proxy-groups": [],
        }

        self.assertTrue(append_cdn_low_rate_group(config))

        group = config["proxy-groups"][0]
        self.assertEqual(["机场A"], group["use"])
        self.assertEqual(CDN_LOW_RATE_FILTER, group["filter"])
        self.assertEqual(["静态 CDN 中转"], group["proxies"])

    def test_no_matching_source_leaves_config_unchanged(self):
        config = {
            "proxies": [{"name": "美国 普通节点"}],
            "proxy-groups": [{"name": "🚀 手动选择", "type": "select", "proxies": []}],
        }

        self.assertFalse(append_cdn_low_rate_group(config))
        self.assertEqual(1, len(config["proxy-groups"]))

    def test_is_idempotent(self):
        config = {
            "proxy-providers": {"机场A": {"type": "http", "url": "https://a.invalid/sub"}},
            "proxy-groups": [
                {"name": "🚀 手动选择", "type": "select", "proxies": ["♻️ 自动选择"]}
            ],
        }

        append_cdn_low_rate_group(config)
        group_count = len(config["proxy-groups"])

        self.assertTrue(append_cdn_low_rate_group(config))
        self.assertEqual(group_count, len(config["proxy-groups"]))
        names = [g["name"] for g in config["proxy-groups"]]
        self.assertEqual(1, names.count(CDN_LOW_RATE_GROUP_NAME))
        manual = next(g for g in config["proxy-groups"] if g["name"] == "🚀 手动选择")
        self.assertEqual(
            1, manual["proxies"].count(CDN_LOW_RATE_GROUP_NAME)
        )


if __name__ == "__main__":
    unittest.main()
