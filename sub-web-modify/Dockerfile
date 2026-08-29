# --- Build stage ---
FROM node:22.18.0-alpine3.22 AS build

# 可选：指定 npm/yarn 镜像源（国内构建加速），默认官方源
ARG NPM_CONFIG_REGISTRY=https://registry.npmjs.org
ENV NPM_CONFIG_REGISTRY=${NPM_CONFIG_REGISTRY}

# 拉取 git 依赖必需；如有原生模块再加 python3 make g++
RUN apk add --no-cache git

WORKDIR /app

# 先拷贝依赖清单利用缓存
COPY package.json yarn.lock ./
# node:22 已自带 yarn 1.x，无需再 npm i -g yarn
RUN yarn install --frozen-lockfile

# 再拷贝源码并构建
COPY . .
RUN yarn build

# --- Runtime stage ---
FROM nginx:1.24-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
