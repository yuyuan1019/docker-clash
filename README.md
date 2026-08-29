# docker-clash 一体化项目

将订阅转换、短链服务、mihomo 内核与面板整合为一个 docker-compose 项目。

## 操作指南

### 日常使用（生成订阅并启用）

1. 浏览器打开 `http://服务器IP:7788/`（订阅转换首页，端口即 `.env` 的 `WEB_PORT`）
2. 如果 `.env` 已设置 `WEB_AUTH_ENABLED=true`，输入 `MIHOMO_SECRET` 登录（默认长期保持）；内网默认无需登录
3. 「订阅链接」处每行填一组：**提供商名称**（可选，如 `机场A`）+ 订阅链接；
   多条订阅点「添加订阅链接」增加行。填了提供商名，Clash 里的代理提供者就显示该名字。
   同一提供商有多个账号时使用唯一名称（如 `机场A-账号1`、`机场A-账号2`）；系统识别到协议和域名相同的订阅后，会自动给节点增加 `[提供商名称]` 前缀，兼容 token 位于查询参数或 URL 路径中的情况
4. 「生成类型」默认 Clash；「远程配置」默认 Custom_OpenClash_Rules（可换 Full/Lite/GFW 等变体）。
   每个 Custom_Clash 版本都提供对应的`香港/日本按提供商细分`选项：它保留所选 GitHub 最新配置，
   并额外生成香港、日本的 `地区_提供商` 策略组。建议把每行的提供商名称填写为简短且唯一的简称，例如 `A`、`B`
   使用 OpenClash **Smart 内核**时，可在 `Custom_Clash Smart 专版` 分组选择对应版本；默认、Full、Lite、GFW、Mainland
   及四个 Fallback 版本均实时基于 GitHub 上游生成，不保存静态副本。Smart 配置不能用于本站官方 Mihomo 容器。
5. 「订阅命名」留空会自动填：单订阅=提供商名，多订阅=`合集`；「更新间隔」默认 7 天
6. 点「生成订阅链接」→ 得到定制订阅长链；再点「生成短链接」→ 得到 `当前域名:端口/s/xxxx`
   生成 Clash 类型后可点「一键导入 Clash」唤起本机 Clash 客户端；已生成短链时优先导入短链。
   “订阅命名”通过订阅响应的 `Content-Disposition` 传给 Clash Verge，长链和短链导入均会使用该名称
7. 主页「生成最新配置」只写入候选 `latest.yaml`；只有点击「切换当前配置」才替换 `config.yaml` 并重启 mihomo（已关闭时则启动）
8. 点卡片头右侧「打开面板」（或访问 `/xd/`）进入 metacubexd：
   - 面板使用官方预构建镜像。首次使用时，后端地址填写 `当前访问地址/clash`，密钥填写 `.env` 的 `MIHOMO_SECRET`；连接信息会保存在浏览器中
9. 不用代理时点「关闭 mihomo」即可停止内核；状态看卡片头左上角标签（绿=运行中）

页面会把订阅地址、提供商名称、远程配置和高级选项自动保存到服务器的 `data/zurl/web-form-config.json`，使用其他电脑登录同一站点时也会恢复同一份配置；生成后的长链、短链不会保存。该站点共用一份配置，多台设备修改时以最后一次保存为准。此文件包含原始订阅地址，应与 `.env` 一样妥善保护，不要提交到 Git 或公开分享。

### 客户端使用

- OpenClash / mihomo 系客户端：直接用生成的订阅链接或短链，配置由客户端自动更新
- 本机 mihomo 作为局域网代理网关：7890 端口默认已映射，
  其他设备代理直接设置为 `服务器IP:7890`（不需要时到 `docker-compose.yml` 注释掉即可）

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
`/subapi/`、`/provider-regions/` 订阅转换结果和 `/s/` 短链接始终公开，确保代理客户端可以自动更新；首页、面板、Clash 控制 API 和管理操作只在开关开启时要求登录。

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

### 部署到其他机器

```bash
git clone https://github.com/yuyuan1019/docker-clash.git
cd docker-clash
cp .env.example .env
cp config/mihomo/config.example.yaml config/mihomo/config.yaml
vi .env        # 改 ZURL_SHORT_TOKEN（随机长字符串）和 MIHOMO_SECRET
vi config/mihomo/config.yaml   # secret 与 MIHOMO_SECRET 保持一致
docker compose up -d
```

## 架构

**对外暴露两个端口**：7788（nginx 统一网关，可用 `.env` 的 `WEB_PORT` 修改）和 7890（mihomo 混合代理，局域网网关用）：

