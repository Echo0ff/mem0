# Docker 配置文件目录

本目录包含所有Docker相关的配置文件，用于开发和生产环境的容器化部署。

## 📁 文件说明

### Dockerfile
- `dev.Dockerfile` - 开发环境镜像构建文件
- `prod.Dockerfile` - 生产环境镜像构建文件

### Docker Compose
- `docker-compose.dev.yaml` - 开发环境服务编排配置
- `docker-compose.prod.yaml` - 生产环境服务编排配置

### 启动脚本
- `start.dev.sh` - 开发环境应用启动脚本
- `start.prod.sh` - 生产环境应用启动脚本

## 🚀 使用方法

### 开发环境
```bash
# 在server根目录执行
docker compose -f docker/docker-compose.dev.yaml up -d
```

### 生产环境
```bash
# 使用管理脚本（推荐）
./scripts/manage.sh run

# 或直接使用docker compose
docker compose -f docker/docker-compose.prod.yaml up -d
```

## 🔧 配置说明

### 开发环境特性
- 使用`--reload`模式支持热重载
- 挂载本地代码目录，支持实时代码修改
- 使用开发数据库配置
- 日志输出到控制台

### 生产环境特性
- 使用Gunicorn + Uvicorn Workers
- 多进程部署提升性能
- 数据持久化卷配置
- 健康检查和自动重启
- 日志文件持久化
- 安全配置（非root用户运行）

## 📝 路径配置

所有路径都已相对于server根目录进行配置：
- 构建上下文：`../..` (项目根目录)
- 配置文件：`../.env` 或 `../.env.prod`
- 数据目录：`../data`, `../logs` 等

## 🛠️ 维护指南

### 修改配置
1. 修改对应的docker-compose文件
2. 重新构建镜像：`./scripts/build.sh`
3. 重启服务：`./scripts/manage.sh restart`

### 添加新服务
1. 在相应的docker-compose文件中添加服务定义
2. 确保网络和依赖关系正确配置
3. 更新健康检查配置

### 端口管理
- 开发环境：8888端口
- 生产环境：18888端口
- 确保端口不与现有服务冲突