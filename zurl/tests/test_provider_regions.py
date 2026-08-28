import unittest

from app.api.provider_regions import (
    REGION_GROUPS,
    expand_provider_region_groups,
    fix_region_name_compatibility,
    prefix_duplicate_provider_nodes,
)


def region_group(name, marker):
    return {
        "name": name,
        "type": "url-test",
        "use": ["A", "B"],
        "filter": marker,
        "url": "https://cp.cloudflare.com/generate_204",
        "interval": 300,
        "tolerance": 50,
    }


class ProviderRegionGroupsTest(unittest.TestCase):
    def build_config(self):
        region_groups = [
            region_group(name, f"filter-{index}")
            for index, (name, _, _) in enumerate(REGION_GROUPS)
        ]
        return {
            "proxy-providers": {
                "A": {"type": "http", "url": "https://a.invalid/sub"},
                "B": {"type": "http", "url": "https://b.invalid/sub"},
            },
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": [name for name, _, _ in REGION_GROUPS],
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "proxies": [
                        "🚀 手动选择",
                        *[name for name, _, _ in REGION_GROUPS],
                    ],
                },
                {
                    "name": "🐟 漏网之鱼",
                    "type": "select",
                    "proxies": [
                        "🚀 手动选择",
                        *[name for name, _, _ in REGION_GROUPS],
                    ],
                },
                *region_groups,
            ],
        }

    def test_adds_hong_kong_and_japan_for_each_provider(self):
        config = self.build_config()

        added = expand_provider_region_groups(config)

        self.assertEqual(4, added)
        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual(["A"], groups["🇭🇰 香港_A"]["use"])
        self.assertEqual(["B"], groups["🇭🇰 香港_B"]["use"])
        self.assertEqual("filter-0", groups["🇭🇰 香港_A"]["filter"])
        self.assertNotIn("proxies", groups["🇭🇰 香港_A"])

    def test_expands_selectable_groups_but_keeps_excluded_groups_unchanged(self):
        config = self.build_config()
        original_manual = list(config["proxy-groups"][0]["proxies"])

        expand_provider_region_groups(config)

        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual(
            [
                original_manual[0],
                "🇭🇰 香港_A",
                "🇭🇰 香港_B",
                original_manual[1],
                "🇯🇵 日本_A",
                "🇯🇵 日本_B",
            ],
            groups["🚀 手动选择"]["proxies"],
        )
        self.assertEqual(
            ["🚀 手动选择", *original_manual],
            groups["🐟 漏网之鱼"]["proxies"],
        )
        youtube = groups["📹 YouTube"]["proxies"]
        self.assertEqual(
            ["🇭🇰 香港节点", "🇭🇰 香港_A", "🇭🇰 香港_B"],
            youtube[1:4],
        )
        self.assertIn("🇯🇵 日本_A", youtube)
        self.assertIn("🇯🇵 日本_B", youtube)
        self.assertNotIn("🇼🇸 台湾_A", youtube)

    def test_gfw_variant_without_base_regions_uses_automatic_group_template(self):
        config = {
            "proxy-providers": {
                "A": {"type": "http", "url": "https://a.invalid/sub"},
                "B": {"type": "http", "url": "https://b.invalid/sub"},
            },
            "proxy-groups": [
                {
                    "name": "🚀 手动选择",
                    "type": "select",
                    "proxies": ["♻️ 自动选择"],
                },
                {
                    "name": "♻️ 自动选择",
                    "type": "url-test",
                    "use": ["A", "B"],
                    "filter": ".*",
                    "url": "https://cp.cloudflare.com/generate_204",
                    "interval": 300,
                    "tolerance": 50,
                },
            ],
        }

        added = expand_provider_region_groups(config)

        self.assertEqual(4, added)
        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual(
            [
                "♻️ 自动选择",
                "🇭🇰 香港_A",
                "🇭🇰 香港_B",
                "🇯🇵 日本_A",
                "🇯🇵 日本_B",
            ],
            groups["🚀 手动选择"]["proxies"],
        )
        self.assertEqual(["A"], groups["🇭🇰 香港_A"]["use"])
        self.assertIn("香港", groups["🇭🇰 香港_A"]["filter"])
        self.assertEqual(["B"], groups["🇯🇵 日本_B"]["use"])
        self.assertIn("日本", groups["🇯🇵 日本_B"]["filter"])

    def test_gfw_fallback_variant_uses_fallback_group_template(self):
        config = {
            "proxy-providers": {
                "A": {"type": "http", "url": "https://a.invalid/sub"},
            },
            "proxy-groups": [
                {
                    "name": "🚀 故障转移",
                    "type": "fallback",
                    "proxies": ["A 节点 1", "A 节点 2"],
                    "url": "https://cp.cloudflare.com/generate_204",
                    "interval": 300,
                }
            ],
        }

        self.assertEqual(2, expand_provider_region_groups(config))
        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual("url-test", groups["🇯🇵 日本_A"]["type"])
        self.assertEqual(["A"], groups["🇯🇵 日本_A"]["use"])
        self.assertNotIn("proxies", groups["🇯🇵 日本_A"])
        self.assertIn("🇭🇰 香港_A", groups["🚀 故障转移"]["proxies"])

    def test_is_idempotent(self):
        config = self.build_config()
        expand_provider_region_groups(config)
        group_count = len(config["proxy-groups"])
        youtube_members = list(config["proxy-groups"][1]["proxies"])

        added = expand_provider_region_groups(config)

        self.assertEqual(0, added)
        self.assertEqual(group_count, len(config["proxy-groups"]))
        self.assertEqual(youtube_members, config["proxy-groups"][1]["proxies"])

    def test_without_proxy_providers_keeps_config_unchanged(self):
        config = {"proxy-groups": [region_group(REGION_GROUPS[0][0], "hk")]}

        self.assertEqual(0, expand_provider_region_groups(config))
        self.assertEqual(1, len(config["proxy-groups"]))


