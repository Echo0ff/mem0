FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置国内 PyPI 源（持久化）
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# 替换 Debian 源为阿里云镜像
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       wget \
       git \
       gcc \
       g++ \
       build-essential \
       libssl-dev \
       libffi-dev \
       libpq-dev \
       libjpeg-dev \
       zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（直接 pip 安装更稳定）
RUN pip install -i https://mirrors.aliyun.com/pypi/simple uv

# 设置国内 pip 源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple

# 复制 requirements 并安装 Python 依赖
COPY server/requirements.txt .
RUN uv pip install --system -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt

# 安装 mem0 库（生产模式）
WORKDIR /app/packages
COPY pyproject.toml .
COPY poetry.lock .
COPY README.md .
COPY mem0 ./mem0
RUN uv pip install --system -i https://mirrors.aliyun.com/pypi/simple -e .[graph]

# 返回 app 目录并复制服务器代码
WORKDIR /app
COPY server .

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/history /app/data && \
    chmod -R 755 /app && \
    chown -R root:root /app

# 使用 root 用户运行
USER root

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || curl -f http://localhost:8000/docs || exit 1

# 暴露端口
EXPOSE 8000

# 添加启动脚本
COPY server/docker/start.prod.sh /app/docker/start.prod.sh
RUN chmod +x /app/docker/start.prod.sh

# 默认启动命令
CMD ["/app/docker/start.prod.sh"]
