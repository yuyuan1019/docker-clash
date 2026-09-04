# docker-clash · 订阅转换 + 代理内核一体化自托管方案

一套 docker-compose 即可跑起的自托管 Clash 订阅服务：**订阅转换 → 短链分发 → 配置应用 → 内核运行 → 面板管理** 全链路闭环，在群晖等 NAS 或任意 Docker 主机上几分钟完成部署。

## ✨ 特性亮点

- **一键闭环**：网页上填好订阅，「生成订阅链接 → 短链 → 更新并应用配置」，mihomo 内核即刻按新配置运行，全程无需 SSH 登录服务器
- **多订阅聚合**：多条订阅合并转换，按提供商命名 proxy-provider；同源多账号自动加 `[提供商名称]` 节点前缀，流量来源一目了然
- **动态域名**：后端地址、短链域名全部根据当前访问地址动态生成，换域名 / 换端口 / 上 HTTPS 均零配置
- **智能订阅命名**：单订阅自动跟随提供商名，多订阅自动取 `合集`，通过 `Content-Disposition` 传给 Clash Verge 作为配置名
- **转换增强层**（zurl）：地区兼容归并（Tokyo→日本、Incheon→韩国、California→美国）、CDN/低倍率专属选择组、分组默认选中项，全部外置 `transform.yaml` 热加载
- **内核可控**：「开启/关闭 mihomo」按状态切换显示，30 秒自动刷新运行状态；配置应用失败自动回滚
- **短链服务**：自建 zurl 短链（`/s/xxxx`），长链再长也不怕，客户端自动更新不受影响
- **安全防护**：可选 `MIHOMO_SECRET` 网页登录（HttpOnly 长期 Cookie）、内部令牌防直连刷接口、Docker socket 受控使用
- **官方镜像优先**：SubConverter / mihomo / metacubexd 均用官方预构建镜像，本地只构建轻量前端与网关，群晖也能轻松编译

## 🚀 快速开始

```bash
# 1. 克隆并初始化配置（密钥文件不入库，从模板复制）
git clone https://github.com/yuyuan1019/docker-clash.git
cd docker-clash
cp .env.example .env
cp config/mihomo/config.example.yaml config/mihomo/config.yaml

# 2. 修改安全配置
vi .env                        # 公网部署设 WEB_AUTH_ENABLED=true，并修改 ZURL_SHORT_TOKEN、MIHOMO_SECRET
vi config/mihomo/config.yaml   # secret 与 .env 的 MIHOMO_SECRET 保持一致

# 3. 启动（首次构建 sub-web / zurl，并拉取 metacubexd 等官方镜像）
docker compose up -d

# 4. 访问（默认 Web 端口 7788）
#    http://服务器IP:7788/       订阅转换
#    http://服务器IP:7788/xd/    metacubexd 官方面板
```

国内构建加速：编辑 `docker-compose.yml`，取消各服务 `args` 里的 `NPM_CONFIG_REGISTRY` / `PIP_INDEX_URL` 镜像源注释。

## 🧭 操作指南

### 日常使用（生成订阅并启用）

1. 浏览器打开 `http://服务器IP:7788/`（订阅转换首页，端口即 `.env` 的 `WEB_PORT`）
2. 如果 `.env` 已设置 `WEB_AUTH_ENABLED=true`，输入 `MIHOMO_SECRET` 登录（默认长期保持）；内网默认无需登录
3. 「订阅链接」处每行填一组：**提供商名称**（可选，如 `机场A`）+ 订阅链接；
   多条订阅点「添加订阅链接」增加行。填了提供商名，Clash 里的代理提供者就显示该名字。
   同一提供商有多个账号时使用唯一名称（如 `机场A-账号1`、`机场A-账号2`）；系统识别到协议和域名相同的订阅后，会自动给节点增加 `[提供商名称]` 前缀，兼容 token 位于查询参数或 URL 路径中的情况
4. 「生成类型」默认 Clash；「远程配置」默认 Custom_OpenClash_Rules（可换 Full/Fallback/GFW 等变体）；
   Lite/Mainland 及其余 Fallback 变体、ACL4SSR 系列、自托管 BiliHK 版均已移除
   （COCR 默认模板已覆盖这些场景）。Smart 专版、Stash 和「香港/日本按提供商细分」复写版均已彻底移除。