```
http://域名/         → sub-web-modify      订阅转换前端（本地构建）
http://域名/subapi/  → SubConverter-Extended 订阅转换后端（官方镜像）
http://域名/provider-regions/ → GitHub 各 Clash 版本港日提供商复写订阅（zurl 增量生成）
http://域名/smart/   → GitHub 最新配置 Smart 动态复写订阅（仅 OpenClash Smart 内核）
http://域名/smart-provider-regions/ → Smart 各版本港日按 provider 细分组合版
http://域名/short    → zurl 短链生成 API（POST，nginx 注入内部令牌）
http://域名/apply    → 只生成 mihomo 候选配置 latest.yaml（POST，同上防护）
http://域名/s/xxxx   → zurl 短链 302 解析跳转
http://域名/xd/      → metacubexd 官方面板镜像（nginx 适配 /xd/ 子路径）
http://域名/clash/   → mihomo Clash API（含 WebSocket，面板连接用）
```

- 订阅转换界面的「后端地址」「短链选择」**默认值根据当前访问域名动态生成**
  （`window.location.origin + '/subapi'` / `'/short'`），换域名、换端口、上 HTTPS 均无需改代码。
- 生成的短链同样是动态的 `当前域名:端口/s/xxxx`（zurl 从反代请求头取 Host/Proto，包括非标准端口）。
- 一键导入使用 Clash Verge 支持的 `clash://install-config?url=...` 格式；zurl 会转发 SubConverter 的
  `Content-Disposition`，上游未返回时根据 `filename` 参数生成该响应头，使页面“订阅命名”成为客户端配置名称。
- 部署在 HTTPS 反向代理后时，nginx 会保留外层 `X-Forwarded-Proto: https`，长链、短链及登录 Cookie 均使用外部协议。
- metacubexd 使用官方 `ghcr.io/metacubex/metacubexd:latest` 预构建镜像，不在群晖本地编译；
  首次连接时填写 `当前访问源/clash` 和 `MIHOMO_SECRET`。也可在 `.env` 的 `DEFAULT_BACKEND_URL` 中预填完整后端地址。
- mihomo 的 7890 代理端口默认已对局域网开放（`allow-lan: true`）；
  不需要对外提供代理时，到 `docker-compose.yml` 注释掉 mihomo 的端口映射即可。
- 「生成最新配置」只拉取转换结果并写入 `config/mihomo/latest.yaml`，不影响当前运行配置。
- 每个 Custom_Clash 和 Smart 版本都有`香港/日本按提供商细分`选项，不会复制或固定上游配置：每次订阅刷新仍由
  SubConverter 获取所选 GitHub 配置，zurl 只克隆上游香港、日本组，将 `use` 限定到单个 provider，并把派生组追加到
  可选择的策略中。GFW/GFW Fallback 上游没有地区组时，会继承其自动/故障转移参数生成港日组。
  GitHub 原版选项保持不变；普通复写订阅同样可供外部 OpenClash/Mihomo 客户端使用。
