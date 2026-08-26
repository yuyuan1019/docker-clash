# 基于redis镜像构建
FROM redis:7-alpine
# 可选：指定 pip 镜像源（国内构建加速），默认官方源
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
# 工作目录
WORKDIR /opt/zurl
# 把当前目录下的所有文件拷贝到工作目录
COPY . .
# 执行安装脚本
RUN sh install.sh
# 暴露端口和目录
EXPOSE 3080
VOLUME /opt/zurl/app/data
# 启动命令
CMD ["sh", "run.sh"]