# docker-clash 一体化项目

将订阅转换、短链服务、mihomo 内核与面板整合为一个 docker-compose 项目。

## 操作指南

### 日常使用（生成订阅并启用）

1. 浏览器打开 `http://服务器IP/`（订阅转换首页）
2. 「订阅链接」处每行填一组：**提供商名称**（可选，如 `机场A`）+ 订阅链接；
   多条订阅点「添加订阅链接」增加行。填了提供商名，Clash 里的代理提供者就显示该名字
3. 「生成类型」默认 Clash；「远程配置」默认 Custom_OpenClash_Rules（可换 Full/Lite/GFW 等变体）
4. 「订阅命名」留空会自动填：单订阅=提供商名，多订阅=`合集`；「更新间隔」默认 7 天
5. 点「生成订阅链接」→ 得到定制订阅长链；再点「生成短链接」→ 得到 `当前域名/s/xxxx`
6. 点「启用 mihomo」→ 自动把转换结果写入本机 mihomo 并热重载（容器若已停止会自动拉起）
7. 点卡片头右侧「打开面板」（或访问 `/xd/`）进入 metacubexd：
   - 后端地址填 `http://服务器IP/clash`，密钥为 `.env` 的 `MIHOMO_SECRET`（默认 `yuan`）
8. 不用代理时点「关闭 mihomo」即可停止内核；状态看卡片头左上角标签（绿=运行中）

### 客户端使用

- OpenClash / mihomo 系客户端：直接用生成的订阅链接或短链，配置由客户端自动更新
- 本机 mihomo 作为局域网代理网关：7890 端口默认已映射，
  其他设备代理直接设置为 `服务器IP:7890`（不需要时到 `docker-compose.yml` 注释掉即可）

### 运维操作

```bash
docker compose up -d          # 启动/更新（配置变更后）
docker compose stop           # 停止全部服务（数据保留在 ./data）
docker compose start          # 恢复
docker compose logs -f zurl   # 看某个服务日志（zurl/subconverter/mihomo/nginx...）
docker compose pull && docker compose up -d   # 升级 subconverter/mihomo 官方镜像
# 本地构建的三个前端/后端改了代码后：
docker compose build sub-web zurl metacubexd && docker compose up -d
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
http://域名/short    → zurl 短链生成 API（POST，nginx 注入内部令牌）
http://域名/apply    → 一键启用：把本站 Clash 订阅链接应用为 mihomo 运行配置（POST，同上防护）
http://域名/s/xxxx   → zurl 短链 302 解析跳转
http://域名/xd/      → metacubexd 面板（Nuxt baseURL=/xd/，本地构建）
http://域名/clash/   → mihomo Clash API（含 WebSocket，面板连接用）
```

- 订阅转换界面的「后端地址」「短链选择」**默认值根据当前访问域名动态生成**
  （`window.location.origin + '/subapi'` / `'/short'`），换域名、换端口、上 HTTPS 均无需改代码。
- 生成的短链同样是动态的 `当前域名/s/xxxx`（zurl 从反代请求头取 Host/Proto）。
- 面板连接地址：`http://域名/clash`，密钥为 `config/mihomo/config.yaml` 里的 `secret`。
- mihomo 的 7890 代理端口默认已对局域网开放（`allow-lan: true`）；
  不需要对外提供代理时，到 `docker-compose.yml` 注释掉 mihomo 的端口映射即可。
- 「启用 mihomo」按钮：生成订阅链接后点击，后端会拉取转换结果、写入管理端口 9090 与密钥
  （默认 `yuan`，`.env` 的 `MIHOMO_SECRET` 可改）后原地重写 `config/mihomo/config.yaml`，
  并调用 mihomo `PATCH /configs?force=true` 热重载，面板 `/xd/` 即可看到新配置与节点；
  若 mihomo 容器处于停止状态会先自动启动。
- 「关闭 mihomo」按钮：经 Docker socket（`/var/run/docker.sock`）停止 mihomo 容器，
  代理服务即停止；再用「启用 mihomo」可随时恢复。
