from fastapi import APIRouter,Form, Request, Depends, UploadFile, File
from fastapi.responses import PlainTextResponse
from app.api.index import IndexAPI
from app.api.option import OptionAPI
from app.api.sys import SysAPI
from app.api.user import UserAPI, UserItem
from app.api.url import *
from app.api.compat import CompatAPI
from app.api.sub_providers import SubProviderAPI
from app.api import gateway_auth
from app.middleware.auth import get_current_session
from app.models.sessions import Sessions
from app.middleware.click import update_click_counts
from app.middleware.deny import deny_uas
from app.config import templates

# 创建 APIRouter 实例
router = APIRouter()

indexAPI = IndexAPI()
userAPI = UserAPI()
urlAPI = UrlAPI()
compatAPI = CompatAPI()
sysAPI = SysAPI()
optionAPI = OptionAPI()
subProviderAPI = SubProviderAPI()

# 公网入口认证（仅供 nginx auth_request 与登录页调用）
@router.get("/gateway/auth")
async def gateway_auth_check(request: Request):
    return await gateway_auth.auth(request)

@router.get("/gateway/login-page")
async def gateway_login_page(request: Request):
    return await gateway_auth.login_page(request)

@router.post("/gateway/login")
async def gateway_login(request: Request):
    return await gateway_auth.login(request)

@router.get("/gateway/logout")
async def gateway_logout(request: Request):
    return await gateway_auth.logout(request)

@router.get("/gateway/form-config")
async def gateway_get_form_config(request: Request):
    return await gateway_auth.get_form_config(request)

@router.post("/gateway/form-config")
async def gateway_save_form_config(request: Request):
    return await gateway_auth.save_form_config(request)

# 提供商字典（订阅转换页面，保存于数据库）
@router.get("/gateway/sub-providers")
async def gateway_list_sub_providers(request: Request):
    return await subProviderAPI.list_providers(request)

@router.post("/gateway/sub-providers")
async def gateway_save_sub_provider(request: Request):
    return await subProviderAPI.save_provider(request)

@router.post("/gateway/sub-providers/delete")
async def gateway_delete_sub_provider(request: Request):
    return await subProviderAPI.delete_provider(request)

# 订阅转换页面表单中的当前订阅链接（供 subs-check 的 sub-urls-remote 动态读取）
@router.get("/sub-links")
async def sub_links(request: Request):
    return PlainTextResponse(gateway_auth.sub_links_for_subscheck())

# 首页
@router.get("/")
async def index(request: Request):
    return await indexAPI.index(request=request)

# 短链接跳转
@router.get("/{short_url}")
@router.head("/{short_url}")
async def redirect_to_long_url(
    short_url: str, 
    request: Request = None
):
    # print(f"收到短链接请求: {short_url}")  # 添加这行调试
    return await urlAPI.redirect(short_url=short_url, request=request)

# myurls 风格兼容短链接口（供 sub-web-modify 前端调用，令牌由 nginx 注入）
@router.post("/short")
async def compat_short_create(request: Request, longUrl: str = Form(...), shortKey: str = Form("")):
    return await compatAPI.short_create(long_url_b64=longUrl, short_key=shortKey, request=request)

# 生成最新候选配置（不更新或重载 mihomo，令牌由 nginx 注入）
@router.post("/apply")
async def compat_apply_to_mihomo(request: Request, subUrl: str = Form(...)):
    return await compatAPI.apply_to_mihomo(sub_url=subUrl, request=request)

# 生成和读取「净化并生成」的静态 Clash 节点快照。
# POST 受网关登录与内部令牌保护；GET 保持免登录，供 Clash/OpenClash 直接订阅。
@router.post("/clean-snapshot")
async def clean_snapshot_create(request: Request):
    return await compatAPI.clean_snapshot_create(request=request)

@router.get("/clean-snapshot/{snapshot_id}.yaml")
async def clean_snapshot_get(snapshot_id: str):
    return await compatAPI.clean_snapshot_get(snapshot_id=snapshot_id)

# nginx 将普通 /subapi/sub 定点转到这里，其余 SubConverter API 保持直连。
@router.get("/subapi-compat/sub")
async def compat_subscription(request: Request):
    return await compatAPI.subscription_compat(request=request)

# 查询 mihomo 容器运行状态（GET，令牌由 nginx 注入）
@router.get("/mihomo/status")
async def compat_mihomo_status(request: Request):
    return await compatAPI.mihomo_status(request=request)

# 生成带环境密钥的 metacubexd 面板深链接
@router.post("/mihomo/panel-url")
async def compat_mihomo_panel_url(request: Request):
    return await compatAPI.panel_url(request=request)

