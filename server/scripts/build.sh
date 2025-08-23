#!/bin/bash

# Mem0 生产环境构建脚本
# 使用方法: ./scripts/build.sh

set -e

echo "=== Mem0 生产环境构建脚本 ==="

# 检查必要文件
if [ ! -f ".env.prod" ]; then
    echo "❌ 错误: .env.prod 文件不存在"
    echo "请先创建 .env.prod 配置文件"
    exit 1
fi

if [ ! -f "docker/docker-compose.prod.yaml" ]; then
    echo "❌ 错误: docker/docker-compose.prod.yaml 文件不存在"
    exit 1
fi

# 创建必要的目录
echo "📁 创建数据目录..."
mkdir -p data/history
mkdir -p logs

# 构建Docker镜像
echo "🔨 构建Docker镜像..."
docker compose -f docker/docker-compose.prod.yaml build --no-cache

echo "✅ 构建完成!"
echo ""
echo "下一步："
echo "1. 编辑 .env.prod 文件，配置正确的API密钥"
echo "2. 运行 ./scripts/run.sh 启动服务"
echo "3. 访问 http://localhost:18888/docs 查看API文档"