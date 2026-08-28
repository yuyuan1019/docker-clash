from copy import deepcopy
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


# 只按用户实际需要细分香港、日本。名称与 Custom_Clash 各版本的基础策略组一致；
# 优先克隆上游地区组。GFW 等没有地区组的精简版本则从其自动/故障转移组
# 继承测速参数，并使用这里的兼容过滤器。
REGION_GROUPS = (
    (
        "🇭🇰 香港节点",
        "🇭🇰 香港",
        r"(?i)(🇭🇰|香港|\bHK\b|Hong ?Kong|Hongkong|HKG|九龙|Kowloon|新界)",
    ),
    (
        "🇯🇵 日本节点",
        "🇯🇵 日本",
        r"(?i)(🇯🇵|日本|东京|大阪|\bJP\b|Japan|JPN|NRT|HND|KIX|TYO|OSA|Tokyo)",
    ),
)

EXCLUDED_PARENT_GROUPS = {
    "♻️ 自动选择",
    "🎯 全球直连",
    "🐟 漏网之鱼",
    "🔀 非标端口",
    *(name for name, _, _ in REGION_GROUPS),
}

PROVIDER_SOURCE_GROUP_NAMES = ("♻️ 自动选择", "🚀 故障转移")


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


def _provider_group_template(
    original_by_name: dict[str, dict], original_name: str, region_filter: str
) -> dict | None:
    original = original_by_name.get(original_name)
    if isinstance(original, dict):
        return original

    for source_name in PROVIDER_SOURCE_GROUP_NAMES:
        source = original_by_name.get(source_name)
        if isinstance(source, dict):
            derived = deepcopy(source)
            # GFW Fallback 只有顶层 fallback；派生地区组仍应负责在单个
            # provider 内测速选优，顶层再按故障转移顺序使用它们。
            if derived.get("type") == "fallback":
                derived["type"] = "url-test"
            derived["filter"] = region_filter
            derived.pop("exclude-filter", None)
            return derived
    return None


def expand_provider_region_groups(config: dict) -> int:
    """按 provider 克隆香港、日本组，并把它们加入可选择的策略组。

    返回新增的派生策略组数量。输入会原地修改；缺少 proxy-provider 或地区组时
    尽量保持配置不变，便于继续兼容 GitHub 上游配置的其他变体。
    """
    if not isinstance(config, dict):
        return 0


    fix_region_name_compatibility(config)
    prefix_duplicate_provider_nodes(config)

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

    for original_name, derived_prefix, region_filter in REGION_GROUPS:
        template = _provider_group_template(
            original_by_name, original_name, region_filter
        )
        if not isinstance(template, dict):
            continue

        region_names: list[str] = []
        for provider_name in providers:
            if not isinstance(provider_name, str) or not provider_name.strip():
                continue
            derived_name = f"{derived_prefix}_{provider_name.strip()}"
            if derived_name in existing_names:
                region_names.append(derived_name)
                continue

            derived = deepcopy(template)
            derived["name"] = derived_name
            derived["use"] = [provider_name]
            # 派生组必须严格限定 provider，不能继承上游可能加入的静态成员。
            derived.pop("proxies", None)
            derived.pop("exclude-filter", None)
            derived_groups.append(derived)
            existing_names.add(derived_name)
            region_names.append(derived_name)

        if region_names:
            derived_by_region[original_name] = region_names

    if not derived_by_region:
        return 0

    all_derived_names = [
        derived_name
        for original_name, _, _ in REGION_GROUPS
        for derived_name in derived_by_region.get(original_name, [])
    ]

    # 已引用标准地区组时紧随其后插入；GFW 等无地区组版本则统一追加。
    # 自动、直连、漏网、非标端口和基础地区组继续保持上游语义。
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
        for derived_name in all_derived_names:
            if derived_name not in seen:
                expanded.append(derived_name)
                seen.add(derived_name)
        group["proxies"] = expanded

    groups.extend(derived_groups)
    return len(derived_groups)
