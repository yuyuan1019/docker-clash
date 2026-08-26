from app.api.sys import *
from app.config import templates
from app.middleware.deny import deny_uas
from app.models.options import Options
import json

class IndexAPI:
    async def index(self, request: Request):
        # 调用deny_uas中间件检查User-Agent
        if await deny_uas(request):
            return templates.TemplateResponse("error_pages/deny.html", {"request": request})
        
        # 获取版本号和版本日期
        versionInfo = {
            "version": VERSION,
            "version_date": VERSION_DATE
        }
        # 默认站点信息，确保变量始终已定义
        site_info = {
            "title": "Zurl",
            "keywords": "zurl,短链服务,短链接",
            "description": "Zurl是一款轻量级短链服务，使用FastAPI开发。",
            "header": "",
            "footer": ""
        }
        # 获取站点信息
        site_str = Options.get_option("site_info")
        # 转为json
        if site_str:
            try:
                parsed = json.loads(site_str)
                if isinstance(parsed, dict):
                    # 合并配置，保留默认缺失字段
                    site_info.update(parsed)
            except (TypeError, ValueError, json.JSONDecodeError):
                # 解析失败保持默认
                pass
        
        # 渲染index.html模板
        return templates.TemplateResponse("index.html", {"request": request, "versionInfo": versionInfo, "site_info": site_info})
