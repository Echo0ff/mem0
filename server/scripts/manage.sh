#!/bin/bash

# Mem0 生产环境综合管理脚本
# 使用方法: ./scripts/manage.sh [命令] [选项]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 显示帮助信息
show_help() {
    echo "Mem0 生产环境管理脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "命令:"
    echo "  build                构建Docker镜像"
    echo "  run                  启动生产环境服务"
    echo "  stop                 停止服务"
    echo "  restart              重启服务"
    echo "  remove [--all]       清理环境"
    echo "  logs [service]       查看日志"
    echo "  status               查看服务状态"
    echo "  shell [service]      进入服务shell"
    echo "  backup               备份数据"
    echo "  restore [file]       恢复数据"
    echo "  update               更新服务"
    echo ""
    echo "选项:"
    echo "  --help              显示此帮助信息"
    echo "  --all               用于remove命令，删除所有数据"
    echo ""
    echo "示例:"
    echo "  $0 build                    # 构建镜像"
    echo "  $0 run                      # 启动服务" 
    echo "  $0 logs mem0                # 查看mem0服务日志"
    echo "  $0 remove --all             # 删除所有数据"
    echo "  $0 shell mem0               # 进入mem0容器shell"
}

# 切换到项目目录
cd "$PROJECT_DIR"

# 解析命令
case "${1:-help}" in
    "build")
        print_info "构建生产环境镜像..."
        bash scripts/build.sh
        ;;
    
    "run"|"start")
        print_info "启动生产环境服务..."
        bash scripts/run.sh
        ;;
    
    "stop")
        print_info "停止生产环境服务..."
        docker compose -f docker/docker-compose.prod.yaml down
        print_success "服务已停止"
        ;;
    
    "restart")
        print_info "重启生产环境服务..."
        docker compose -f docker/docker-compose.prod.yaml restart
        print_success "服务已重启"
        ;;
    
    "remove")
        if [ "$2" = "--all" ]; then
            bash scripts/remove.sh --all
        else
            bash scripts/remove.sh --keep-data
        fi
        ;;
    
    "logs")
        service="${2:-}"
        if [ -n "$service" ]; then
            print_info "查看 $service 服务日志..."
            docker compose -f docker/docker-compose.prod.yaml logs -f "$service"
        else
            print_info "查看所有服务日志..."
            docker compose -f docker/docker-compose.prod.yaml logs -f
        fi
        ;;
    
    "status")
        print_info "检查服务状态..."
        echo ""
        docker compose -f docker/docker-compose.prod.yaml ps
        echo ""
        print_info "健康检查..."
        if curl -f -s http://localhost:18888/docs > /dev/null 2>&1; then
            print_success "Mem0 API服务正常"
        else
            print_error "Mem0 API服务异常"
        fi
        ;;
    
    "shell")
        service="${2:-mem0}"
        print_info "进入 $service 容器..."
        docker compose -f docker/docker-compose.prod.yaml exec "$service" /bin/bash
        ;;
    
    "backup")
        print_info "备份数据..."
        timestamp=$(date +%Y%m%d_%H%M%S)
        backup_dir="backups/backup_$timestamp"
        mkdir -p "$backup_dir"
        
        # 备份PostgreSQL
        print_info "备份PostgreSQL数据库..."
        docker compose -f docker/docker-compose.prod.yaml exec postgres pg_dump -U mem0_user mem0_prod > "$backup_dir/postgres.sql"
        
        # 备份文件数据
        print_info "备份文件数据..."
        if [ -d "data" ]; then
            cp -r data "$backup_dir/"
        fi
        if [ -d "logs" ]; then
            cp -r logs "$backup_dir/"
        fi
        
        print_success "备份完成: $backup_dir"
        ;;
    
    "restore")
        backup_file="$2"
        if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
            print_error "请指定有效的备份文件"
            exit 1
        fi
        print_warning "恢复功能待实现"
        ;;
    
    "update")
        print_info "更新服务..."
        print_info "拉取最新代码..."
        git pull
        
        print_info "重新构建镜像..."
        bash scripts/build.sh
        
        print_info "重启服务..."
        docker compose -f docker/docker-compose.prod.yaml up -d
        
        print_success "更新完成"
        ;;
    
    "help"|"--help"|*)
        show_help
        ;;
esac