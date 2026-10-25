# docker-clash · 订阅转换 + 短链分发自托管方案

一套 docker-compose 即可跑起的自托管 Clash 订阅服务：**订阅转换 → 短链分发 → 客户端订阅** 全链路闭环，在群晖等 NAS 或任意 Docker 主机上几分钟完成部署。

## 当前调整

已彻底移除 mihomo 容器及全部相关部件：compose 里不再有 mihomo / metacubexd 服务，nginx 去掉 `/clash/`、`/xd/`、`/apply`、`/mihomo/*` 入口，zurl 去掉 `docker.sock` 与 mihomo 配置挂载及对应后端代码（`apply_to_mihomo`、`control_mihomo` 等已删除），登录密钥变量由 `MIHOMO_SECRET` 改名为 `WEB_AUTH_KEY`。本项目的定位收敛为：**订阅转换 + 短链分发**，生成的订阅交给客户端（OpenClash / Clash Verge / mihomo 等）自行运行。7788 端口、nginx 与群晖反向代理配置不变。

分组继续由 `data/zurl/transform.yaml` 热加载：统一为一个“流媒体节点”组（`url-test` 自动择优），匹配原始名称包含“流媒体”的节点，并按名称保守排除香港、中国大陆、印度等常见 TikTok 访问受限地区；仍不区分日本、美国。该筛选不代表逐节点解锁实测。TikTok、YouTube、Netflix、DisneyPlus、HBO、PrimeVideo、AppleTV+、Emby、Bahamut 和国外媒体默认使用该组；音乐与其他分流保持原样，非标端口仍直连。`templates` 维持 `Custom_Clash.ini`、`Custom_Clash_Full.ini`，其他模板不会插入不存在的组引用。增强层会在追加自定义组后再次应用默认项，支持新建分组成为默认策略。客户端更新订阅后使用新配置。可提交的示例见 `config/zurl/transform.example.yaml`。

`data/`、实际 `.env`、订阅地址、密钥和生成配置仅保留在本地，不提交 Git。全新部署可复制 `config/zurl/transform.example.yaml` 到 `data/zurl/transform.yaml`；已有本地文件不要覆盖。

## ✨ 特性亮点

- **一键成型**：网页上填好订阅，「生成订阅链接 → 短链」，拿到可直接导入客户端的订阅地址，全程无需 SSH 登录服务器
- **多订阅聚合**：多条订阅合并转换，按提供商命名 proxy-provider；同源多账号自动加 `[提供商名称]` 节点前缀，流量来源一目了然
- **动态域名**：后端地址、短链域名全部根据当前访问地址动态生成，换域名 / 换端口 / 上 HTTPS 均零配置
- **智能订阅命名**：单订阅自动跟随提供商名，多订阅自动取 `合集`，通过 `Content-Disposition` 传给 Clash Verge 作为配置名
- **转换增强层**（zurl）：地区兼容归并（Tokyo→日本、Incheon→韩国、California→美国）、CDN/低倍率专属选择组、分组默认选中项，全部外置 `transform.yaml` 热加载
- **短链服务**：自建 zurl 短链（`/s/xxxx`），长链再长也不怕，客户端自动更新不受影响
- **安全防护**：可选 `WEB_AUTH_KEY` 网页登录（HttpOnly 长期 Cookie）、内部令牌防直连刷接口；不挂载 Docker socket
- **官方镜像优先**：SubConverter 用官方预构建镜像，本地只构建轻量前端与网关，群晖也能轻松编译

## 🚀 快速开始

```bash
# 1. 克隆并初始化配置（密钥文件不入库，从模板复制）
git clone https://github.com/yuyuan1019/docker-clash.git
cd docker-clash
cp .env.example .env

# 2. 修改安全配置
vi .env                        # 公网部署设 WEB_AUTH_ENABLED=true，并修改 ZURL_SHORT_TOKEN、WEB_AUTH_KEY

# 3. 启动（首次构建 sub-web / zurl，并拉取 subconverter 官方镜像）
docker compose up -d

# 4. 访问（默认 Web 端口 7788）
#    http://服务器IP:7788/       订阅转换
```

国内构建加速：编辑 `docker-compose.yml`，取消各服务 `args` 里的 `NPM_CONFIG_REGISTRY` / `PIP_INDEX_URL` 镜像源注释。

## 🧭 操作指南

### 日常使用（生成订阅）

