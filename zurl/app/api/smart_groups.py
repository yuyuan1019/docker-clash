from urllib.parse import urlparse


SMART_CONFIG_HOSTS = {
    "testingcf.jsdelivr.net",
    "cdn.jsdelivr.net",
    "raw.githubusercontent.com",
}

# 与订阅转换页面当前公开的 Clash 远程配置版本保持一致。
SMART_CONFIG_NAMES = {
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

SMART_SOURCE_TYPES = {"url-test", "load-balance"}


def _is_supported_config_path(hostname: str, path: str, config_name: str) -> bool:
    if hostname == "raw.githubusercontent.com":
        return path in {
            "/Aethersailor/Custom_OpenClash_Rules/main/cfg/" + config_name,
            "/Aethersailor/Custom_OpenClash_Rules/refs/heads/main/cfg/"
            + config_name,
        }
    return path in {
        "/gh/Aethersailor/Custom_OpenClash_Rules@main/cfg/" + config_name,
        "/gh/Aethersailor/Custom_OpenClash_Rules@refs/heads/main/cfg/"
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
        or parsed.hostname not in SMART_CONFIG_HOSTS
        or config_name not in SMART_CONFIG_NAMES
        or not _is_supported_config_path(parsed.hostname, parsed.path, config_name)
    ):
        return f"{feature_name}仅支持页面内置的 GitHub Custom_Clash 配置"
    return ""


def smart_request_error(query_args: dict) -> str:
    """校验 Smart 专版只复写受信任的 GitHub 上游 Clash 配置。"""
    return custom_clash_request_error(query_args, "Smart 专版")


def convert_smart_groups(config: dict) -> int:
    """把自动选择组转换成 Smart 内核组，同时保留上游分流语义。"""
    if not isinstance(config, dict):
        return 0

    group_key = None
    if isinstance(config.get("proxy-groups"), list):
        group_key = "proxy-groups"
    elif isinstance(config.get("Proxy Group"), list):
        group_key = "Proxy Group"
    if group_key is None:
        return 0

    changed = 0
    for group in config[group_key]:
        if not isinstance(group, dict):
            continue

        group_type = group.get("type")
        if group_type in SMART_SOURCE_TYPES:
            group["type"] = "smart"
            # Smart 当前不使用 load-balance 的分流策略；遗留字段会误导使用者。
            group.pop("strategy", None)
            group.pop("persistent", None)
            changed += 1
        elif group_type != "smart":
            continue

        # 使用官方 Smart 轻量模型；不在路由器上采集训练数据。
        group["uselightgbm"] = True
        group["collectdata"] = False
        group.pop("sample-rate", None)

    return changed