- Smart 专版同样先由 SubConverter 获取所选 GitHub `main` 分支配置，再把 `url-test` / `load-balance` 自动组动态改为
  `type: smart`，启用 `uselightgbm`、关闭本机训练数据采集，并保留 select/fallback 业务层及上游测试参数。
  Fallback 专版因此仍按上游顺序完成故障转移，内部自动组则使用 Smart 选路。该格式依赖
  [OpenClash Smart 内核](https://github.com/vernesong/OpenClash/tree/core/master/smart)，普通 Meta/Mihomo 内核不支持；
  首页“生成最新配置”会明确拒绝把 Smart 专版切换到本站官方 Mihomo 容器，避免启动失败。
- 所有 `/subapi/sub` Clash 转换和 `/provider-regions/sub` 提供商复写订阅都会经过统一地区兼容层：
  `Tokyo` 归入日本、`Incheon` 归入韩国、`California` 归入美国，并同步从“其他地区”及兜底候选中排除。
- 多个 `proxy-provider` 的订阅地址具有相同协议和域名时，视为同一来源的不同账号；路径和查询参数中的 token 均不参与比较，
  并自动通过 `override.additional-prefix` 给节点增加 `[提供商名称]` 前缀，便于在总地区组、连接和日志中区分实际流量来源。不同来源的节点名称保持不变。
- 「切换当前配置」才把 `latest.yaml` 原地写入 `config.yaml` 并重启 mihomo；
  容器已关闭时则启动，启动失败会回滚原配置。
- 「打开面板」使用浏览器原生新标签页进入同源 `/xd/` 官方面板；连接地址和密钥由用户在官方面板中填写并保存。
- 设置 `WEB_AUTH_ENABLED=true` 后，公网入口直接使用同一个 `MIHOMO_SECRET` 登录；保持 `false` 时适合可信内网免登录使用。
- 认证 Cookie 为 HttpOnly、默认长期有效（10 年）；修改 `MIHOMO_SECRET` 可使所有旧登录失效。`/subapi/`、`/provider-regions/` 转换结果和 `/s/` 短链接不受登录开关影响。
- 「关闭 mihomo」按钮：经 Docker socket（`/var/run/docker.sock`）停止 mihomo 容器，
  代理服务即停止；再用「切换当前配置」可启动并恢复。
- 首页卡片头左侧有 mihomo 状态标签（运行中/已停止/未知），每 30 秒自动刷新，点击可手动刷新。
- 默认远程配置/规则：[Custom_OpenClash_Rules](https://github.com/Aethersailor/Custom_OpenClash_Rules)
  （前端默认选中 GitHub 仓库 `cfg` 目录直链；后端 `default_external_config` 默认也是它）。

## 快速开始

```bash
# 1. 初始化配置（密钥文件不入库，从模板复制）
cp .env.example .env
cp config/mihomo/config.example.yaml config/mihomo/config.yaml

# 2. 修改安全配置
vi .env                        # 公网设置 WEB_AUTH_ENABLED=true，并修改 ZURL_SHORT_TOKEN、MIHOMO_SECRET
vi config/mihomo/config.yaml   # secret 与 .env 的 MIHOMO_SECRET 保持一致

# 2. 启动（首次构建 sub-web / zurl，并拉取 metacubexd 等官方镜像）
docker compose up -d

# 3. 访问（默认 Web 端口 7788）
http://服务器IP:7788/       订阅转换
http://服务器IP:7788/xd/    metacubexd 官方面板
```

国内构建加速：编辑 `docker-compose.yml`，取消各服务 `args` 里的
`NPM_CONFIG_REGISTRY` / `PIP_INDEX_URL` 镜像源注释。

## 目录说明

| 路径 | 说明 |
|---|---|
| `sub-web-modify/` | 订阅转换前端（已改为动态域名默认值） |
| `SubConverter-Extended/` | 转换后端源码（默认用官方镜像；`base/pref.toml` 已挂载，可自行定制） |
| `zurl/` | 短链服务（新增 `app/api/compat.py` 兼容层：`POST /short`） |
| `nginx/templates/` | 网关配置（envsubst 模板） |
| `config/mihomo/config.yaml` | mihomo 内核配置 |
| `data/` | 运行数据（zurl sqlite/redis、mihomo 缓存） |

## 对上游项目的修改清单

- **sub-web-modify** `src/views/Subconverter.vue`
  - 新增 `siteOrigin/localBackend/localShort` 动态常量
  - 后端地址、短链选择默认项改为本站动态地址（下拉列表第一项）
  - 默认远程配置改为 Custom_OpenClash_Rules（GitHub `cfg` 目录直链）
  - `makeUrl`/`makeShortUrl` 兜底地址改为本站动态地址
  - `getBackendVersion` 提示语通用化；`download.html` 链接改为跟随当前协议
  - 「从URL解析」支持带 `/subapi` 或 `/provider-regions` 前缀的本站链接
  - `Dockerfile` 增加 `NPM_CONFIG_REGISTRY` 构建参数；补充 `.dockerignore`
- **zurl**
  - 新增 `app/api/compat.py`：myurls 风格 `POST /short`（base64 longUrl + 可选 shortKey），
    返回 `{Code, Message, ShortUrl}`；ShortUrl 按请求头动态拼接 `/s/` 前缀
  - `POST /apply` 只生成候选 `latest.yaml`；`POST /mihomo/latest-config` 才切换当前配置并重启 mihomo
  - `app/routers/routers.py` 注册 `/short`、`/apply` 路由；`DENY_SHORT_URLS` 增加 `short`、`s`、`apply`
  - `Dockerfile` 增加 `PIP_INDEX_URL` 构建参数；`requirements.txt` 增加 `pyyaml`；补充 `.dockerignore`
- **SubConverter-Extended**：无代码修改，仅复制 `base/pref.example.toml` → `base/pref.toml` 用于挂载

## 安全提示

1. `.env` 的 `ZURL_SHORT_TOKEN` 务必修改（它防止绕过 nginx 直连 zurl 刷短链；
   经 nginx 的 `/short` 本身是公开的，与公共 sub-web 行为一致）。
2. `config/mihomo/config.yaml` 的 `secret` 默认 `yuan`（与 `.env` 的 `MIHOMO_SECRET` 一致），
   公网部署务必同时修改这两处，`/clash` 即面板控制 API。
3. 7890 代理端口默认对局域网开放，请注意来源限制；不需要时注释掉端口映射。
4. zurl 容器挂载了 `/var/run/docker.sock` 用于启停 mihomo，socket 权限等同宿主机 root，
   请勿把 zurl 的 3080 端口直接暴露到公网（默认不映射，仅经 nginx 受控路径访问）。
5. 如需 HTTPS，把域名指到 nginx（默认 :7788，或改 `WEB_PORT` 为 80），前端/短链会自动跟随 `https://`。
