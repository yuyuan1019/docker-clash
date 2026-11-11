import logging
import re

from app.api.transform_config import load_custom_groups, load_group_defaults

logger = logging.getLogger("uvicorn.error")

# mihomo 内置策略，作为默认项目标永远合法
BUILTIN_POLICIES = frozenset({"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"})

# 开头的内联标志，如 (?i) 或 (?im)
_LEADING_FLAGS = re.compile(r"^\(\?([aiLmsux]+)\)")


def _scope_inline_flags(pattern: str) -> str:
    """把开头的 (?i) 转成 (?i:...)，便于嵌进更大的表达式。

    同一表达式里再出现 (?i) 属于「非开头位置的内联标志」——mihomo（regexp2）
    接受，但 Python re 等引擎会直接报错，转成作用域写法两边都合法，语义不变。
    """
    match = _LEADING_FLAGS.match(pattern)
    if not match:
        return pattern
    return f"(?{match.group(1)}:{pattern[match.end():]})"


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


def _effective_providers(spec: dict, providers: list[str]) -> list[str]:
    """该自定义组实际挂载的 provider 列表。

    providers 是白名单（缺省=全部 provider）；exclude_providers 另行排除，
    用于让专属组只吃某些机场的节点（如流媒体组不吃特定订阅）。
    """
    allow = spec.get("providers") or ()
    deny = spec.get("exclude_providers") or ()
    return [
        name for name in providers
        if (not allow or name in allow) and name not in deny
    ]


def _detach_providers(config: dict, all_groups: list, keep: dict) -> int:
    """把 keep 中的 provider 从其他所有组的 provider 来源里剔除。

    keep 形如 {provider 名: {允许保留它的组名}}。订阅里的 provider 是整包挂进
    组（use）的，无法按名字过滤单个节点，所以想让某个订阅的节点只出现在专属组
    里，只能从其他组的 use 列表里摘掉它。摘完没有 provider 的组退回纯组引用，
    连节点也没有时补 DIRECT，避免空 use 让 mihomo 解析失败。返回改动的组数。
    """
    if not keep:
        return 0
    changed = 0
    for item in all_groups:
        if not isinstance(item, dict):
            continue
        use = item.get("use")
        if not isinstance(use, list) or not use:
            continue
        name = item.get("name")
        remaining = [
            provider for provider in use
            if not (provider in keep and name not in keep[provider])
        ]
        if len(remaining) == len(use):
            continue
        if remaining:
            item["use"] = remaining
        else:
            item.pop("use", None)
            item.pop("filter", None)
            item.pop("exclude-filter", None)
            if not item.get("proxies"):
                item["proxies"] = ["DIRECT"]
        changed += 1
    return changed


def append_custom_groups(config: dict, groups=None, template_name: str = "") -> int:
    """按外置配置追加自定义选择组，并挂到 attach_to 指定的组末尾。

    groups 为 None 时从外置配置文件读取（data/zurl/transform.yaml，热加载，
    失败回退内置默认）。机场订阅是 proxy-provider 形态，节点名运行时才可知，
    因此用 filter 在 mihomo 侧筛选；静态节点则直接点名进 proxies。
    attach_with 锚点：包含锚点组（如地区组）的分组会把本组紧跟其后插入，
    与地区组同可选；attach_to 则是追加到指定组末尾（无锚点时的回退）。
    providers / exclude_providers 限定本组挂哪些订阅的节点。
    exclusive 条目会把匹配节点从其他组剔除：显式列表直接移除，provider 组在
    filter 前加负向前瞻（filter 不影响显式成员，exclude-filter 会连显式成员
    一起过滤），仅保留在专属组与 keep_in 组。
    exclusive_providers 条目会把整个订阅从其他所有组的 use 里摘掉，只留本组与
    keep_in 组（订阅级排他，节点名无法用来区分订阅来源）。
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

    # 未指定 templates 的旧配置保持原样；仅按需限制新增组的远程模板范围。
    groups = tuple(
        spec for spec in groups
        if not spec.get("templates") or template_name in spec["templates"]
    )

    providers = _provider_names(config)
    static_names = _static_proxy_names(config)

    all_groups = config[group_key]
    by_name = {
        item.get("name"): item
        for item in all_groups
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }

    # exclusive：匹配节点从其他组中剔除，只保留在专属组与 keep_in 指定的组。
    # 用「filter 负向前瞻」实现，而不是 exclude-filter：mihomo 的 exclude-filter
    # 连显式 proxies 成员一起过滤（实测），会把挂进业务组的专属组本身滤掉；
    # filter 只作用于 provider 节点，不影响显式成员引用。
    # 注意：前瞻必须锚定在开头（否则从中间开始的匹配会让排除失效），而锚定后
    # 原 filter 会被迫也从头匹配——机场节点前面可能带 [提供商] 前缀，地区组的
    # (🇭🇰|港|…) 就再也匹配不到。所以中间用 [\s\S]*? 让原 filter 仍可匹配任意位置。
    exclusive_specs = [spec for spec in groups if spec.get("exclusive")]
    if exclusive_specs:
        matched_union: set[str] = set()
        for spec in exclusive_specs:
            pattern = re.compile(spec["filter"])
            matched_union.update(name for name in static_names if pattern.search(name))
        hide_pattern = "|".join(
            f"(?:{_scope_inline_flags(spec['filter'])})" for spec in exclusive_specs
        )
        exempt_names = {spec["name"] for spec in exclusive_specs}
        for spec in exclusive_specs:
            exempt_names.update(spec.get("keep_in", ()))

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
            # 形态二：provider 节点来源 —— 过滤条件加负向前瞻，隐藏匹配节点。
            use = item.get("use")
            if isinstance(use, list) and use:
                prefix = f"^(?!.*(?:{hide_pattern}))"
                current = item.get("filter")
                if isinstance(current, str) and prefix in current:
                    continue
                if not isinstance(current, str) or current in ("", ".*"):
                    item["filter"] = prefix + ".*"
                else:
                    item["filter"] = (
                        f"{prefix}[\\s\\S]*?(?:{_scope_inline_flags(current)})"
                    )

    ensured: list[str] = []
    for spec in groups:
        pattern = re.compile(spec["filter"])
        matched = [name for name in static_names if pattern.search(name)]
        group_providers = _effective_providers(spec, providers)
        if not group_providers and not matched:
            if spec.get("providers"):
                logger.warning(
                    "transform 配置组 %s 指定的 provider 在本次订阅中不存在（%s），"
                    "已跳过该组",
                    spec["name"],
                    ", ".join(spec["providers"]),
                )
            continue

        group = by_name.get(spec["name"])
        if group is None:
            group = {"name": spec["name"]}
            all_groups.append(group)
            by_name[spec["name"]] = group

        group["type"] = spec["type"]
        if group_providers:
            group["use"] = group_providers
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

    # exclusive_providers：把指定订阅的节点从其他所有组摘掉，只保留在声明它的
    # 自定义组（如「塔菲美国节点」）与 keep_in 组里。只在组确实生成成功后才摘，
    # 避免专属组没建成时把所有节点都藏掉。
    provider_keep: dict[str, set[str]] = {}
    for spec in groups:
        if spec["name"] not in ensured_set:
            continue
        for provider in spec.get("exclusive_providers", ()):
            allowed = provider_keep.setdefault(provider, set())
            allowed.add(spec["name"])
            allowed.update(spec.get("keep_in", ()))
    _detach_providers(config, all_groups, provider_keep)
    return len(ensured)
