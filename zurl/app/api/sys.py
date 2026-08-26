from app.config import get_config
from app.utils.helper import *

# 版本号
VERSION = "1.2.2"
# 版本日期
VERSION_DATE = "20260327"

class SysAPI:

    def app_info(self):
        data = {
            "username": get_config()["user"]["USERNAME"],
            "email": get_config()["user"]["EMAIL"],
            "version": VERSION,
            "version_date": VERSION_DATE
        }
        return show_json(200, "success", data)
    
    async def siteInfo(self):
        username = get_config()["user"]["USERNAME"]
        password = get_config()["user"]["PASSWORD"]

        # 如果任意一个为空
        if not username or not password:
            is_init = "no"
        else:
            is_init = "yes"

        return show_json(200, "success", {
            "is_init": is_init
        })