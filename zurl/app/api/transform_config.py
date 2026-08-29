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

# 内置默认：等价于外置配置只定义这一个组。
# filter 含义：名称带 CDN/低倍率字样，或倍率 ≤0.5x 的节点
# （0.5x、x0.5、0.25x、0.1x、0.5倍 等；1x/2x/10.5x 不会命中）。
DEFAULT_CUSTOM_GROUPS = (
    {
        "name": "CDN/低倍率节点",
        "filter": r"(?i)(?:cdn|低倍率|\b0(?:\.\d+)?\s*[x×倍]|[x×]\s*0(?:\.\d+)?\b)",
        "type": "select",
        "attach_to": ("🚀 手动选择",),
        "exclusive": True,
        "keep_in": ("♻️ 自动选择",),
    },
)

ALLOWED_GROUP_TYPES = {"select", "url-test", "fallback", "load-balance"}

_cache: dict = {"path": None, "mtime": None, "groups": DEFAULT_CUSTOM_GROUPS}


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
                "exclusive": exclusive,
                "keep_in": tuple(keep_in),
            }
        )
    return tuple(groups)


def load_custom_groups(path: str | None = None) -> tuple[dict, ...]:
    """读取外置自定义组配置；带 mtime 缓存，文件变更后自动重载。"""
    path = path or _config_path()
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        # 文件不存在 = 未自定义，直接用内置默认（不写缓存，便于之后创建文件生效）。
        return DEFAULT_CUSTOM_GROUPS

    if _cache["path"] == path and _cache["mtime"] == mtime:
        return _cache["groups"]

    groups = None
    try:
        with open(path, encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except Exception as exc:
        logger.warning("transform 配置读取/解析失败，使用内置默认：%s（%s）", path, exc)
    else:
        if not isinstance(data, dict):
            logger.warning("transform 配置顶层不是对象，使用内置默认：%s", path)
        else:
            groups = _normalize_groups(data.get("custom_groups"))

    if groups is None:
        groups = DEFAULT_CUSTOM_GROUPS
    _cache.update(path=path, mtime=mtime, groups=groups)
    return groups
