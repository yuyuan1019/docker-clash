from urllib.parse import quote


PASSTHROUGH_HEADERS = (
    "subscription-userinfo",
    "profile-update-interval",
    "content-disposition",
    "profile-title",
)


def build_subscription_response_headers(
    upstream_headers: dict, query_args: dict
) -> dict[str, str]:
    """保留订阅元数据，并在上游缺失时用 filename 生成配置名称。"""
    normalized = {
        str(name).lower(): str(value)
        for name, value in upstream_headers.items()
        if value is not None
    }
    result = {}
    for name in PASSTHROUGH_HEADERS:
        value = normalized.get(name)
        if not value:
            continue
        try:
            value.encode("latin-1")
        except UnicodeEncodeError:
            continue
        result[name] = value

    filename = query_args.get("filename", [""])[0].strip()
    if (
        filename
        and len(filename) <= 255
        and not any(ch in filename for ch in "\r\n\x00")
    ):
        result["content-disposition"] = (
            "attachment; filename=\"subscription\"; "
            f"filename*=UTF-8''{quote(filename, safe='')}"
        )
    return result
