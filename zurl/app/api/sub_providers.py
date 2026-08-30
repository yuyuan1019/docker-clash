from fastapi import Request
from fastapi.responses import Response

from app.api.gateway_auth import COOKIE_NAME, WEB_AUTH_ENABLED, _valid_session
from app.models.sub_providers import SubProvider

# 提供商字典上限与字段长度限制
MAX_PROVIDERS = 200
MAX_NAME_LEN = 64
MAX_URL_LEN = 2048


def _authorized(request: Request) -> bool:
    # 与 /gateway/form-config 同一套网关会话鉴权
    return not WEB_AUTH_ENABLED or _valid_session(request.cookies.get(COOKIE_NAME, ""))


def _unauthorized() -> Response:
    return Response(status_code=401, headers={"Cache-Control": "no-store"})


class SubProviderAPI:
    async def list_providers(self, request: Request):
        if not _authorized(request):
            return _unauthorized()
        return {"Code": 1, "Message": "ok", "Providers": SubProvider.list_all()}

    async def save_provider(self, request: Request):
        if not _authorized(request):
            return _unauthorized()
        try:
            body = await request.json()
        except Exception:
            return {"Code": 0, "Message": "请求不是有效的 JSON"}
        if not isinstance(body, dict):
            return {"Code": 0, "Message": "请求格式不正确"}

        name = str(body.get("name", "")).strip()
        url = str(body.get("url", "")).strip()
        # 与前端拼接 sourceSubUrl 的约束保持一致：名称不允许出现 , | < >
        name = name.replace(",", "").replace("|", "").replace("<", "").replace(">", "").strip()
        if not name:
            return {"Code": 0, "Message": "提供商名称不能为空"}
        if not url:
            return {"Code": 0, "Message": "订阅链接不能为空"}
        if len(name) > MAX_NAME_LEN:
            return {"Code": 0, "Message": f"提供商名称不能超过 {MAX_NAME_LEN} 个字符"}
        if len(url) > MAX_URL_LEN:
            return {"Code": 0, "Message": "订阅链接过长"}
        if not SubProvider.url_exists(url) and SubProvider.count() >= MAX_PROVIDERS:
            return {"Code": 0, "Message": f"最多保存 {MAX_PROVIDERS} 条提供商记录"}

        saved = SubProvider.upsert(name, url)
        if not saved:
            return {"Code": 0, "Message": "保存提供商失败"}
        return {"Code": 1, "Message": "ok", "Provider": saved}

    async def delete_provider(self, request: Request):
        if not _authorized(request):
            return _unauthorized()
        try:
            body = await request.json()
        except Exception:
            return {"Code": 0, "Message": "请求不是有效的 JSON"}
        if not isinstance(body, dict):
            return {"Code": 0, "Message": "请求格式不正确"}
        try:
            provider_id = int(body.get("id", 0))
        except (TypeError, ValueError):
            return {"Code": 0, "Message": "记录 ID 不正确"}
        if provider_id <= 0 or not SubProvider.delete_by_id(provider_id):
            return {"Code": 0, "Message": "提供商记录不存在或已删除"}
        return {"Code": 1, "Message": "ok"}
