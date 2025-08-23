#!/bin/bash

# Mem0 生产环境测试脚本
# 用于验证部署是否成功

set -e

echo "=== Mem0 生产环境测试脚本 ==="

BASE_URL="http://localhost:18888"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 测试API可达性
test_api_reachability() {
    print_info "测试API可达性..."
    if curl -f -s "$BASE_URL/docs" > /dev/null; then
        print_success "API文档页面访问正常"
    else
        print_error "API文档页面无法访问"
        return 1
    fi
}

# 测试基本API接口
test_basic_api() {
    print_info "测试基本API接口..."
    
    # 测试根路径重定向
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/")
    if [ "$response" = "307" ] || [ "$response" = "200" ]; then
        print_success "根路径访问正常"
    else
        print_error "根路径访问异常，HTTP状态码: $response"
        return 1
    fi
}

# 测试内存API
test_memory_api() {
    print_info "测试内存API..."
    
    # 创建测试内存
    test_data='{
        "messages": [
            {"role": "user", "content": "测试消息"},
            {"role": "assistant", "content": "这是一个测试回复"}
        ],
        "user_id": "test_user_001"
    }'
    
    response=$(curl -s -w "%{http_code}" -X POST "$BASE_URL/memories" \
        -H "Content-Type: application/json" \
        -d "$test_data")
    
    http_code=$(echo "$response" | tail -c 4)
    
    if [ "$http_code" = "200" ]; then
        print_success "内存创建API正常"
        
        # 测试获取内存
        get_response=$(curl -s -w "%{http_code}" "$BASE_URL/memories?user_id=test_user_001")
        get_http_code=$(echo "$get_response" | tail -c 4)
        
        if [ "$get_http_code" = "200" ]; then
            print_success "内存获取API正常"
        else
            print_error "内存获取API异常，HTTP状态码: $get_http_code"
        fi
    else
        print_error "内存创建API异常，HTTP状态码: $http_code"
        echo "响应内容: $(echo "$response" | head -c -4)"
    fi
}

# 测试数据库连接
test_database_connection() {
    print_info "测试数据库连接..."
    
    # 检查PostgreSQL
    if docker compose -f docker/docker-compose.prod.yaml exec -T postgres pg_isready -U mem0_user > /dev/null 2>&1; then
        print_success "PostgreSQL连接正常"
    else
        print_error "PostgreSQL连接异常"
        return 1
    fi
    
    # 检查Neo4j（通过容器健康检查）
    neo4j_health=$(docker compose -f docker/docker-compose.prod.yaml ps neo4j --format "table {{.State}}" | tail -n 1)
    if [[ "$neo4j_health" == *"healthy"* ]]; then
        print_success "Neo4j连接正常"
    else
        print_error "Neo4j连接异常，状态: $neo4j_health"
    fi
    
    # 检查Milvus
    milvus_health=$(docker compose -f docker/docker-compose.prod.yaml ps milvus-standalone --format "table {{.State}}" | tail -n 1)
    if [[ "$milvus_health" == *"healthy"* ]]; then
        print_success "Milvus连接正常"
    else
        print_error "Milvus连接异常，状态: $milvus_health"
    fi
}

# 测试日志记录
test_logging() {
    print_info "测试日志记录..."
    
    if [ -f "logs/mem0.log" ]; then
        log_size=$(stat -f%z "logs/mem0.log" 2>/dev/null || stat -c%s "logs/mem0.log" 2>/dev/null || echo "0")
        if [ "$log_size" -gt "0" ]; then
            print_success "应用日志正常记录"
        else
            print_error "应用日志文件为空"
        fi
    else
        print_error "应用日志文件不存在"
    fi
    
    if [ -f "logs/access.log" ]; then
        print_success "访问日志文件存在"
    else
        print_error "访问日志文件不存在"
    fi
}

# 运行所有测试
run_all_tests() {
    echo ""
    echo "开始运行测试..."
    echo ""
    
    failed_tests=0
    
    test_api_reachability || ((failed_tests++))
    echo ""
    
    test_basic_api || ((failed_tests++))
    echo ""
    
    test_memory_api || ((failed_tests++))
    echo ""
    
    test_database_connection || ((failed_tests++))
    echo ""
    
    test_logging || ((failed_tests++))
    echo ""
    
    # 测试总结
    echo "=== 测试结果总结 ==="
    if [ $failed_tests -eq 0 ]; then
        print_success "所有测试通过！生产环境部署成功 🎉"
        echo ""
        echo "🌐 服务访问地址:"
        echo "  - API文档: $BASE_URL/docs"
        echo "  - PostgreSQL: localhost:15432"
        echo "  - Neo4j: http://localhost:17474"
        echo "  - Minio: http://localhost:19001"
        echo ""
        echo "📋 后续操作:"
        echo "  - 查看日志: ./scripts/manage.sh logs"
        echo "  - 监控状态: ./scripts/manage.sh status"
        echo "  - 备份数据: ./scripts/manage.sh backup"
    else
        print_error "有 $failed_tests 个测试失败，请检查日志:"
        echo ""
        echo "📋 故障排除:"
        echo "  - 查看服务状态: ./scripts/manage.sh status"
        echo "  - 查看详细日志: ./scripts/manage.sh logs"
        echo "  - 重启服务: ./scripts/manage.sh restart"
        exit 1
    fi
}

# 主函数
main() {
    # 检查服务是否运行
    if ! docker compose -f docker/docker-compose.prod.yaml ps | grep -q "Up"; then
        print_error "生产环境服务未运行，请先执行: ./scripts/run.sh"
        exit 1
    fi
    
    run_all_tests
}

# 执行主函数
main "$@"