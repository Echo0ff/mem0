FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

# 创建日志目录
RUN mkdir -p /app/logs

# 创建非root用户（生产环境安全实践）
RUN groupadd -r mem0 && useradd -r -g mem0 mem0
RUN chown -R mem0:mem0 /app
USER mem0

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# 暴露端口
EXPOSE 8000

# 默认启动命令（生产模式）
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "/app/logs/access.log", "--error-logfile", "/app/logs/error.log", "--log-level", "info"]