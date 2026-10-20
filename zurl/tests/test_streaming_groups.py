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


STREAMING_GROUPS = ("日本流媒体", "美国流媒体")
STREAMING_SPECS = [
    {
        "name": country + "流媒体",
        "filter": f"(?:{country}.*流媒体|流媒体.*{country})",
        "type": "select",
        "attach_to": ["🎶 TikTok", "📹 YouTube"],
        "templates": ["Custom_Clash.ini", "Custom_Clash_Full.ini"],
    }
    for country in ("日本", "美国")
]


def provider_config():
    return {
        "proxy-providers": {
            "Provider_A": {"type": "http", "url": "https://example.invalid/sub"}
        },
        "proxy-groups": [
            {"name": "🚀 手动选择", "type": "select", "proxies": ["DIRECT"]},
            {"name": "🎶 TikTok", "type": "select", "proxies": ["🚀 手动选择"]},
            {"name": "📹 YouTube", "type": "select", "proxies": ["🚀 手动选择"]},
            {"name": "🎥 Netflix", "type": "select", "proxies": ["🚀 手动选择"]},
        ],
    }


def convert(template, config=None):
    query = urlencode({"target": "clash", "config": template})
    request = Request({
        "type": "http", "method": "GET", "path": "/subapi/sub",
        "query_string": query.encode(), "headers": [],
    })
    fetch = AsyncMock(
        return_value=(200, yaml.safe_dump(config or provider_config(), allow_unicode=True), {})
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as config_file:
        yaml.safe_dump({"custom_groups": STREAMING_SPECS}, config_file)
        config_file.flush()
        with patch.dict(os.environ, {"TRANSFORM_CONFIG_FILE": config_file.name}):
            with patch.object(CompatAPI, "_fetch_subconverter", fetch):
                response = asyncio.run(CompatAPI().subscription_compat(request))
    return yaml.safe_load(bytes(response.body))


class StreamingGroupsTest(unittest.TestCase):
    def test_only_requested_templates_offer_both_groups_to_tiktok_and_youtube(self):
        for filename in (
            "Custom_Clash.ini",
            "Custom_Clash_Full.ini",
            "Custom_Clash_Fallback.ini",
            "Custom_Clash_GFW.ini",
            "ACL4SSR_Online_Full.ini",
        ):
            with self.subTest(filename=filename):
                result = convert("https://example.invalid/cfg/" + filename)
                groups = {group["name"]: group for group in result["proxy-groups"]}
                expected = filename in {"Custom_Clash.ini", "Custom_Clash_Full.ini"}
                for name in STREAMING_GROUPS:
                    self.assertEqual(expected, name in groups)
                    for service in ("🎶 TikTok", "📹 YouTube"):
                        self.assertEqual(expected, name in groups[service]["proxies"])
                    self.assertNotIn(name, groups["🎥 Netflix"]["proxies"])
                    if expected:
                        self.assertEqual("select", groups[name]["type"])
                        self.assertEqual(["Provider_A"], groups[name]["use"])

    def test_country_and_streaming_are_both_required_in_either_order(self):
        result = convert("https://example.invalid/cfg/Custom_Clash.ini")
        groups = {group["name"]: group for group in result["proxy-groups"]}
        for country, other in (("日本", "美国"), ("美国", "日本")):
            pattern = groups[country + "流媒体"]["filter"]
            for name in (country + "-流媒体-01", "流媒体-" + country + "-02"):
                self.assertIsNotNone(re.search(pattern, name))
            for name in (country + "-普通节点", "香港-流媒体", other + "-流媒体", "流媒体"):
                self.assertIsNone(re.search(pattern, name))

    def test_static_nodes_are_filtered_and_existing_defaults_are_preserved(self):
        config = provider_config()
        config.pop("proxy-providers")
        names = ["日本-流媒体01", "流媒体-美国02", "日本-普通03", "香港-流媒体04"]
        config["proxies"] = [{"name": name} for name in names]
        before = deepcopy(config)
        result = convert("https://example.invalid/cfg/Custom_Clash_Full.ini", config)
        groups = {group["name"]: group for group in result["proxy-groups"]}
        self.assertEqual([names[0]], groups["日本流媒体"]["proxies"])
        self.assertEqual([names[1]], groups["美国流媒体"]["proxies"])
        for service in ("🎶 TikTok", "📹 YouTube"):
            self.assertEqual("🚀 手动选择", groups[service]["proxies"][0])
        self.assertEqual(before["proxy-groups"][3], groups["🎥 Netflix"])

    def test_repeated_conversion_does_not_duplicate_groups_or_choices(self):
        template = "https://example.invalid/cfg/Custom_Clash.ini"
        first = convert(template)
        second = convert(template, first)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