1. 浏览器打开 `http://服务器IP:7788/`（订阅转换首页，端口即 `.env` 的 `WEB_PORT`）
2. 如果 `.env` 已设置 `WEB_AUTH_ENABLED=true`，输入 `WEB_AUTH_KEY` 登录（默认长期保持）；内网默认无需登录
3. 「订阅链接」处每行填一组：**提供商名称**（可选，如 `机场A`）+ 订阅链接；
   多条订阅点「添加订阅链接」增加行。填了提供商名，Clash 里的代理提供者就显示该名字。
   同一提供商有多个账号时使用唯一名称（如 `机场A-账号1`、`机场A-账号2`）；系统识别到协议和域名相同的订阅后，会自动给节点增加 `[提供商名称]` 前缀，兼容 token 位于查询参数或 URL 路径中的情况
4. 「生成类型」默认 Clash；「远程配置」默认 Custom_OpenClash_Rules（可换 Full/Fallback/GFW 等变体）；
   另提供 ACL4SSR（LoveMyself546 维护版，含 Online_Full 全量规则与 Online_Full_AdblockPlus 全量去广告）；
   Lite/Mainland 及其余 Fallback 变体、自托管 BiliHK 版均已移除。Smart 专版、Stash 和「香港/日本按提供商细分」复写版均已彻底移除。
5. 「订阅命名」紧跟「远程配置」之后默认展示：留空自动填（单订阅=提供商名，多订阅=`合集`，并自动追加所选远程配置名，如 `合集-Custom_Clash_Full`；切换远程配置或重新选择提供商会自动同步）；「更新间隔」默认 7 天
6. 首行操作按钮：点「生成订阅链接」→ 得到定制订阅长链；点「生成短链接」→ 得到 `当前域名:端口/s/xxxx`；点「复制订阅命名」可一键复制当前命名；
   「从URL解析」可把长/短链接还原回表单；生成 Clash 类型后可点「一键导入 Clash」唤起本机 Clash 客户端（已生成短链时优先导入短链）。
   “订阅命名”通过订阅响应的 `Content-Disposition` 传给 Clash Verge，长链和短链导入均会使用该名称
7. 本机不再运行代理内核，页面只负责生成订阅与短链；拿到链接后在客户端里导入即可自动更新。

页面会把订阅地址、提供商名称、远程配置和高级选项自动保存到服务器的 `data/zurl/web-form-config.json`，使用其他电脑登录同一站点时也会恢复同一份配置；生成后的长链、短链不会保存。该站点共用一份配置，多台设备修改时以最后一次保存为准。此文件包含原始订阅地址，应与 `.env` 一样妥善保护，不要提交到 Git 或公开分享。

### 客户端使用

- OpenClash / mihomo / Clash Verge 等客户端：直接用生成的订阅链接或短链，配置由客户端自动更新
- 需要 Web 面板时由客户端自带，本项目不再提供面板与内核

### 首页登录保护（内网可关闭，公网应开启）

登录保护由 `.env` 控制，登录密钥使用 `WEB_AUTH_KEY`，不会打包进前端代码。

仅在本地内网使用时，保持默认配置即可直接打开首页：

```dotenv
WEB_AUTH_ENABLED=false
```

需要从公网访问时，务必启用登录并把默认密钥改为足够长的随机字符串：

```dotenv
WEB_AUTH_ENABLED=true
WEB_AUTH_TTL=315360000
WEB_AUTH_KEY=请替换为足够长的随机字符串
```

修改后重新构建 zurl，并重启 nginx 使认证配置生效：

```bash
docker compose up -d --build zurl
docker compose restart nginx
```

登录 Cookie 使用 HttpOnly，默认有效 10 年（由 `WEB_AUTH_TTL` 调整）；访问 `/logout` 可退出登录。修改 `WEB_AUTH_KEY` 会立即使所有旧登录失效。
`/subapi/` 订阅转换结果和 `/s/` 短链接始终公开，确保代理客户端可以自动更新；首页与管理操作只在开关开启时要求登录。

### 运维操作

```bash
docker compose up -d          # 启动/更新（配置变更后）
docker compose stop           # 停止全部服务（数据保留在 ./data）
docker compose start          # 恢复
docker compose logs -f zurl   # 看某个服务日志（zurl/subconverter/nginx...）
docker compose pull && docker compose up -d   # 升级 subconverter 官方镜像
# 本地构建的前端/后端改了代码后：
docker compose build sub-web zurl && docker compose up -d
```

## 🏗️ 架构

**只对外暴露一个端口**：7788（nginx 统一网关，可用 `.env` 的 `WEB_PORT` 修改）：