- 首页卡片头左侧有 mihomo 状态标签（运行中/已停止/未知），每 30 秒自动刷新，点击可手动刷新。
- 默认远程配置/规则：[Custom_OpenClash_Rules](https://github.com/Aethersailor/Custom_OpenClash_Rules)
  （前端默认选中 jsdelivr 加速地址；后端 `default_external_config` 默认也是它）。

## 快速开始

```bash
# 1. 初始化配置（密钥文件不入库，从模板复制）
cp .env.example .env
cp config/mihomo/config.example.yaml config/mihomo/config.yaml

# 2. 修改安全配置
vi .env                        # 改 ZURL_SHORT_TOKEN（随机长字符串）；MIHOMO_SECRET 默认 yuan
vi config/mihomo/config.yaml   # secret 与 .env 的 MIHOMO_SECRET 保持一致

# 2. 启动（首次会自动构建 sub-web / zurl / metacubexd）
docker compose up -d

# 3. 访问
http://服务器IP/       订阅转换
http://服务器IP/xd/    metacubexd 面板（后端地址填 http://服务器IP/clash，secret 同上）
```

国内构建加速：编辑 `docker-compose.yml`，取消各服务 `args` 里的
`NPM_CONFIG_REGISTRY` / `PIP_INDEX_URL` 镜像源注释。

## 目录说明

| 路径 | 说明 |
|---|---|
| `sub-web-modify/` | 订阅转换前端（已改为动态域名默认值） |
| `SubConverter-Extended/` | 转换后端源码（默认用官方镜像；`base/pref.toml` 已挂载，可自行定制） |
| `zurl/` | 短链服务（新增 `app/api/compat.py` 兼容层：`POST /short`） |
| `metacubexd/` | 面板（使用 `packages/ui/Dockerfile` 构建纯 UI） |
| `mihomo/` | ⚠️ 此目录是星穹铁道 Python 库（KT-Yeh/mihomo），**不是代理内核**，未使用；内核用官方镜像 |
| `nginx/templates/` | 网关配置（envsubst 模板） |
| `config/mihomo/config.yaml` | mihomo 内核配置 |
| `data/` | 运行数据（zurl sqlite/redis、mihomo 缓存） |

## 对上游项目的修改清单

- **sub-web-modify** `src/views/Subconverter.vue`
  - 新增 `siteOrigin/localBackend/localShort` 动态常量
  - 后端地址、短链选择默认项改为本站动态地址（下拉列表第一项）
  - 默认远程配置改为 Custom_OpenClash_Rules（jsdelivr 地址）
  - `makeUrl`/`makeShortUrl` 兜底地址改为本站动态地址
  - `getBackendVersion` 提示语通用化；`download.html` 链接改为跟随当前协议
  - 「从URL解析」支持带 `/subapi` 前缀的本站链接
  - `Dockerfile` 增加 `NPM_CONFIG_REGISTRY` 构建参数；补充 `.dockerignore`
- **zurl**
  - 新增 `app/api/compat.py`：myurls 风格 `POST /short`（base64 longUrl + 可选 shortKey），
    返回 `{Code, Message, ShortUrl}`；ShortUrl 按请求头动态拼接 `/s/` 前缀
  - 同文件新增 `POST /apply`：本站 Clash 订阅链接 → 内网拉取转换结果 → 保留核心项重写
    mihomo 配置 → 热重载（`MIHOMO_API`/`MIHOMO_CONFIG_FILE`/`SUBCONVERTER_INTERNAL` 可配）
  - `app/routers/routers.py` 注册 `/short`、`/apply` 路由；`DENY_SHORT_URLS` 增加 `short`、`s`、`apply`
  - `Dockerfile` 增加 `PIP_INDEX_URL` 构建参数；`requirements.txt` 增加 `pyyaml`；补充 `.dockerignore`
- **metacubexd** `packages/ui/Dockerfile` 增加 `NUXT_APP_BASE_URL` 构建参数（子路径 /xd/ 部署）并禁用 PWA、增加 `NPM_CONFIG_REGISTRY` 构建参数；`nuxt.config.ts` 增加 `subWebUrl` 运行时配置；`components/Sidebar.vue` 侧边栏新增「订阅转换」快捷入口
- **SubConverter-Extended**：无代码修改，仅复制 `base/pref.example.toml` → `base/pref.toml` 用于挂载

## 安全提示

1. `.env` 的 `ZURL_SHORT_TOKEN` 务必修改（它防止绕过 nginx 直连 zurl 刷短链；
   经 nginx 的 `/short` 本身是公开的，与公共 sub-web 行为一致）。
2. `config/mihomo/config.yaml` 的 `secret` 默认 `yuan`（与 `.env` 的 `MIHOMO_SECRET` 一致），
   公网部署务必同时修改这两处，`/clash` 即面板控制 API。
3. 7890 代理端口默认对局域网开放，请注意来源限制；不需要时注释掉端口映射。
4. zurl 容器挂载了 `/var/run/docker.sock` 用于启停 mihomo，socket 权限等同宿主机 root，
   请勿把 zurl 的 3080 端口直接暴露到公网（默认不映射，仅经 nginx 受控路径访问）。
5. 如需 HTTPS，把域名指到 nginx（:80），前端/短链会自动跟随 `https://`。
