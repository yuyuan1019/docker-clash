import re
from urllib.parse import urlsplit


# 上游主要按节点名称分组；补齐机场常用、但当前规则未覆盖的英文城市名。
REGION_NAME_ALIASES = {
    "🇺🇸 美国节点": ("California",),
    "🇯🇵 日本节点": ("Tokyo",),
    "🇰🇷 韩国节点": ("Incheon",),
}

_ALL_ALIAS_PATTERN = "|".join(
    re.escape(alias)
    for aliases in REGION_NAME_ALIASES.values()
    for alias in aliases
)


def _group_key(config: dict) -> str | None:
    if isinstance(config.get("proxy-groups"), list):
        return "proxy-groups"
    if isinstance(config.get("Proxy Group"), list):
        return "Proxy Group"
    return None


def _provider_url_family(raw_url: str) -> tuple | None:
    """返回不包含路径或 token 的订阅来源特征。"""
    try:
        parsed = urlsplit(raw_url.strip())
    except (TypeError, ValueError):
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return (
        parsed.scheme.lower(),
        parsed.netloc.casefold(),
    )


def prefix_duplicate_provider_nodes(config: dict) -> int:
    """同源订阅账号有两条以上时，为其节点增加 provider 名称前缀。"""
    if not isinstance(config, dict):
        return 0
    providers = config.get("proxy-providers")
    if not isinstance(providers, dict):
        return 0

    families: dict[tuple, list[tuple[str, dict]]] = {}
    for provider_name, provider in providers.items():
        if not isinstance(provider_name, str) or not isinstance(provider, dict):
            continue
        family = _provider_url_family(provider.get("url", ""))
        if family is not None:
            families.setdefault(family, []).append((provider_name, provider))

    changed = 0
    for same_source in families.values():
        if len(same_source) < 2:
            continue
        for provider_name, provider in same_source:
            prefix = f"[{provider_name.strip()}] "
            override = provider.get("override")
            if not isinstance(override, dict):
                override = {}
                provider["override"] = override
            current = override.get("additional-prefix", "")
            if not isinstance(current, str):
                current = ""
            if not current.startswith(prefix):
                override["additional-prefix"] = prefix + current
                changed += 1
    return changed


def _append_filter_aliases(pattern: str, aliases: tuple[str, ...]) -> str:
    alias_pattern = "|".join(re.escape(alias) for alias in aliases)
    return f"(?:{pattern})|(?i:{alias_pattern})"


def _exclude_aliases_from_filter(pattern: str) -> str:
    if pattern.startswith("(?i)"):
        return f"(?i)(?!.*(?:{_ALL_ALIAS_PATTERN})){pattern[4:]}"
    return f"(?i)(?!.*(?:{_ALL_ALIAS_PATTERN}))(?:{pattern})"


def fix_region_name_compatibility(config: dict) -> int:
    """修正英文城市归属，兼容静态节点和 proxy-provider 两种配置。"""
    if not isinstance(config, dict):
        return 0

    group_key = _group_key(config)
    if group_key is None:
        return 0

    groups = [group for group in config[group_key] if isinstance(group, dict)]
    proxies = config.get("proxies")
    proxy_names = []
    if isinstance(proxies, list):
        proxy_names = [
            proxy.get("name")
            for proxy in proxies
            if isinstance(proxy, dict) and isinstance(proxy.get("name"), str)
        ]

    changed = 0
    matched_by_region = {
        region: [
            name
            for name in proxy_names
            if any(alias.casefold() in name.casefold() for alias in aliases)
        ]
        for region, aliases in REGION_NAME_ALIASES.items()
    }
    all_matched_names = {
        name for names in matched_by_region.values() for name in names
    }

    for group in groups:
        name = group.get("name", "")
        aliases = REGION_NAME_ALIASES.get(name)
        pattern = group.get("filter")

        if aliases and isinstance(pattern, str) and not any(
            alias.casefold() in pattern.casefold() for alias in aliases
        ):
            group["filter"] = _append_filter_aliases(pattern, aliases)
            changed += 1

        members = group.get("proxies")
        if aliases and isinstance(members, list):
            for proxy_name in matched_by_region[name]:
                if proxy_name not in members:
                    members.append(proxy_name)
                    changed += 1

        if "其他地区" in name:
            if isinstance(pattern, str) and not all(
                alias.casefold() in pattern.casefold()
                for region_aliases in REGION_NAME_ALIASES.values()
                for alias in region_aliases
            ):
                group["filter"] = _exclude_aliases_from_filter(pattern)
                changed += 1
            if isinstance(members, list):
                filtered = [member for member in members if member not in all_matched_names]
                changed += len(members) - len(filtered)
                group["proxies"] = filtered

        exclude_pattern = group.get("exclude-filter")
        if isinstance(exclude_pattern, str) and not all(
            alias.casefold() in exclude_pattern.casefold()
            for region_aliases in REGION_NAME_ALIASES.values()
            for alias in region_aliases
        ):
            group["exclude-filter"] = _append_filter_aliases(
                exclude_pattern,
                tuple(
                    alias
                    for region_aliases in REGION_NAME_ALIASES.values()
                    for alias in region_aliases
                ),
            )
            changed += 1

    return changed
