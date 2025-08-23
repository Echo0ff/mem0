#!/bin/bash
set -e

echo "=== 启动 Mem0 生产环境 ==="

# 等待依赖服务启动
echo "等待依赖服务启动..."

# 等待 PostgreSQL
echo "等待 PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL 已就绪"

# 等待 Neo4j
echo "等待 Neo4j..."
while ! nc -z neo4j 7687; do
  sleep 1
done
echo "Neo4j 已就绪"

# 等待 Milvus
echo "等待 Milvus..."
while ! nc -z milvus-standalone 19530; do
  sleep 1
done
echo "Milvus 已就绪"

# 设置环境变量
export ENVIRONMENT=production
export PYTHONPATH=/app:$PYTHONPATH

# 创建日志目录
mkdir -p /app/logs

# 启动应用
echo "启动 Mem0 应用..."
exec gunicorn main:app \
    --workers 4 \
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