5. 「订阅命名」紧跟「远程配置」之后默认展示：留空自动填（单订阅=提供商名，多订阅=`合集`，并自动追加所选远程配置名，如 `合集-Custom_Clash_Full`；切换远程配置会自动同步）；「更新间隔」默认 7 天
6. 首行操作按钮：点「生成订阅链接」→ 得到定制订阅长链；再点「生成短链接」→ 得到 `当前域名:端口/s/xxxx`；
   「从URL解析」可把长/短链接还原回表单；生成 Clash 类型后可点「一键导入 Clash」唤起本机 Clash 客户端（已生成短链时优先导入短链）。
   “订阅命名”通过订阅响应的 `Content-Disposition` 传给 Clash Verge，长链和短链导入均会使用该名称
7. 次行操作按钮：「更新并应用配置」一键完成两步：先据当前订阅生成候选 `latest.yaml`，成功后自动将其切换为 `config.yaml` 并重启 mihomo（已关闭时则启动）；
   mihomo 控制按钮按状态切换：运行中显示「关闭 mihomo」（需确认），已停止显示「开启 mihomo」（直接启动）；
   状态标签（绿=运行中）每 30 秒自动刷新，点击可手动刷新；「打开面板」新标签页进入 metacubexd

页面会把订阅地址、提供商名称、远程配置和高级选项自动保存到服务器的 `data/zurl/web-form-config.json`，使用其他电脑登录同一站点时也会恢复同一份配置；生成后的长链、短链不会保存。该站点共用一份配置，多台设备修改时以最后一次保存为准。此文件包含原始订阅地址，应与 `.env` 一样妥善保护，不要提交到 Git 或公开分享。

### 客户端使用

- OpenClash / mihomo 系客户端：直接用生成的订阅链接或短链，配置由客户端自动更新
- 本机 mihomo 作为局域网代理网关：7890 端口默认已映射，
  其他设备代理直接设置为 `服务器IP:7890`（不需要时到 `docker-compose.yml` 注释掉即可）
- 面板首次使用：后端地址填写 `当前访问地址/clash`，密钥填写 `.env` 的 `MIHOMO_SECRET`；连接信息会保存在浏览器中。
  也可在 `.env` 的 `DEFAULT_BACKEND_URL` 中预填完整后端地址

### 首页登录保护（内网可关闭，公网应开启）

登录保护由 `.env` 控制，登录密钥直接复用 `MIHOMO_SECRET`，不会打包进前端代码。

仅在本地内网使用时，保持默认配置即可直接打开首页：

```dotenv
WEB_AUTH_ENABLED=false
```

需要从公网访问时，务必启用登录并把默认密钥改为足够长的随机字符串：

```dotenv
WEB_AUTH_ENABLED=true
WEB_AUTH_TTL=315360000
MIHOMO_SECRET=请替换为足够长的随机字符串
```

修改后重新构建 zurl，并重启 nginx 使认证配置生效：

```bash
docker compose up -d --build zurl
docker compose restart nginx
```

登录 Cookie 使用 HttpOnly，默认有效 10 年（由 `WEB_AUTH_TTL` 调整）；访问 `/logout` 可退出登录。修改 `MIHOMO_SECRET` 会立即使所有旧登录失效。
`/subapi/` 订阅转换结果和 `/s/` 短链接始终公开，确保代理客户端可以自动更新；首页、面板、Clash 控制 API 和管理操作只在开关开启时要求登录。

### 运维操作

```bash
docker compose up -d          # 启动/更新（配置变更后）
docker compose stop           # 停止全部服务（数据保留在 ./data）
docker compose start          # 恢复
docker compose logs -f zurl   # 看某个服务日志（zurl/subconverter/mihomo/nginx...）
docker compose pull && docker compose up -d   # 升级 subconverter/mihomo/metacubexd 官方镜像
# 本地构建的前端/后端改了代码后：
docker compose build sub-web zurl && docker compose up -d
```

## 🏗️ 架构