class RegionNameCompatibilityTest(unittest.TestCase):
    def test_moves_static_city_nodes_out_of_other_region(self):
        city_nodes = [
            "Tokyo V2 - B Group",
            "Incheon SS - B Group",
            "California V2 - B Group",
        ]
        config = {
            "proxies": [{"name": name} for name in city_nodes],
            "proxy-groups": [
                {"name": "🇺🇸 美国节点", "proxies": []},
                {"name": "🇯🇵 日本节点", "proxies": []},
                {"name": "🇰🇷 韩国节点", "proxies": []},
                {"name": "🌐 其他地区", "proxies": list(city_nodes)},
            ],
        }

        fix_region_name_compatibility(config)

        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual(["California V2 - B Group"], groups["🇺🇸 美国节点"]["proxies"])
        self.assertEqual(["Tokyo V2 - B Group"], groups["🇯🇵 日本节点"]["proxies"])
        self.assertEqual(["Incheon SS - B Group"], groups["🇰🇷 韩国节点"]["proxies"])
        self.assertEqual([], groups["🌐 其他地区"]["proxies"])

    def test_patches_provider_filters_and_is_idempotent(self):
        config = {
            "proxy-groups": [
                {"name": "🇺🇸 美国节点", "filter": "(?i)(USA|America)"},
                {"name": "🇯🇵 日本节点", "filter": "(?i)(Japan|JP)"},
                {"name": "🇰🇷 韩国节点", "filter": "(?i)(Korea|KR)"},
                {"name": "🌐 其他地区", "filter": "(?i)^(?!.*(?:USA|Japan|Korea)).*$"},
                {"name": "🚀 故障转移", "exclude-filter": "(?i)(USA|Japan|Korea)"},
            ]
        }

        changed = fix_region_name_compatibility(config)
        changed_again = fix_region_name_compatibility(config)

        self.assertEqual(5, changed)
        self.assertEqual(0, changed_again)
        rendered = str(config)
        self.assertIn("California", rendered)
        self.assertIn("Tokyo", rendered)
        self.assertIn("Incheon", rendered)


class DuplicateProviderPrefixTest(unittest.TestCase):
    def test_prefixes_only_accounts_with_same_url_family(self):
        config = {
            "proxy-providers": {
                "喵喵-账号1": {
                    "type": "http",
                    "url": "https://example.com/api/subscribe?token=aaa&type=clash",
                },
                "喵喵-账号2": {
                    "type": "http",
                    "url": "https://example.com/api/subscribe?type=clash&token=bbb",
                    "override": {"udp": True},
                },
                "其他机场": {
                    "type": "http",
                    "url": "https://other.example/sub?token=ccc",
                },
            },
            "proxy-groups": [],
        }

        changed = prefix_duplicate_provider_nodes(config)

        self.assertEqual(2, changed)
        providers = config["proxy-providers"]
        self.assertEqual(
            "[喵喵-账号1] ",
            providers["喵喵-账号1"]["override"]["additional-prefix"],
        )
        self.assertEqual(
            "[喵喵-账号2] ",
            providers["喵喵-账号2"]["override"]["additional-prefix"],
        )
        self.assertTrue(providers["喵喵-账号2"]["override"]["udp"])
        self.assertNotIn("override", providers["其他机场"])

    def test_preserves_existing_prefix_and_is_idempotent(self):
        config = {
            "proxy-providers": {
                "A1": {
                    "url": "https://example.com/sub?token=one",
                    "override": {"additional-prefix": "[自定义] "},
                },
                "A2": {"url": "https://example.com/sub?token=two"},
            },
            "proxy-groups": [],
        }

        changed = prefix_duplicate_provider_nodes(config)
        changed_again = prefix_duplicate_provider_nodes(config)

        self.assertEqual(2, changed)
        self.assertEqual(0, changed_again)
        self.assertEqual(
            "[A1] [自定义] ",
            config["proxy-providers"]["A1"]["override"]["additional-prefix"],
        )

    def test_groups_same_origin_even_when_token_location_differs(self):
        config = {
            "proxy-providers": {
                "A": {"url": "https://example.com/sub?token=one"},
                "B": {"url": "https://example.com/sub/two"},
            },
            "proxy-groups": [],
        }

        self.assertEqual(2, prefix_duplicate_provider_nodes(config))

    def test_does_not_group_different_origins(self):
        config = {
            "proxy-providers": {
                "A": {"url": "https://one.example/sub?token=one"},
                "B": {"url": "https://two.example/sub?token=two"},
            },
            "proxy-groups": [],
        }

        self.assertEqual(0, prefix_duplicate_provider_nodes(config))


if __name__ == "__main__":
    unittest.main()
