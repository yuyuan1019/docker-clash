# syntax=docker/dockerfile:1
# Standalone metacubexd panel (Nuxt node-server, ships only the dashboard).
# Build context MUST be the repo root: docker buildx build -f packages/ui/Dockerfile .

# ---- Stage 1: build the Nuxt node-server output (on the builder's native arch) ----
FROM --platform=$BUILDPLATFORM node:22-alpine AS builder
# 可选：指定 pnpm/npm 镜像源（国内构建加速），默认官方源
ARG NPM_CONFIG_REGISTRY=https://registry.npmjs.org
ENV NPM_CONFIG_REGISTRY=${NPM_CONFIG_REGISTRY}
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH HUSKY=0
WORKDIR /repo
RUN corepack enable
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json tsconfig.base.json ./
COPY packages/ packages/
COPY apps/ apps/
RUN pnpm install --frozen-lockfile
# 子路径部署支持：构建期注入 Nuxt baseURL（如 /xd/，经 nginx 反代）；
# 子路径下禁用 PWA，避免 Service Worker 缓存作用域问题
ARG NUXT_APP_BASE_URL=/
ENV NUXT_APP_BASE_URL=${NUXT_APP_BASE_URL} \
    MCXD_DISABLE_PWA=true
RUN pnpm --filter @metacubexd/ui build
# -> /repo/packages/ui/.output (Nitro node-server preset, serves the CSR panel)

# ---- Stage 2: slim runtime ----
FROM node:22-alpine
ENV PORT=80 NODE_ENV=production
EXPOSE 80
WORKDIR /app
COPY --from=builder /repo/packages/ui/.output ./.output
COPY packages/ui/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
CMD ["/docker-entrypoint.sh"]
