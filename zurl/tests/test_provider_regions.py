import unittest

from app.api.provider_regions import (
    fix_region_name_compatibility,
    prefix_duplicate_provider_nodes,
)


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
