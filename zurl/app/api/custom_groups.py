import re

# 名称含 CDN（不区分大小写）或「低倍率」的节点归入该手动选择组。
CDN_LOW_RATE_GROUP_NAME = "CDN/低倍率节点"
CDN_LOW_RATE_FILTER = "(?i)(?:cdn|低倍率)"
_CDN_LOW_RATE_PATTERN = re.compile(CDN_LOW_RATE_FILTER)

# 追加完组后，把组名挂到这些手动选择组末尾，方便在常用入口直接切换。
MANUAL_GROUP_NAMES = ("🚀 手动选择",)


def _group_key(config: dict) -> str | None:
    if isinstance(config.get("proxy-groups"), list):
        return "proxy-groups"
    if isinstance(config.get("Proxy Group"), list):
        return "Proxy Group"
    return None


def _matched_static_proxies(config: dict) -> list[str]:
    proxies = config.get("proxies")
    if not isinstance(proxies, list):
        return []
    names = []
    for proxy in proxies:
        if (
            isinstance(proxy, dict)
            and isinstance(proxy.get("name"), str)
            and _CDN_LOW_RATE_PATTERN.search(proxy["name"])
        ):
            names.append(proxy["name"])
    return names


def _provider_names(config: dict) -> list[str]:
    providers = config.get("proxy-providers")
    if not isinstance(providers, dict):
        return []
    return [name for name in providers if isinstance(name, str) and name.strip()]


def append_cdn_low_rate_group(config: dict) -> bool:
    """追加「CDN/低倍率节点」手动选择组，并挂到手动选择组下。

    机场订阅是 proxy-provider 形态，节点名在运行时才可知，因此用
    filter 在 mihomo 侧筛选；静态节点则直接点名进 proxies。
    无 provider 且无匹配的静态节点时保持配置不变；重复调用幂等。
    """
    if not isinstance(config, dict):
        return False
    group_key = _group_key(config)
    if group_key is None:
        return False

    providers = _provider_names(config)
    static_names = _matched_static_proxies(config)
    if not providers and not static_names:
        return False

    groups = config[group_key]
    group = next(
        (
            item
            for item in groups
            if isinstance(item, dict) and item.get("name") == CDN_LOW_RATE_GROUP_NAME
        ),
        None,
    )
    if group is None:
        group = {"name": CDN_LOW_RATE_GROUP_NAME, "type": "select"}
        groups.append(group)

    group["type"] = "select"
    if providers:
        group["use"] = providers
        group["filter"] = CDN_LOW_RATE_FILTER
    else:
        group.pop("use", None)
        group.pop("filter", None)
    if static_names:
        group["proxies"] = static_names
    else:
        group.pop("proxies", None)

    for item in groups:
        if (
            isinstance(item, dict)
            and item.get("name") in MANUAL_GROUP_NAMES
            and isinstance(item.get("proxies"), list)
            and CDN_LOW_RATE_GROUP_NAME not in item["proxies"]
        ):
            item["proxies"].append(CDN_LOW_RATE_GROUP_NAME)
    return True
