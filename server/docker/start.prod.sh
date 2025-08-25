#!/bin/bash
set -e

echo "=== 启动 Mem0 生产环境 ==="

# 设置环境变量
export ENVIRONMENT=production
export PYTHONPATH=/app:$PYTHONPATH

# 创建日志目录
mkdir -p /app/logs

# 启动应用
echo "启动 Mem0 应用..."
exec gunicorn main:app \
    --workers ${WORKERS:-4} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --log-level info \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --preload