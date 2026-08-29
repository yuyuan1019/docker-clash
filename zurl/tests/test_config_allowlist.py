import unittest

from app.api.config_allowlist import (
    CONFIG_NAMES,
    custom_clash_request_error,
)

GITHUB_BASE = "https://github.com/Aethersailor/Custom_OpenClash_Rules/raw/main/cfg/"
GITHUB_REFS_BASE = (
    "https://github.com/Aethersailor/Custom_OpenClash_Rules/raw/refs/heads/main/cfg/"
)
FEATURE = "香港/日本提供商复写版"


class ConfigAllowlistTest(unittest.TestCase):
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
            CONFIG_NAMES,
        )

    def test_accepts_supported_github_config(self):
        for config_name in CONFIG_NAMES:
            for url in (GITHUB_BASE + config_name, GITHUB_REFS_BASE + config_name):
                with self.subTest(url=url):
                    query = {"target": ["clash"], "config": [url]}
                    self.assertEqual(
                        "", custom_clash_request_error(query, FEATURE)
                    )

    def test_rejects_legacy_cdn_and_raw_hosts(self):
        for url in (
            "https://testingcf.jsdelivr.net/gh/Aethersailor/"
            "Custom_OpenClash_Rules@refs/heads/main/cfg/Custom_Clash.ini",
            "https://cdn.jsdelivr.net/gh/Aethersailor/"
            "Custom_OpenClash_Rules@main/cfg/Custom_Clash.ini",
            "https://raw.githubusercontent.com/Aethersailor/"
            "Custom_OpenClash_Rules/main/cfg/Custom_Clash.ini",
        ):
            with self.subTest(url=url):
                query = {"target": ["clash"], "config": [url]}
                self.assertIn(
                    "仅支持页面内置", custom_clash_request_error(query, FEATURE)
                )

    def test_rejects_non_clash_and_untrusted_config(self):
        self.assertIn(
            "仅支持 Clash",
            custom_clash_request_error({"target": ["surge"], "config": [""]}, FEATURE),
        )
        self.assertIn(
            "页面内置",
            custom_clash_request_error(
                {"target": ["clash"], "config": ["https://evil.invalid/Custom_Clash.ini"]},
                FEATURE,
            ),
        )
        self.assertIn(
            "页面内置",
            custom_clash_request_error(
                {
                    "target": ["clash"],
                    "config": ["https://github.com/other/repo/raw/main/cfg/Custom_Clash.ini"],
                },
                FEATURE,
            ),
        )
        self.assertIn(
            "页面内置",
            custom_clash_request_error(
                {
                    "target": ["clash"],
                    "config": "https://github.com/Aethersailor/Custom_OpenClash_Rules/tree/main/cfg/Custom_Clash.ini",
                },
                FEATURE,
            ),
        )


if __name__ == "__main__":
    unittest.main()
