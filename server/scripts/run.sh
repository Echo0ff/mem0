#!/bin/bash

# Mem0 生产环境运行脚本
# 设计为从 /server 目录根部执行: bash scripts/run.sh

set -e

echo "=== Mem0 生产环境启动脚本 ==="

# 检查必要文件
if [ ! -f ".env.prod" ]; then
    echo "❌ 错误: .env.prod 文件不存在"
    echo "请先运行 bash scripts/build.sh 构建项目"
    exit 1
fi

# 检查API密钥是否已配置
if grep -q "your_production_" .env.prod; then
    echo "⚠️  警告: 检测到默认API密钥，请确保已配置正确的生产环境密钥"
    echo "受影响的配置项:"
    grep "your_production_" .env.prod | cut -d'=' -f1 | sed 's/^/  - /'
    echo ""
    read -p "是否继续启动? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查关键端口是否被占用
echo "🔍 检查端口占用情况..."
ports_to_check=(18888 15432 17474 17687 19530 9091 9000 9001 12379 12380)
occupied_ports=()

for port in "${ports_to_check[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        occupied_ports+=($port)
    fi
done

if [ ${#occupied_ports[@]} -ne 0 ]; then
    echo "❌ 错误: 以下端口已被占用: ${occupied_ports[*]}"
    echo "请检查是否有其他服务在运行，或修改配置文件中的端口"
    echo ""
    echo "端口用途:"
    echo "  - 18888: Mem0 API"
    echo "  - 15432: PostgreSQL"
    echo "  - 17474/17687: Neo4j"
    echo "  - 19530/19091: Milvus"
    echo "  - 19000/19001: MinIO"
    echo "  - 12379: etcd"
    exit 1
fi

# 检查系统资源
echo "💻 检查系统资源..."
available_memory=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
available_disk=$(df -h . | awk 'NR==2{print $4}')

echo "  - 可用内存: ${available_memory}GB"
echo "  - 可用磁盘: ${available_disk}"

if (( $(echo "$available_memory < 4.0" | bc -l) )); then
    echo "⚠️  警告: 可用内存不足 4GB，可能影响性能"
fi

# 启动服务（分阶段启动）
echo "🚀 启动生产环境服务..."

# 第一阶段: 基础服务
echo "📡 启动基础服务 (etcd, minio)..."
docker compose -f docker/docker-compose.prod.yaml up -d etcd minio

# 等待基础服务就绪
echo "⏳ 等待基础服务就绪..."
max_wait=60
wait_time=0

while [ $wait_time -lt $max_wait ]; do
    etcd_healthy=$(docker compose -f docker/docker-compose.prod.yaml ps etcd --format json | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "starting")
    minio_healthy=$(docker compose -f docker/docker-compose.prod.yaml ps minio --format json | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "starting")
    
    if [ "$etcd_healthy" = "healthy" ] && [ "$minio_healthy" = "healthy" ]; then
        break
    fi
    
    echo "  等待基础服务... ($wait_time/${max_wait}s) [etcd: $etcd_healthy, minio: $minio_healthy]"
    sleep 3
    wait_time=$((wait_time + 3))
done

if [ $wait_time -ge $max_wait ]; then
    echo "❌ 基础服务启动超时，检查日志:"
    docker compose -f docker/docker-compose.prod.yaml logs etcd minio
    exit 1
fi

# 第二阶段: 数据库服务
echo "🗄️  启动数据库服务 (postgres, neo4j, milvus)..."
docker compose -f docker/docker-compose.prod.yaml --env-file .env.prod up -d postgres neo4j milvus-standalone attu

# 等待数据库服务就绪
echo "⏳ 等待数据库服务就绪..."
wait_time=0
max_wait=120

while [ $wait_time -lt $max_wait ]; do
    postgres_healthy=$(docker compose -f docker/docker-compose.prod.yaml ps postgres --format json | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "starting")
    neo4j_healthy=$(docker compose -f docker/docker-compose.prod.yaml ps neo4j --format json | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "starting")
    milvus_healthy=$(docker compose -f docker/docker-compose.prod.yaml ps milvus-standalone --format json | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || echo "starting")
    
    if [ "$postgres_healthy" = "healthy" ] && [ "$neo4j_healthy" = "healthy" ] && [ "$milvus_healthy" = "healthy" ]; then
        break
    fi
    
    echo "  等待数据库服务... ($wait_time/${max_wait}s)"
    echo "    postgres: $postgres_healthy, neo4j: $neo4j_healthy, milvus: $milvus_healthy"
    sleep 5
    wait_time=$((wait_time + 5))
done

if [ $wait_time -ge $max_wait ]; then
    echo "❌ 数据库服务启动超时，检查日志:"
    docker compose -f docker/docker-compose.prod.yaml logs postgres neo4j milvus-standalone attu
    exit 1
fi

# 第三阶段: 应用服务
echo "🚀 启动应用服务..."
docker compose -f docker/docker-compose.prod.yaml up -d mem0

# 等待应用服务启动
echo "⏳ 等待应用服务启动..."
max_attempts=40
attempt=1

while [ $attempt -le $max_attempts ]; do
    # 检查多个健康检查端点
    if curl -f -s http://localhost:18888/docs > /dev/null 2>&1 || \
       curl -f -s http://localhost:18888/health > /dev/null 2>&1; then
        echo "✅ 服务启动成功!"
        break
    fi
    
    # 显示详细状态
    if [ $((attempt % 10)) -eq 0 ]; then
        echo "📊 当前服务状态:"
        docker compose -f docker/docker-compose.prod.yaml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    fi
    
    echo "  等待应用服务... ($attempt/$max_attempts)"
    sleep 3
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ 应用服务启动超时"
    echo ""
    echo "📊 最终服务状态:"
    docker compose -f docker/docker-compose.prod.yaml ps
    echo ""
    echo "📋 查看日志排查问题:"
    echo "docker compose -f docker/docker-compose.prod.yaml logs mem0"
    exit 1
fi

# 最终状态检查
echo ""
echo "📊 服务状态检查..."
docker compose -f docker/docker-compose.prod.yaml ps

echo ""
echo "🌐 服务访问地址:"
echo "  - 📚 API文档: http://localhost:18888/docs"
echo "  - 🐘 PostgreSQL: localhost:15432"
echo "  - 🕸️  Neo4j: http://localhost:17474"
echo "  - 🗂️  MinIO: http://localhost:19001 (admin/minioadmin)"
echo "  - 🔍 Milvus: localhost:19530"
echo "  - 📊 Attu: http://localhost:28090"

echo ""
echo "📋 管理命令:"
echo "  - 查看所有日志: docker compose -f docker/docker-compose.prod.yaml logs -f"