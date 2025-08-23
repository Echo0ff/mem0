#!/bin/bash

# Mem0 生产环境清理脚本
# 使用方法: ./scripts/remove.sh [选项]
# 选项:
#   --all       删除所有数据（包括数据库数据）
#   --keep-data 只停止服务，保留数据

set -e

echo "=== Mem0 生产环境清理脚本 ==="

# 解析参数
REMOVE_DATA=false
KEEP_DATA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            REMOVE_DATA=true
            shift
            ;;
        --keep-data)
            KEEP_DATA=true
            shift
            ;;
        *)
            echo "未知选项: $1"
            echo "用法: $0 [--all|--keep-data]"
            exit 1
            ;;
    esac
done

# 如果没有指定选项，询问用户
if [ "$REMOVE_DATA" = false ] && [ "$KEEP_DATA" = false ]; then
    echo "请选择清理方式:"
    echo "1. 只停止服务，保留所有数据"
    echo "2. 停止服务并删除所有数据（不可恢复）"
    read -p "请输入选择 (1/2): " choice
    
    case $choice in
        1)
            KEEP_DATA=true
            ;;
        2)
            REMOVE_DATA=true
            ;;
        *)
            echo "无效选择，退出"
            exit 1
            ;;
    esac
fi

# 停止服务
echo "🛑 停止生产环境服务..."
if docker compose -f docker/docker-compose.prod.yaml ps --services --filter "status=running" | grep -q .; then
    docker compose -f docker/docker-compose.prod.yaml down
    echo "✅ 服务已停止"
else
    echo "ℹ️  没有运行中的服务"
fi

# 删除数据
if [ "$REMOVE_DATA" = true ]; then
    echo ""
    echo "⚠️  即将删除所有数据，此操作不可恢复！"
    read -p "确定要继续吗? (yes/NO): " confirm
    
    if [ "$confirm" = "yes" ]; then
        echo "🗑️  删除Docker卷..."
        docker compose -f docker/docker-compose.prod.yaml down -v
        
        echo "🗑️  删除本地数据..."
        if [ -d "data" ]; then
            rm -rf data
            echo "✅ 本地数据目录已删除"
        fi
        
        if [ -d "logs" ]; then
            rm -rf logs  
            echo "✅ 日志目录已删除"
        fi
        
        echo "🗑️  删除Docker镜像..."
        if docker images | grep -q "mem0-prod-mem0"; then
            docker rmi mem0-prod-mem0 2>/dev/null || true
            echo "✅ Docker镜像已删除"
        fi
        
        echo "✅ 所有数据已清理完成"
    else
        echo "❌ 取消删除操作"
    fi
elif [ "$KEEP_DATA" = true ]; then
    echo "✅ 服务已停止，数据已保留"
fi

echo ""
echo "📋 清理完成!"
if [ "$REMOVE_DATA" = true ] && [ "$confirm" = "yes" ]; then
    echo "所有数据已删除，如需重新部署请运行:"
    echo "  ./scripts/build.sh"
    echo "  ./scripts/run.sh"
elif [ "$KEEP_DATA" = true ]; then
    echo "如需重新启动服务，请运行:"
    echo "  ./scripts/run.sh"
fi