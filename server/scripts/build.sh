#!/bin/bash

# Mem0 生产环境构建脚本
# 设计为从 /server 目录根部执行: bash scripts/build.sh

set -e

echo "=== Mem0 生产环境构建脚本 ==="

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装或不在 PATH 中"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ 错误: Docker Compose 未安装或版本过低"
    echo "请安装 Docker Compose v2.0 或更高版本"
    exit 1
fi

# 检查必要文件
if [ ! -f ".env.prod" ]; then
    echo "❌ 错误: .env.prod 文件在 /server 目录不存在"
    echo "请先创建 .env.prod 配置文件"
    exit 1
fi

if [ ! -f "docker/docker-compose.prod.yaml" ]; then
    echo "❌ 错误: docker/docker-compose.prod.yaml 文件不存在"
    exit 1
fi

# 检查项目根目录文件
if [ ! -f "../pyproject.toml" ]; then
    echo "❌ 错误: 项目根目录的 pyproject.toml 文件不存在"
    echo "请确保在正确的目录结构中运行此脚本"
    exit 1
fi

# 创建必要的目录
echo "📁 创建数据目录..."
mkdir -p logs
mkdir -p history
mkdir -p data

# 设置目录权限
echo "🔧 设置目录权限..."
chmod 755 logs history data

# 停止现有服务（如果在运行）
echo "🛑 停止现有服务..."
docker compose -f docker/docker-compose.prod.yaml down || true

# 清理旧的镜像（可选）
read -p "是否清理旧的 Docker 镜像? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 清理旧镜像..."
    docker compose -f docker/docker-compose.prod.yaml down --rmi all || true
    docker system prune -f || true
fi

# 构建Docker镜像
echo "🔨 构建Docker镜像..."
docker compose -f docker/docker-compose.prod.yaml build --no-cache

# 验证镜像构建
echo "🔍 验证镜像..."
if ! docker images | grep -q mem0-prod; then
    echo "❌ 错误: 镜像构建失败"
    exit 1
fi

echo "✅ 构建完成!"
echo ""
echo "📋 构建摘要:"
echo "  - 应用镜像: $(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep mem0-prod | head -1)"
echo ""
echo "下一步："
echo "1. 检查 .env.prod 文件，确保配置正确的API密钥"
echo "2. 运行 bash scripts/run.sh 启动服务"
echo "3. 访问 http://localhost:18888/docs 查看API文档"
echo ""
echo "📚 有用的命令:"
echo "  - 查看配置: docker compose -f docker/docker-compose.prod.yaml config"
echo "  - 验证服务: docker compose -f docker/docker-compose.prod.yaml ps"