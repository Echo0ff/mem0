#!/bin/bash

# Mem0 生产环境运行脚本
# 使用方法: ./scripts/run.sh

set -e

echo "=== Mem0 生产环境启动脚本 ==="

# 检查必要文件
if [ ! -f ".env.prod" ]; then
    echo "❌ 错误: .env.prod 文件不存在"
    echo "请先运行 ./scripts/build.sh 构建项目"
    exit 1
fi

# 检查API密钥是否已配置
if grep -q "your_production_" .env.prod; then
    echo "⚠️  警告: 检测到默认API密钥，请确保已配置正确的生产环境密钥"
    read -p "是否继续启动? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查端口是否被占用
echo "🔍 检查端口占用情况..."
if lsof -Pi :18888 -sTCP:LISTEN -t >/dev/null; then
    echo "❌ 错误: 端口 18888 已被占用"
    echo "请检查是否有其他Mem0实例在运行，或修改 docker/docker-compose.prod.yaml 中的端口配置"
    exit 1
fi

# 启动服务
echo "🚀 启动生产环境服务..."
docker compose -f docker/docker-compose.prod.yaml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
docker compose -f docker/docker-compose.prod.yaml ps

# 健康检查
echo "🏥 进行健康检查..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f -s http://localhost:18888/docs > /dev/null 2>&1; then
        echo "✅ 服务启动成功!"
        echo ""
        echo "🌐 服务访问地址:"
        echo "  - API文档: http://localhost:18888/docs"
        echo "  - PostgreSQL: localhost:15432"
        echo "  - Neo4j: http://localhost:17474"
        echo "  - Minio: http://localhost:19001"
        echo ""
        echo "📋 查看日志:"
        echo "  - 应用日志: docker compose -f docker/docker-compose.prod.yaml logs -f mem0"
        echo "  - 所有服务: docker compose -f docker/docker-compose.prod.yaml logs -f"
        echo ""
        echo "📁 日志文件位置:"
        echo "  - 应用日志: ./logs/mem0.log"
        echo "  - 访问日志: ./logs/access.log"
        echo "  - 错误日志: ./logs/error.log"
        exit 0
    fi
    
    echo "等待服务启动... ($attempt/$max_attempts)"
    sleep 2
    ((attempt++))
done

echo "❌ 服务启动超时，请检查日志:"
echo "docker compose -f docker/docker-compose.prod.yaml logs"
exit 1