**对外暴露两个端口**：7788（nginx 统一网关，可用 `.env` 的 `WEB_PORT` 修改）和 7890（mihomo 混合代理，局域网网关用）：

```
http://域名/         → sub-web-modify      订阅转换前端（本地构建）
http://域名/subapi/  → SubConverter-Extended 订阅转换后端（官方镜像）
http://域名/short    → zurl 短链生成 API（POST，nginx 注入内部令牌）
http://域名/apply    → 只生成 mihomo 候选配置 latest.yaml（POST，同上防护）
http://域名/s/xxxx   → zurl 短链 302 解析跳转
http://域名/xd/      → metacubexd 官方面板镜像（nginx 适配 /xd/ 子路径）
http://域名/clash/   → mihomo Clash API（含 WebSocket，面板连接用）
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
- 「更新并应用配置」按钮一键串联两步：先拉取转换结果写入候选 `config/mihomo/latest.yaml`（不影响当前运行配置），
  再把 `latest.yaml` 原地写入 `config.yaml` 并重启 mihomo；容器已关闭时则启动，启动失败会回滚原配置。
- mihomo 控制按钮经 Docker socket（`/var/run/docker.sock`）启停容器；状态标签每 30 秒自动刷新。

### 转换增强层（zurl transform）

- 所有 `/subapi/sub` Clash 转换都会经过统一地区兼容层：
  `Tokyo` 归入日本、`Incheon` 归入韩国、`California` 归入美国，并同步从“其他地区”及兜底候选中排除。
- 默认不追加任何自定义分组，保持远程模板（GitHub 仓库 `cfg` 目录的 ini）原样；
  如需追加自定义组，可在 `data/zurl/transform.yaml`（模板：`config/zurl/transform.example.yaml`）
  的 `custom_groups` 中自行定义，修改保存后下次转换即生效，无需重建/重启容器。
  机场订阅按 proxy-provider filter 在运行时筛选，静态节点直接点名。
- 默认不调整任何分组的默认选中项，保持远程模板原样（mihomo select 组首项即默认）；
  如需置顶指定分组的默认项，可在 `data/zurl/transform.yaml` 的 `group_defaults` 中
  自行配置（模板：`config/zurl/transform.example.yaml`），同样支持热加载。
  对全部远程配置变体（Custom_Clash / _Full / _Fallback / _GFW）统一生效：
  `_Fallback` 的 fallback 组同样把目标组置为第一顺位（主节点）；目标组在模板中
  不存在时跳过、不插入悬空引用。
- 当前 `group_defaults` 生效的服务分流默认出口（2026-09-04 起）：
  ChatGPT / AI服务 / 谷歌服务 / 谷歌FCM → 🇸🇬 新加坡节点；
  TikTok / YouTube → 🇺🇸 美国节点；
  微软服务 / 苹果服务 / 测速工具 → 🚀 手动选择
  （注：`_Fallback` 变体无「🚀 手动选择」组，后三者在该变体中保持 🎯 全球直连
  默认，仍为手动可选，仅默认项不受影响）。
- 多个 `proxy-provider` 的订阅地址具有相同协议和域名时，视为同一来源的不同账号；路径和查询参数中的 token 均不参与比较，
  并自动通过 `override.additional-prefix` 给节点增加 `[提供商名称]` 前缀，便于在总地区组、连接和日志中区分实际流量来源。不同来源的节点名称保持不变。
- 当前 `custom_groups` 追加的节点组：`🎬 流媒体`（节点名含「流媒体」，type=select），
  挂入 YouTube / TikTok / Netflix / DisneyPlus / HBO / PrimeVideo / AppleTV+ / Emby / Spotify / Bahamut / 国外媒体 的可选列表；
  其中 YouTube / TikTok 默认「🇺🇸 美国节点」、**第二顺位即 🎬 流媒体**（`attach_after`，Fallback 变体中即故障转移的第二备份）。
  `attach_after` 仅对 `attach_to` 目标组生效，锚点成员不存在时退化为追加末尾。

## 📁 目录说明

| 路径 | 说明 |
|---|---|
| `sub-web-modify/` | 订阅转换前端（已改为动态域名默认值） |
| `SubConverter-Extended/` | 转换后端源码（默认用官方镜像；`base/pref.toml` 已挂载，可自行定制） |
| `zurl/` | 短链服务（新增 `app/api/compat.py` 兼容层：`POST /short`、`/apply`、mihomo 控制） |
| `nginx/templates/` | 网关配置（envsubst 模板） |
| `config/mihomo/config.yaml` | mihomo 内核配置 |
| `config/zurl/transform.example.yaml` | 转换增强层配置模板（复制到 `data/zurl/transform.yaml` 生效） |
| `data/` | 运行数据（zurl sqlite/redis、mihomo 缓存、网页表单自动保存） |

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
  - 操作按钮重排：首行 生成订阅链接/生成短链接/从URL解析/一键导入 Clash（统一尺寸）；
    「生成最新配置」+「切换当前配置」合并为「更新并应用配置」；mihomo 按钮按状态显示开启/关闭
  - `Dockerfile` 增加 `NPM_CONFIG_REGISTRY` 构建参数；补充 `.dockerignore`
- **zurl**
  - 新增 `app/api/compat.py`：myurls 风格 `POST /short`（base64 longUrl + 可选 shortKey），
    返回 `{Code, Message, ShortUrl}`；ShortUrl 按请求头动态拼接 `/s/` 前缀
  - `POST /apply` 只生成候选 `latest.yaml`；`POST /mihomo/latest-config` 才切换当前配置并重启 mihomo；
    `POST /mihomo/{start,stop}` 经 Docker socket 启停容器
  - `GET/POST /gateway/form-config`：网页表单自动保存与恢复
  - 转换增强层：地区归并、自定义组 `custom_groups`、默认选中项 `group_defaults`（均默认关闭，`transform.yaml` 热加载开启）
  - `app/routers/routers.py` 注册 `/short`、`/apply` 路由；`DENY_SHORT_URLS` 增加 `short`、`s`、`apply`
  - `Dockerfile` 增加 `PIP_INDEX_URL` 构建参数；`requirements.txt` 增加 `pyyaml`；补充 `.dockerignore`
- **SubConverter-Extended**：无代码修改，仅复制 `base/pref.example.toml` → `base/pref.toml` 用于挂载

## 🔒 安全提示

1. `.env` 的 `ZURL_SHORT_TOKEN` 务必修改（它防止绕过 nginx 直连 zurl 刷短链；
   经 nginx 的 `/short` 本身是公开的，与公共 sub-web 行为一致）。
2. `config/mihomo/config.yaml` 的 `secret` 默认 `yuan`（与 `.env` 的 `MIHOMO_SECRET` 一致），
   公网部署务必同时修改这两处，`/clash` 即面板控制 API。
3. 7890 代理端口默认对局域网开放，请注意来源限制；不需要时注释掉端口映射。
4. zurl 容器挂载了 `/var/run/docker.sock` 用于启停 mihomo，socket 权限等同宿主机 root，
   请勿把 zurl 的 3080 端口直接暴露到公网（默认不映射，仅经 nginx 受控路径访问）。
5. 如需 HTTPS，把域名指到 nginx（默认 :7788，或改 `WEB_PORT` 为 80），前端/短链会自动跟随 `https://`。

## 🙏 致谢 / 上游项目

| 项目 | 用途 |
|---|---|
| [sub-web-modify](https://github.com/youshandefeiyang/sub-web-modify)（基于 [CareyWang/sub-web](https://github.com/CareyWang/sub-web)） | 订阅转换前端 |
| [SubConverter-Extended](https://github.com/aethersailor/subconverter-extended)（[tindy2013/subconverter](https://github.com/tindy2013/subconverter) 扩展版） | 订阅转换后端 |
| [zurl](https://github.com/helloxz/zurl) | 短链服务（深度定制） |
| [mihomo](https://github.com/MetaCubeX/mihomo) | Clash.Meta 代理内核 |
| [metacubexd](https://github.com/MetaCubeX/metacubexd) | 官方 Web 面板 |
| [Custom_OpenClash_Rules](https://github.com/Aethersailor/Custom_OpenClash_Rules) | 默认远程配置 / 规则集 |
