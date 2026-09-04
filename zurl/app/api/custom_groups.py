import logging
import re

from app.api.transform_config import load_custom_groups, load_group_defaults

logger = logging.getLogger("uvicorn.error")

# mihomo 内置策略，作为默认项目标永远合法
BUILTIN_POLICIES = frozenset({"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"})


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


def apply_group_defaults(config: dict, defaults=None) -> int:
    """把指定分组的默认选中项置顶（mihomo select 组首项即默认）。

    defaults 为 None 时从外置配置读取（group_defaults，热加载）。
    目标已在成员列表中时移到置顶；目标不在列表中时仅当它在配置中
    确实存在（其他分组、静态节点或内置策略）才插入引用，避免插入
    悬空引用导致 mihomo 解析失败直接退出（转换后端偶尔会因远程配置
    拉取异常而生成分组缺失的降级配置）。分组不存在或没有 proxies
    列表时跳过。返回发生调整的分组数量。
    """
    if not isinstance(config, dict):
        return 0
    group_key = _group_key(config)
    if group_key is None:
        return 0
    if defaults is None:
        defaults = load_group_defaults()
    else:
        defaults = tuple(defaults)

    by_name = {
        item.get("name"): item
        for item in config[group_key]
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    # 合法目标 = 配置中真实存在的分组/静态节点 + mihomo 内置策略；
    # 其余一律跳过，防止把不存在的组名插进 proxies 造成 mihomo 启动失败。
    valid_targets = (
        set(by_name) | set(_static_proxy_names(config)) | BUILTIN_POLICIES
    )
    changed = 0
    for spec in defaults:
        group = by_name.get(spec["group"])
        if not isinstance(group, dict):
            continue
        members = group.get("proxies")
        if not isinstance(members, list):
            continue
        target = spec["default"]
        if members and members[0] == target:
            continue
        if target not in members and target not in valid_targets:
            logger.warning(
                "group_defaults 跳过：%s 的默认项 %s 在配置中不存在（可能是降级配置），"
                "未插入避免悬空引用",
                spec["group"],
                target,
            )
            continue
        if target in members:
            members.remove(target)
        members.insert(0, target)
        changed += 1
    return changed


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
    attach_with 锚点：包含锚点组（如地区组）的分组会把本组紧跟其后插入，
    与地区组同可选；attach_to 则是追加到指定组末尾（无锚点时的回退）。
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

    if exclusive_specs:
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
            # 形态二：provider 节点列表（业务组的 .* 全量节点）。
            if "use" in item or "filter" in item:
                if isinstance(item.get("proxies"), list) and item["proxies"]:
                    # 带组引用的业务组：直接去掉 .* 节点列表。既剔除单个 CDN 节点，
                    # 也避免 exclude-filter 按名字把挂入的「🏷️ CDN/低倍率节点」组
                    # 本身滤掉（mihomo 的 filter 对显式成员同样生效）。
                    item.pop("use", None)
                    item.pop("filter", None)
                    item.pop("exclude-filter", None)
                else:
                    # 纯节点组（无组引用、也挂不了组）：运行时过滤兜底。
                    existing = item.get("exclude-filter")
                    if (
                        not isinstance(existing, str)
                        or exclude_pattern not in existing
                    ):
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
            if name not in ensured_set or name in members:
                continue
            # attach_with：包含锚点组（如地区组）的分组，紧跟最后一个锚点后插入，
            # 与香港节点学同等的可选位置；否则回退 attach_to（追加到末尾）。
            anchors = spec.get("attach_with", ())
            if anchors:
                insert_at = -1
                for index, member in enumerate(members):
                    if isinstance(member, str) and member in anchors:
                        insert_at = index + 1
                if insert_at >= 0:
                    members.insert(insert_at, name)
                    continue
            # attach_after：仅对 attach_to 目标组生效，紧跟指定成员后插入
            # （如紧跟默认项置为第二顺位）；成员不存在时退化为追加末尾
            # （如 Bahamut 无美国节点）。非目标组不处理。
            if item.get("name") in spec.get("attach_to", ()):
                after = spec.get("attach_after")
                if isinstance(after, str) and after and after in members:
                    members.insert(members.index(after) + 1, name)
                    continue
                members.append(name)
    return len(ensured)
