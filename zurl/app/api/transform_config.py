"""外置转换配置加载器。

配置文件默认位于 /opt/zurl/app/data/transform.yaml（即宿主机 data/zurl/，
该目录已 bind-mount 进容器），修改保存后下次转换即生效，无需重建或重启。
文件缺失或格式错误时自动回退内置默认，不影响订阅生成。
"""

import logging
import os
import re

import yaml

logger = logging.getLogger("uvicorn.error")

# 内置默认：不追加任何自定义分组。
# 保持远程模板（GitHub 仓库 cfg 目录的 ini）原样，只做分组默认项置顶
# （group_defaults）；如需追加自定义组（如 CDN/低倍率专属组），
# 在 data/zurl/transform.yaml 的 custom_groups 中自行定义，
# 参见 config/zurl/transform.example.yaml。
DEFAULT_CUSTOM_GROUPS = ()

ALLOWED_GROUP_TYPES = {"select", "url-test", "fallback", "load-balance"}

# 内置默认：不调整任何分组的默认选中项，保持远程模板（GitHub 仓库
# cfg 目录的 ini）原样（mihomo select 组首项即默认）。
# 如需置顶指定分组默认项，在 data/zurl/transform.yaml 的 group_defaults
# 中自行定义，参见 config/zurl/transform.example.yaml。
DEFAULT_GROUP_DEFAULTS = ()

_cache: dict = {
    "path": None,
    "mtime": None,
    "groups": DEFAULT_CUSTOM_GROUPS,
    "defaults": DEFAULT_GROUP_DEFAULTS,
}


def _config_path() -> str:
    return os.environ.get(
        "TRANSFORM_CONFIG_FILE", "/opt/zurl/app/data/transform.yaml"
    )


def _normalize_groups(raw) -> tuple[dict, ...] | None:
    """校验 custom_groups 列表；返回 None 表示整份配置不可用（回退默认）。

    单条目不合法时跳过该条并告警，其余条目继续生效；列表本身不是
    list、或条目缺 name/filter 时视为整份不可用。空列表是合法值，
    表示用户主动关闭自定义组。
    """
    if not isinstance(raw, list):
        return None

    groups = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            logger.warning("transform 配置条目不是对象，已跳过：%r", entry)
            continue
        name = entry.get("name")
        pattern = entry.get("filter")
        if not isinstance(name, str) or not name.strip():
            logger.warning("transform 配置条目缺少有效 name，已跳过：%r", entry)
            continue
        if name in seen:
            logger.warning("transform 配置组名重复，已跳过：%s", name)
            continue
        if not isinstance(pattern, str) or not pattern:
            logger.warning("transform 配置组 %s 缺少 filter，已跳过", name)
            continue
        try:
            re.compile(pattern)
        except re.error:
            logger.warning("transform 配置组 %s 的 filter 不是有效正则，已跳过", name)
            continue
        group_type = entry.get("type", "select")
        if group_type not in ALLOWED_GROUP_TYPES:
            logger.warning(
                "transform 配置组 %s 的 type 不受支持（%s），已跳过", name, group_type
            )
            continue
        attach_to = entry.get("attach_to", [])
        if not isinstance(attach_to, list) or not all(
            isinstance(item, str) for item in attach_to
        ):
            logger.warning("transform 配置组 %s 的 attach_to 不合法，已跳过", name)
            continue
        attach_with = entry.get("attach_with", [])
        if not isinstance(attach_with, list) or not all(
            isinstance(item, str) for item in attach_with
        ):
            logger.warning("transform 配置组 %s 的 attach_with 不合法，已跳过", name)
            continue
        exclusive = entry.get("exclusive", False)
        if not isinstance(exclusive, bool):
            logger.warning("transform 配置组 %s 的 exclusive 不是布尔值，已跳过", name)
            continue
        keep_in = entry.get("keep_in", [])
        if not isinstance(keep_in, list) or not all(
            isinstance(item, str) for item in keep_in
        ):
            logger.warning("transform 配置组 %s 的 keep_in 不合法，已跳过", name)
            continue
        seen.add(name)
        groups.append(
            {
                "name": name,
                "filter": pattern,
                "type": group_type,
                "attach_to": tuple(attach_to),
                "attach_with": tuple(attach_with),
                "exclusive": exclusive,
                "keep_in": tuple(keep_in),
            }
        )
    return tuple(groups)


def _normalize_group_defaults(raw) -> tuple[dict, ...] | None:
    """校验 group_defaults 列表；返回 None 表示整份不可用（回退默认）。"""
    if not isinstance(raw, list):
        return None

    defaults = []
    for entry in raw:
        if not isinstance(entry, dict):
            logger.warning("group_defaults 条目不是对象，已跳过：%r", entry)
            continue
        group = entry.get("group")
        target = entry.get("default")
        if not isinstance(group, str) or not group.strip():
            logger.warning("group_defaults 条目缺少有效 group，已跳过：%r", entry)
            continue
        if not isinstance(target, str) or not target.strip():
            logger.warning("group_defaults 条目 %s 缺少有效 default，已跳过", group)
            continue
        defaults.append({"group": group, "default": target})
    return tuple(defaults)


def _parse_file(path: str) -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    """读取并校验外置配置，返回 (custom_groups, group_defaults)。"""
    try:
        with open(path, encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except Exception as exc:
        logger.warning("transform 配置读取/解析失败，使用内置默认：%s（%s）", path, exc)
        return DEFAULT_CUSTOM_GROUPS, DEFAULT_GROUP_DEFAULTS
    if not isinstance(data, dict):
        logger.warning("transform 配置顶层不是对象，使用内置默认：%s", path)
        return DEFAULT_CUSTOM_GROUPS, DEFAULT_GROUP_DEFAULTS

    groups = _normalize_groups(data.get("custom_groups"))
    defaults = _normalize_group_defaults(data.get("group_defaults"))
    if groups is None:
        groups = DEFAULT_CUSTOM_GROUPS
    if defaults is None:
        defaults = DEFAULT_GROUP_DEFAULTS
    return groups, defaults


def _load(path: str | None = None):
    path = path or _config_path()
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        # 文件不存在 = 未自定义，直接用内置默认（不写缓存，便于之后创建文件生效）。
        return DEFAULT_CUSTOM_GROUPS, DEFAULT_GROUP_DEFAULTS

    if _cache["path"] == path and _cache["mtime"] == mtime:
        return _cache["groups"], _cache["defaults"]

    groups, defaults = _parse_file(path)
    _cache.update(path=path, mtime=mtime, groups=groups, defaults=defaults)
    return groups, defaults


def load_custom_groups(path: str | None = None) -> tuple[dict, ...]:
    """读取外置自定义组配置；带 mtime 缓存，文件变更后自动重载。"""
    return _load(path)[0]


def load_group_defaults(path: str | None = None) -> tuple[dict, ...]:
    """读取各分组默认选中项配置；带 mtime 缓存，文件变更后自动重载。"""
    return _load(path)[1]
