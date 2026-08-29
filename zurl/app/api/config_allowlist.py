from urllib.parse import urlparse


# 仅允许页面内置的 GitHub 官方仓库直链（Custom_OpenClash_Rules cfg 目录）。
CONFIG_HOSTS = {"github.com"}

# 与订阅转换页面当前公开的 Clash 远程配置版本保持一致。
CONFIG_NAMES = {
    "Custom_Clash.ini",
    "Custom_Clash_Full.ini",
    "Custom_Clash_Lite.ini",
    "Custom_Clash_GFW.ini",
    "Custom_Clash_Mainland.ini",
    "Custom_Clash_Fallback.ini",
    "Custom_Clash_Full_Fallback.ini",
    "Custom_Clash_Lite_Fallback.ini",
    "Custom_Clash_GFW_Fallback.ini",
}


def _is_supported_config_path(path: str, config_name: str) -> bool:
    return path in {
        "/Aethersailor/Custom_OpenClash_Rules/raw/main/cfg/" + config_name,
        "/Aethersailor/Custom_OpenClash_Rules/raw/refs/heads/main/cfg/"
        + config_name,
    }


def custom_clash_request_error(query_args: dict, feature_name: str) -> str:
    """校验功能只复写页面内置且受信任的 GitHub Clash 配置。"""
    if query_args.get("target", [""])[0] != "clash":
        return f"{feature_name}仅支持 Clash 配置"

    config_url = query_args.get("config", [""])[0].strip()
    parsed = urlparse(config_url)
    config_name = parsed.path.rsplit("/", 1)[-1]
    if (
        parsed.scheme != "https"
        or parsed.hostname not in CONFIG_HOSTS
        or config_name not in CONFIG_NAMES
        or not _is_supported_config_path(parsed.path, config_name)
    ):
        return f"{feature_name}仅支持页面内置的 GitHub Custom_Clash 配置"
    return ""
