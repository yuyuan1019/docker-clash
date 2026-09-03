import hashlib
import hmac
import html
import json
import os
import tempfile
import time
from collections import defaultdict, deque
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response


WEB_AUTH_KEY = os.environ.get("MIHOMO_SECRET", "")
WEB_AUTH_ENABLED = os.environ.get("WEB_AUTH_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
WEB_AUTH_TTL = max(300, int(os.environ.get("WEB_AUTH_TTL", "315360000")))
COOKIE_NAME = "docker_clash_session"
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW = 300
_failed_attempts = defaultdict(deque)
FORM_CONFIG_FILE = os.environ.get(
    "WEB_FORM_CONFIG_FILE", "app/data/web-form-config.json"
)
MAX_FORM_CONFIG_BYTES = 256 * 1024


def _safe_next(value: str) -> str:
    value = (value or "/").strip()
    if not value.startswith("/") or value.startswith("//"):
        return "/"
    if any(char in value for char in "\r\n\x00"):
        return "/"
    return value


def _client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def _is_https(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    return (forwarded or request.url.scheme).lower() == "https"


def _signature(expires_at: int) -> str:
    return hmac.new(
        WEB_AUTH_KEY.encode("utf-8"),
        str(expires_at).encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _valid_session(token: str) -> bool:
    if not WEB_AUTH_KEY or not token:
        return False
    try:
        expires_text, signature = token.split(".", 1)
        expires_at = int(expires_text)
    except (ValueError, TypeError):
        return False
    if expires_at < int(time.time()):
        return False
    return hmac.compare_digest(signature, _signature(expires_at))


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    attempts = _failed_attempts[ip]
    while attempts and now - attempts[0] > ATTEMPT_WINDOW:
        attempts.popleft()
    return len(attempts) >= MAX_ATTEMPTS


def _record_failure(ip: str) -> None:
    _failed_attempts[ip].append(time.monotonic())


def _login_html(next_url: str, error: str = "", status_code: int = 200) -> HTMLResponse:
    safe_next = html.escape(_safe_next(next_url), quote=True)
    error_html = f'<div class="error">{html.escape(error)}</div>' if error else ""
    configured_html = "" if WEB_AUTH_KEY else (
        '<div class="error">服务端尚未配置 MIHOMO_SECRET，请先修改 .env 并重启 zurl。</div>'
    )
    content = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>docker-clash 登录</title>
  <style>
    *{{box-sizing:border-box}} body{{margin:0;min-height:100vh;display:grid;place-items:center;padding:20px;
    color:#e5e7eb;background:radial-gradient(circle at top,#1e3a5f,#0f172a 48%,#020617);font-family:system-ui,sans-serif}}
    main{{width:min(400px,100%);padding:32px;border:1px solid #334155;border-radius:18px;background:rgba(15,23,42,.92);
    box-shadow:0 24px 70px rgba(0,0,0,.45)}} h1{{margin:0 0 8px;font-size:25px}} p{{margin:0 0 24px;color:#94a3b8}}
    label{{display:block;margin-bottom:8px;font-size:14px}} input{{width:100%;padding:12px 14px;color:#f8fafc;background:#020617;
    border:1px solid #475569;border-radius:10px;font-size:16px;outline:none}} input:focus{{border-color:#38bdf8;box-shadow:0 0 0 3px rgba(56,189,248,.15)}}
    button{{width:100%;margin-top:16px;padding:12px;border:0;border-radius:10px;background:#0ea5e9;color:white;font-size:16px;font-weight:650;cursor:pointer}}
    button:hover{{background:#0284c7}} .error{{margin:0 0 16px;padding:10px 12px;border-radius:9px;color:#fecaca;background:#7f1d1d}}
  </style>
</head>
<body><main>
  <h1>docker-clash</h1><p>请输入访问密钥后继续</p>
  {configured_html}{error_html}
  <form method="post" action="/gateway/login">
    <input type="hidden" name="next" value="{safe_next}">
    <label for="key">访问密钥</label>
    <input id="key" name="key" type="password" required autofocus autocomplete="current-password">
    <button type="submit">登录</button>
  </form>
</main></body></html>"""
    return HTMLResponse(
        content,
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        },
    )


async def auth(request: Request) -> Response:
    if not WEB_AUTH_ENABLED:
        return Response(status_code=204)
    if _valid_session(request.cookies.get(COOKIE_NAME, "")):
        return Response(status_code=204)
    return Response(status_code=401, headers={"Cache-Control": "no-store"})


async def login_page(request: Request) -> Response:
    next_url = _safe_next(request.query_params.get("next", "/"))
    if not WEB_AUTH_ENABLED:
        return RedirectResponse(next_url, status_code=303)
    if _valid_session(request.cookies.get(COOKIE_NAME, "")):
        return RedirectResponse(next_url, status_code=303)
    return _login_html(next_url)


async def login(request: Request) -> Response:
    form = await request.form()
    next_url = _safe_next(str(form.get("next", "/")))
    if not WEB_AUTH_ENABLED:
        return RedirectResponse(next_url, status_code=303)
    supplied_key = str(form.get("key", ""))
    ip = _client_ip(request)

    if not WEB_AUTH_KEY:
        return _login_html(next_url, "服务端尚未配置访问密钥。", status_code=503)
    if _rate_limited(ip):
        return _login_html(next_url, "尝试次数过多，请 5 分钟后再试。", status_code=429)
    if not hmac.compare_digest(supplied_key, WEB_AUTH_KEY):
        _record_failure(ip)
        return _login_html(next_url, "访问密钥错误。", status_code=401)

    _failed_attempts.pop(ip, None)
    expires_at = int(time.time()) + WEB_AUTH_TTL
    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        f"{expires_at}.{_signature(expires_at)}",
        max_age=WEB_AUTH_TTL,
        httponly=True,
        secure=_is_https(request),
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


async def logout(request: Request) -> RedirectResponse:
    response = RedirectResponse(f"/login?next={quote('/', safe='')}", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/", secure=_is_https(request), samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return response


async def get_form_config(request: Request):
    if WEB_AUTH_ENABLED and not _valid_session(request.cookies.get(COOKIE_NAME, "")):
        return Response(status_code=401, headers={"Cache-Control": "no-store"})
    if not os.path.isfile(FORM_CONFIG_FILE):
        return {"Code": 1, "Message": "ok", "FormConfig": None}
    try:
        with open(FORM_CONFIG_FILE, encoding="utf-8") as file:
            config = json.load(file)
        if not isinstance(config, dict) or config.get("version") != 1:
            raise ValueError("unsupported form config")
        return {"Code": 1, "Message": "ok", "FormConfig": config}
    except Exception:
        return {"Code": 0, "Message": "读取已保存配置失败", "FormConfig": None}


async def save_form_config(request: Request):
    if WEB_AUTH_ENABLED and not _valid_session(request.cookies.get(COOKIE_NAME, "")):
        return Response(status_code=401, headers={"Cache-Control": "no-store"})
    try:
        config = await request.json()
    except Exception:
        return {"Code": 0, "Message": "配置不是有效的 JSON"}
    if not isinstance(config, dict) or config.get("version") != 1:
        return {"Code": 0, "Message": "配置版本不受支持"}
    if not isinstance(config.get("form"), dict):
        return {"Code": 0, "Message": "页面配置格式不正确"}

    content = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    if len(content.encode("utf-8")) > MAX_FORM_CONFIG_BYTES:
        return {"Code": 0, "Message": "页面配置超过 256KB 限制"}

    target_dir = os.path.dirname(FORM_CONFIG_FILE) or "."
    temp_path = ""
    try:
        os.makedirs(target_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target_dir,
            prefix=".web-form-config-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = file.name
            file.write(content)
        os.replace(temp_path, FORM_CONFIG_FILE)
        return {"Code": 1, "Message": "ok"}
    except Exception:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        return {"Code": 0, "Message": "保存页面配置失败"}
