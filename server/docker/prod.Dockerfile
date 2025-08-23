FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖 - 优化版本
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 安装uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 复制requirements并安装Python依赖
COPY server/requirements.txt .
RUN uv pip install --system -r requirements.txt

# 安装mem0库（生产模式）
WORKDIR /app/packages
COPY pyproject.toml .
COPY poetry.lock .
COPY README.md .
COPY mem0 ./mem0
RUN uv pip install --system -e .[graph]

# 返回app目录并复制服务器代码
WORKDIR /app
COPY server .

# 创建必要的目录和设置权限
RUN mkdir -p /app/logs /app/history /app/data && \
    chmod -R 755 /app && \
    chown -R root:root /app

# 使用 root 用户运行
USER root

# 健康检查 - 修复路径
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || curl -f http://localhost:8000/docs || exit 1

# 暴露端口
EXPOSE 8000

# 添加启动脚本
COPY docker/start.prod.sh /app/docker/start.prod.sh
RUN chmod +x /app/docker/start.prod.sh

# 默认启动命令
CMD ["/app/docker/start.prod.sh"]