# 把最新候选配置切换为当前配置，然后重启/启动 mihomo
@router.post("/mihomo/latest-config")
async def compat_activate_latest_mihomo_config(request: Request):
    return await compatAPI.activate_latest_config(request=request)

# 启动/关闭 mihomo 容器（经 Docker socket，令牌由 nginx 注入）
# 通配 action 路由必须放在上述具体端点之后，避免拦截它们。
@router.post("/mihomo/{action}")
async def compat_control_mihomo(action: str, request: Request):
    return await compatAPI.control_mihomo(action=action, request=request)

# 登录接口
@router.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...), request: Request = None):
    return userAPI.login(username=username, password=password, request=request)

# 短链接接口
@router.post("/api/shorten_url")
async def shorten_url(item: UrlItem, request: Request,session = Depends(get_current_session)):
    return await urlAPI.shorten_url(item=item, request=request)

# 导入接口
@router.post("/api/import")
async def import_urls(file: UploadFile = File(...), session = Depends(get_current_session)):
    return await urlAPI.import_data(file=file)

# 获取链接列表
@router.get("/api/urls")
async def get_urls(request: Request, session = Depends(get_current_session),page: int = 1, limit: int = 10):
    return urlAPI.get_list(page=page, limit=limit)

# 批量删除短链接
@router.post("/api/delete/urls")
async def batch_delete_urls(item: UrlDeleteItem, session = Depends(get_current_session)):
    return urlAPI.batch_delete(ids=item)

# 清空所有链接
@router.post("/api/urls/clear")
async def clear_urls(session = Depends(get_current_session)):
    return urlAPI.clear_all()

# 删除单个链接
@router.post("/api/delete/url")
async def delete_url(short_url: str = Form(...), session = Depends(get_current_session)):
    return urlAPI.delete_by_short_url(short_url=short_url)

# 获取链接的标题和描述
@router.post("/api/get_url_metadata")
async def get_url_metadata(url: str = Form(...), session = Depends(get_current_session)):
    return await urlAPI.get_url_metadata(url=url)

# 获取单个链接信息
@router.post("/api/get_url_info")
async def get_url_info(short_url: str = Form(...), session = Depends(get_current_session)):
    return await urlAPI.get_by_shorten_url(short_url=short_url)

# 更新链接信息
@router.post("/api/update_url/{id}")
async def update_url(id: int, item: UrlItem, session = Depends(get_current_session)):
    return urlAPI.update_url(id=id, item=item)

# 搜索链接
@router.post("/api/search")
async def search_urls(item: UrlSearchItem, session = Depends(get_current_session)):
    return urlAPI.search_urls(item=item)

# 获取用户登录状态
@router.get("/api/user/is_login")
async def is_login(session = Depends(get_current_session)):
    return userAPI.is_login()

# 用户退出登录
@router.get("/api/user/logout")
async def logout(request: Request, session = Depends(get_current_session)):
    return await userAPI.logout(request=request)

# 用户初始化
@router.post("/api/user/init")
async def init_user(item: UserItem):
    return userAPI.init(item=item)

# 获取app信息
@router.get("/api/get/appinfo")
async def get_app_info(session = Depends(get_current_session)):
    return sysAPI.app_info()

# 获取站点状态等信息
@router.get("/api/get/siteinfo")
async def get_siteinfo():
    return await sysAPI.siteInfo()

# 生成token接口
@router.get("/api/user/create_token")
async def create_token(request: Request,session = Depends(get_current_session)):
    return await userAPI.create_token(request=request)

# 更换token接口
@router.get("/api/user/change_token")
async def change_token(request: Request, session = Depends(get_current_session)):
    return await userAPI.change_token(request=request)

# 获取API Token
@router.get("/api/user/get_token")
async def get_token(request:Request,session = Depends(get_current_session)):
    return await userAPI.get_token(request=request)

# 获取选项配置
@router.get("/api/option/get")
async def get_option(key: str, session = Depends(get_current_session)):
    return await optionAPI.get_option(key=key)

# 设置配置选项
@router.post("/api/option/set")
async def set_option(key: str = Form(...), value: str = Form(...), session = Depends(get_current_session)):
    return await optionAPI.set_option(key=key, value=value)

# 获取站点信息，不需要认证
@router.get("/api/option/get_site_info")
async def get_site_info():
    return await optionAPI.get_site_info()

# 修改密码
@router.post("/api/user/change_password")
async def change_password(old_password: str = Form(...), new_password: str = Form(...), session = Depends(get_current_session)):
    return userAPI.change_password(old_password=old_password, new_password=new_password)