```
http://域名/         → sub-web-modify      订阅转换前端（本地构建）
http://域名/subapi/  → SubConverter-Extended 订阅转换后端（官方镜像）
http://域名/short    → zurl 短链生成 API（POST，nginx 注入内部令牌）
http://域名/s/xxxx   → zurl 短链 302 解析跳转
```

技术要点：

- 订阅转换界面的「后端地址」「短链选择」**默认值根据当前访问域名动态生成**
  （`window.location.origin + '/subapi'` / `'/short'`），换域名、换端口、上 HTTPS 均无需改代码。
  恢复自动保存的表单时，站内形式地址（`*/subapi`、`*/short`）会自动替换为当前访问域名：
  内网 IP 与外网域名交替访问后无需手动改地址；外部自定义后端原样保留。「从URL解析」解析出的本站后端同样处理。
- 生成的短链同样是动态的 `当前域名:端口/s/xxxx`（zurl 从反代请求头取 Host/Proto，包括非标准端口）。
- 一键导入使用 Clash Verge 支持的 `clash://install-config?url=...` 格式；zurl 会转发 SubConverter 的
  `Content-Disposition`，上游未返回时根据 `filename` 参数生成该响应头，使页面“订阅命名”成为客户端配置名称。
- 部署在 HTTPS 反向代理后时，nginx 会保留外层 `X-Forwarded-Proto: https`，长链、短链及登录 Cookie 均使用外部协议。

### 转换增强层（zurl transform）

- 所有 `/subapi/sub` Clash 转换都会经过统一地区兼容层：
  `Tokyo` 归入日本、`Incheon` 归入韩国、`California` 归入美国，并同步从“其他地区”及兜底候选中排除。
- 默认不追加任何自定义分组，保持远程模板（GitHub 仓库 `cfg` 目录的 ini）原样；
  如需追加自定义组，可在 `data/zurl/transform.yaml`（模板：`config/zurl/transform.example.yaml`）
  的 `custom_groups` 中自行定义，修改保存后下次转换即生效，无需重建/重启容器。
  机场订阅按 proxy-provider filter 在运行时筛选，静态节点直接点名。
- 默认保持远程模板原样，仅对指定项按需覆盖默认出口（mihomo select 组首项即默认）：
  - `🔀 非标端口` → `🎯 全球直连`（避免非 80/443 端口的大流量/下载走代理）。
  - `💬 即时通讯`、`🌐 社交媒体`、`🚀 GitHub`、`🎮 Steam`、`🎮 游戏平台` → `🇭🇰 香港节点`。
  - `📢 谷歌FCM`、`🇬 谷歌服务`、`🤖 ChatGPT` → `🇸🇬 新加坡节点`。
  - `🤖 AI服务`（及 `_Full` 的 `🤖 国外AI服务`） → `🇯🇵 日本节点`。
  - `🍎 苹果服务`、`Ⓜ️ 微软服务`、`🚀 测速工具`、`🐟 漏网之鱼` → `🚀 手动选择`。
  如需调整其他分组，可在 `data/zurl/transform.yaml` 的 `group_defaults` 中
  自行配置（模板：`config/zurl/transform.example.yaml`），支持热加载。
  对全部远程配置变体（Custom_Clash / _Full / _Fallback / _GFW）统一生效：
  `_Fallback` 的 fallback 组同样把目标组置为第一顺位（主节点）；目标组在模板中
  不存在时跳过、不插入悬空引用。
- 多个 `proxy-provider` 的订阅地址具有相同协议和域名时，视为同一来源的不同账号；路径和查询参数中的 token 均不参与比较，
  并自动通过 `override.additional-prefix` 给节点增加 `[提供商名称]` 前缀，便于在总地区组、连接和日志中区分实际流量来源。不同来源的节点名称保持不变。
- 当前 `custom_groups`：按需自定义节点组（当前为空，完全遵循上游远程配置的各服务分流设定）。

## 📁 目录说明

| 路径 | 说明 |
|---|---|
| `sub-web-modify/` | 订阅转换前端（已改为动态域名默认值） |
| `SubConverter-Extended/` | 转换后端源码（默认用官方镜像；`base/pref.toml` 已挂载，可自行定制） |
| `zurl/` | 短链服务（新增 `app/api/compat.py` 兼容层：`POST /short`；另含网关登录与表单保存） |
| `nginx/templates/` | 网关配置（envsubst 模板） |
| `config/zurl/transform.example.yaml` | 转换增强层配置模板（复制到 `data/zurl/transform.yaml` 生效） |
| `data/` | 运行数据（zurl sqlite/redis、网页表单自动保存） |

