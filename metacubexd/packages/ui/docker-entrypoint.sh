#!/bin/sh

set -eu

# Map DEFAULT_BACKEND_URL to Nuxt runtime config env var.
# Nitro embeds public asset metadata at build time, so do not rewrite config.js.
export NUXT_PUBLIC_DEFAULT_BACKEND_URL="${DEFAULT_BACKEND_URL:-}"
# 连接表单默认密钥（通常与 mihomo secret 一致）
export NUXT_PUBLIC_DEFAULT_BACKEND_SECRET="${DEFAULT_BACKEND_SECRET:-}"
# 订阅转换首页地址（侧边栏快捷入口）；留空则面板按当前主机名+80端口推导
export NUXT_PUBLIC_SUB_WEB_URL="${SUB_WEB_URL:-}"
# GitHub Releases metadata is public, but authenticated requests have a much
# higher rate limit. The public runtime value is intentionally available to the
# browser, so use only a narrowly scoped/read-only token.
export NUXT_PUBLIC_GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# Start Node.js server
exec node /app/.output/server/index.mjs
