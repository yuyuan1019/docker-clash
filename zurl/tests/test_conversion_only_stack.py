import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


class ConversionOnlyStackTest(unittest.TestCase):
    def test_frontend_has_no_local_kernel_actions_or_status_polling(self):
        page = (ROOT / "sub-web-modify/src/views/Subconverter.vue").read_text()
        for retired in (
            "更新并应用配置", "开启 mihomo", "关闭 mihomo", "打开面板",
            "mihomoStatus", "getMihomoStatus", "controlMihomo", "updateAndApplyConfig",
            "statusTimer", "xdPanelUrl", '"/mihomo/', '"/apply"',
        ):
            with self.subTest(retired=retired):
                self.assertFalse(retired in page, f"页面仍含 {retired}")
        for retained in ("生成订阅链接", "生成短链接", "从URL解析", "一键导入 Clash"):
            self.assertIn(retained, page)

    def test_only_mihomo_service_is_removed_and_web_port_is_unchanged(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        services = compose["services"]
        self.assertEqual(
            {"nginx", "sub-web", "subconverter", "zurl", "metacubexd"}, set(services)
        )
        self.assertEqual(["${WEB_PORT:-7788}:80"], services["nginx"]["ports"])
        self.assertNotIn("mihomo", services["metacubexd"].get("depends_on", []))


if __name__ == "__main__":
    unittest.main()