## 🔧 对上游项目的修改清单

- **sub-web-modify** `src/views/Subconverter.vue`
  - 新增 `siteOrigin/localBackend/localShort` 动态常量
  - 后端地址、短链选择默认项改为本站动态地址（下拉列表第一项）
  - 默认远程配置改为 Custom_OpenClash_Rules（jsDelivr CDN 地址）
  - `makeUrl`/`makeShortUrl` 兜底地址改为本站动态地址
  - `getBackendVersion` 提示语通用化；`download.html` 链接改为跟随当前协议
  - 「订阅命名」移至「远程配置」之后默认展示；提供商名称被修改时自动同步一次命名
  - 移除「自定义配置」按钮及远程配置上传/JS 排序/JS 筛选弹窗及配套死代码
  - 修复「从URL解析」因未定义变量 `builtInMode` 导致解析中断、弹窗不关闭、订阅命名不同步的问题
  - 「从URL解析」支持带 `/subapi` 前缀的本站链接；解析出的本站后端地址跟随当前访问域名
  - 后端地址/短链在恢复自动保存表单时自动跟随当前访问域名（内外网交替访问后自动替换，外部自定义后端保留）
  - 操作按钮重排：首行 生成订阅链接/生成短链接/复制订阅命名/从URL解析/一键导入 Clash（统一尺寸）；
    移除「更新并应用配置」与 mihomo 开/关按钮（本机不再运行内核）
  - `Dockerfile` 增加 `NPM_CONFIG_REGISTRY` 构建参数；补充 `.dockerignore`
- **zurl**
  - 新增 `app/api/compat.py`：myurls 风格 `POST /short`（base64 longUrl + 可选 shortKey），
    返回 `{Code, Message, ShortUrl}`；ShortUrl 按请求头动态拼接 `/s/` 前缀
  - 已删除 `POST /apply`、`GET /mihomo/status`、`POST /mihomo/panel-url`、`POST /mihomo/latest-config`、
    `POST /mihomo/{start,stop}` 及底层 `apply_to_mihomo` / `control_mihomo` / `_docker_request` 等实现
  - `GET/POST /gateway/form-config`：网页表单自动保存与恢复
  - 转换增强层：地区归并、自定义组 `custom_groups`、默认选中项 `group_defaults`（均默认关闭，`transform.yaml` 热加载开启）
  - `app/routers/routers.py` 注册 `/short` 路由；`DENY_SHORT_URLS` 增加 `short`、`s`、`apply`、`mihomo`（保留词，仅用于短链后缀避让）
  - `Dockerfile` 增加 `PIP_INDEX_URL` 构建参数；`requirements.txt` 增加 `pyyaml`；补充 `.dockerignore`
- **SubConverter-Extended**：无代码修改，仅复制 `base/pref.example.toml` → `base/pref.toml` 用于挂载

## 🔒 安全提示

1. `.env` 的 `ZURL_SHORT_TOKEN` 务必修改（它防止绕过 nginx 直连 zurl 刷短链；
   经 nginx 的 `/short` 本身是公开的，与公共 sub-web 行为一致）。
2. `.env` 的 `WEB_AUTH_KEY` 即首页登录密钥，公网部署务必改为足够长的随机字符串（默认留空即无法登录）。
3. zurl 不再挂载 `/var/run/docker.sock`；仍请勿把 zurl 的 3080 端口直接暴露到公网（默认不映射，仅经 nginx 受控路径访问）。
4. 如需 HTTPS，把域名指到 nginx（默认 :7788，或改 `WEB_PORT` 为 80），前端/短链会自动跟随 `https://`。

## 🙏 致谢 / 上游项目

| 项目 | 用途 |
|---|---|
| [sub-web-modify](https://github.com/youshandefeiyang/sub-web-modify)（基于 [CareyWang/sub-web](https://github.com/CareyWang/sub-web)） | 订阅转换前端 |
| [SubConverter-Extended](https://github.com/aethersailor/subconverter-extended)（[tindy2013/subconverter](https://github.com/tindy2013/subconverter) 扩展版） | 订阅转换后端 |
| [zurl](https://github.com/helloxz/zurl) | 短链服务（深度定制） |
| [Custom_OpenClash_Rules](https://github.com/Aethersailor/Custom_OpenClash_Rules) | 默认远程配置 / 规则集 |
