import re

from app.api.transform_config import load_custom_groups


def _group_key(config: dict) -> str | None:
    if isinstance(config.get("proxy-groups"), list):
        return "proxy-groups"
    if isinstance(config.get("Proxy Group"), list):
        return "Proxy Group"
    return None


def _static_proxy_names(config: dict) -> list[str]:
    proxies = config.get("proxies")
    if not isinstance(proxies, list):
        return []
    names = []
    for proxy in proxies:
        if isinstance(proxy, dict) and isinstance(proxy.get("name"), str):
            names.append(proxy["name"])
    return names


def _provider_names(config: dict) -> list[str]:
    providers = config.get("proxy-providers")
    if not isinstance(providers, dict):
        return []
    return [name for name in providers if isinstance(name, str) and name.strip()]


def append_custom_groups(config: dict, groups=None) -> int:
    """按外置配置追加自定义选择组，并挂到 attach_to 指定的组末尾。

    groups 为 None 时从外置配置文件读取（data/zurl/transform.yaml，热加载，
    失败回退内置默认）。机场订阅是 proxy-provider 形态，节点名运行时才可知，
    因此用 filter 在 mihomo 侧筛选；静态节点则直接点名进 proxies。
    exclusive 条目会把匹配节点从其他组剔除（显式列表直接移除，
    provider filter 组追加 exclude-filter），仅保留在专属组与 keep_in 组。
    无 provider 且无匹配静态节点的组不会生成（也不会被 attach，避免悬空引用）；
    重复调用幂等。返回成功生成的组数量。
    """
    if not isinstance(config, dict):
        return 0
    group_key = _group_key(config)
    if group_key is None:
        return 0
    if groups is None:
        groups = load_custom_groups()
    else:
        groups = tuple(groups)

    providers = _provider_names(config)
    static_names = _static_proxy_names(config)

    all_groups = config[group_key]
    by_name = {
        item.get("name"): item
        for item in all_groups
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }

    # exclusive：匹配节点从其他组中剔除，只保留在专属组与 keep_in 指定的组。
    exclusive_specs = [spec for spec in groups if spec.get("exclusive")]
    matched_union: set[str] = set()
    for spec in exclusive_specs:
        pattern = re.compile(spec["filter"])
        matched_union.update(name for name in static_names if pattern.search(name))
    exclude_pattern = "|".join(spec["filter"] for spec in exclusive_specs)
    exempt_names = {spec["name"] for spec in exclusive_specs}
    for spec in exclusive_specs:
        exempt_names.update(spec.get("keep_in", ()))

    if exclude_pattern:
        for item in all_groups:
            if not isinstance(item, dict) or item.get("name") in exempt_names:
                continue
            # 形态一：显式节点列表 —— 直接移除匹配节点。
            if matched_union and isinstance(item.get("proxies"), list):
                item["proxies"] = [
                    member
                    for member in item["proxies"]
                    if not (isinstance(member, str) and member in matched_union)
                ]
            # 形态二：provider filter 组（含业务组的 .* 全量节点）——追加 exclude-filter。
            if "filter" in item or "use" in item:
                existing = item.get("exclude-filter")
                if not isinstance(existing, str) or exclude_pattern not in existing:
                    item["exclude-filter"] = (
                        f"{existing}|{exclude_pattern}"
                        if isinstance(existing, str) and existing
                        else exclude_pattern
                    )

    ensured: list[str] = []
    for spec in groups:
        pattern = re.compile(spec["filter"])
        matched = [name for name in static_names if pattern.search(name)]
        if not providers and not matched:
            continue

        group = by_name.get(spec["name"])
        if group is None:
            group = {"name": spec["name"]}
            all_groups.append(group)
            by_name[spec["name"]] = group

        group["type"] = spec["type"]
        if providers:
            group["use"] = providers
            group["filter"] = spec["filter"]
        else:
            group.pop("use", None)
            group.pop("filter", None)
        if matched:
            group["proxies"] = matched
        else:
            group.pop("proxies", None)
        ensured.append(spec["name"])

    if not ensured:
        return 0

    ensured_set = set(ensured)
    for item in all_groups:
        if not isinstance(item, dict):
            continue
        members = item.get("proxies")
        if not isinstance(members, list):
            continue
        for spec in groups:
            name = spec["name"]
            if (
                name in ensured_set
                and item.get("name") in spec["attach_to"]
                and name not in members
            ):
                members.append(name)
    return len(ensured)
