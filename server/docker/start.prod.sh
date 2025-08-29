#!/bin/bash
set -e

echo "=== 启动 Mem0 生产环境 ==="

# 设置环境变量
export ENVIRONMENT=production
export PYTHONPATH=/app:$PYTHONPATH

# 创建日志目录
mkdir -p /app/logs

# 启动应用（Uvicorn 多进程）
echo "启动 Mem0 应用 (Uvicorn) ..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WORKERS:-2} \
    --loop uvloop \
    --http httptools \
    --timeout-keep-alive 5