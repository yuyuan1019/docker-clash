import unittest

from app.api.provider_regions import (
    REGION_GROUPS,
    expand_provider_region_groups,
    fix_region_name_compatibility,
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
            for index, (name, _) in enumerate(REGION_GROUPS)
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
                    "proxies": [name for name, _ in REGION_GROUPS],
                },
                {
                    "name": "📹 YouTube",
                    "type": "select",
                    "proxies": ["🚀 手动选择", *[name for name, _ in REGION_GROUPS]],
                },
                {
                    "name": "🐟 漏网之鱼",
                    "type": "select",
                    "proxies": ["🚀 手动选择", *[name for name, _ in REGION_GROUPS]],
                },
                *region_groups,
            ],
        }

    def test_adds_five_regions_for_each_provider(self):
        config = self.build_config()

        added = expand_provider_region_groups(config)

        self.assertEqual(10, added)
        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual(["A"], groups["🇭🇰 香港_A"]["use"])
        self.assertEqual(["B"], groups["🇭🇰 香港_B"]["use"])
        self.assertEqual("filter-0", groups["🇭🇰 香港_A"]["filter"])
        self.assertNotIn("proxies", groups["🇭🇰 香港_A"])

    def test_expands_business_groups_but_keeps_base_groups_unchanged(self):
        config = self.build_config()
        original_manual = list(config["proxy-groups"][0]["proxies"])

        expand_provider_region_groups(config)

        groups = {group["name"]: group for group in config["proxy-groups"]}
        self.assertEqual(original_manual, groups["🚀 手动选择"]["proxies"])
        self.assertEqual(
            ["🚀 手动选择", *original_manual],
            groups["🐟 漏网之鱼"]["proxies"],
        )
        youtube = groups["📹 YouTube"]["proxies"]
        self.assertEqual(
            ["🇭🇰 香港节点", "🇭🇰 香港_A", "🇭🇰 香港_B"],
            youtube[1:4],
        )
        self.assertIn("🇼🇸 台湾_A", youtube)
        self.assertIn("🇼🇸 台湾_B", youtube)

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


if __name__ == "__main__":
    unittest.main()
