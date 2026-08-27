from copy import deepcopy
import re


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


# 仅扩展首批确认的五个地区。名称与 Custom_Clash_Full 当前的基础策略组一致；
# 派生组直接克隆转换结果，地区正则和测速参数仍由上游配置维护。
REGION_GROUPS = (
    ("🇭🇰 香港节点", "🇭🇰 香港"),
    ("🇺🇸 美国节点", "🇺🇸 美国"),
    ("🇯🇵 日本节点", "🇯🇵 日本"),
    ("🇸🇬 新加坡节点", "🇸🇬 新加坡"),
    ("🇼🇸 台湾节点", "🇼🇸 台湾"),
)

EXCLUDED_PARENT_GROUPS = {
    "🚀 手动选择",
    "♻️ 自动选择",
    "🎯 全球直连",
    "🐟 漏网之鱼",
    "🔀 非标端口",
    *(name for name, _ in REGION_GROUPS),
}


def _group_key(config: dict) -> str | None:
    if isinstance(config.get("proxy-groups"), list):
        return "proxy-groups"
    if isinstance(config.get("Proxy Group"), list):
        return "Proxy Group"
    return None


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


def expand_provider_region_groups(config: dict) -> int:
    """按 provider 克隆五个地区组，并把它们加入业务策略组。

    返回新增的派生策略组数量。输入会原地修改；缺少 proxy-provider 或地区组时
    保持配置不变，便于继续兼容 GitHub 上游配置的其他变体。
    """
    if not isinstance(config, dict):
        return 0


    fix_region_name_compatibility(config)

    providers = config.get("proxy-providers")
    group_key = _group_key(config)
    if not isinstance(providers, dict) or not providers or group_key is None:
        return 0

    groups = config[group_key]
    original_by_name = {
        group.get("name"): group
        for group in groups
        if isinstance(group, dict) and isinstance(group.get("name"), str)
    }
    existing_names = set(original_by_name)
    derived_by_region: dict[str, list[str]] = {}
    derived_groups: list[dict] = []

    for original_name, derived_prefix in REGION_GROUPS:
        original = original_by_name.get(original_name)
        if not isinstance(original, dict):
            continue

        region_names: list[str] = []
        for provider_name in providers:
            if not isinstance(provider_name, str) or not provider_name.strip():
                continue
            derived_name = f"{derived_prefix}_{provider_name.strip()}"
            if derived_name in existing_names:
                region_names.append(derived_name)
                continue

            derived = deepcopy(original)
            derived["name"] = derived_name
            derived["use"] = [provider_name]
            # 派生组必须严格限定 provider，不能继承未来上游可能加入的其他成员。
            derived.pop("proxies", None)
            derived_groups.append(derived)
            existing_names.add(derived_name)
            region_names.append(derived_name)

        if region_names:
            derived_by_region[original_name] = region_names

    if not derived_by_region:
        return 0

    # 只扩展引用标准地区组的业务组；基础手动/自动/地区组保持上游原样。
    for group in groups:
        if not isinstance(group, dict) or group.get("name") in EXCLUDED_PARENT_GROUPS:
            continue
        members = group.get("proxies")
        if not isinstance(members, list):
            continue

        expanded: list = []
        seen: set[str] = set()
        for member in members:
            if not isinstance(member, str):
                expanded.append(member)
                continue
            if member not in seen:
                expanded.append(member)
                seen.add(member)
            for derived_name in derived_by_region.get(member, []):
                if derived_name not in seen:
                    expanded.append(derived_name)
                    seen.add(derived_name)
        group["proxies"] = expanded

    groups.extend(derived_groups)
    return len(derived_groups)
