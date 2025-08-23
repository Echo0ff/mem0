#!/bin/bash
set -e

echo "Starting Mem0 Production Application..."

# 创建日志目录
mkdir -p /app/logs

# 运行数据库迁移
echo "Running database migrations..."
cd database && python run_migrations.py && cd ..

# 设置日志文件权限
touch /app/logs/mem0.log
touch /app/logs/access.log
touch /app/logs/error.log

# 启动生产服务器
echo "Starting Gunicorn server..."
exec gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --log-level info \
    --keepalive 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 120 \
    --worker-tmp-dir /dev/shm