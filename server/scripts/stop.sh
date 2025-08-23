#!/bin/bash

# Mem0 生产环境停止脚本
# 设计为从 /server 目录根部执行: bash scripts/stop.sh

set -e

echo "=== Mem0 生产环境停止脚本 ==="

# 检查是否有服务在运行
if ! docker compose -f docker/docker-compose.prod.yaml ps --services --filter "status=running" | grep -q .; then
    echo "ℹ️  没有运行中的服务"
    exit 0
fi

echo "🛑 停止所有服务..."

# 优雅停止应用服务
echo "📱 停止应用服务..."
docker compose -f docker/docker-compose.prod.yaml stop mem0

# 停止数据库服务
echo "🗄️  停止数据库服务..."
docker compose -f docker/docker-compose.prod.yaml stop milvus-standalone neo4j postgres

# 停止基础服务
echo "📡 停止基础服务..."
docker compose -f docker/docker-compose.prod.yaml stop minio etcd

# 完全关闭
docker compose -f docker/docker-compose.prod.yaml down

echo "✅ 所有服务已停止"

# 询问是否清理数据
read -p "是否清理所有数据卷? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 清理数据卷..."
    docker compose -f docker/docker-compose.prod.yaml down -v
    echo "✅ 数据已清理"
fi

echo "📊 清理后状态:"
docker compose -f docker/docker-compose.prod.yaml ps