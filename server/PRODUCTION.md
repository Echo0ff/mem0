# Mem0 生产环境部署指南

## 🚀 快速部署

### 1. 环境准备

确保服务器已安装：
- Docker Engine (>=20.10)
- Docker Compose (>=2.0)
- Git

### 2. 克隆代码

```bash
git clone <your-repo-url>
cd mem0/server
```

### 3. 配置环境变量

复制并编辑生产环境配置：

```bash
cp .env.prod.example .env.prod
vim .env.prod
```

**重要：请务必修改以下配置项：**

```bash
# API密钥 - 必须配置
GLM_API_KEY=your_real_glm_api_key
SILICONFLOW_API_KEY=your_real_siliconflow_api_key

# 数据库密码 - 建议修改
DATABASE_URL=postgresql://mem0_user:your_secure_password@postgres:5432/mem0_prod
NEO4J_PASSWORD=your_secure_neo4j_password

# 安全配置 - 必须修改
SECRET_KEY=your_super_secret_key_change_this_in_production
```

### 4. 一键部署

```bash
# 构建镜像
./scripts/build.sh

# 启动服务
./scripts/run.sh
```

## 🛠️ 管理命令

使用综合管理脚本：

```bash
# 查看帮助
./scripts/manage.sh help

# 常用命令
./scripts/manage.sh build          # 构建镜像
./scripts/manage.sh run            # 启动服务
./scripts/manage.sh stop           # 停止服务
./scripts/manage.sh restart        # 重启服务
./scripts/manage.sh status         # 查看状态
./scripts/manage.sh logs           # 查看所有日志
./scripts/manage.sh logs mem0      # 查看特定服务日志
./scripts/manage.sh shell mem0     # 进入容器shell
./scripts/manage.sh backup         # 备份数据
./scripts/manage.sh remove         # 清理环境
./scripts/manage.sh remove --all   # 删除所有数据
```

## 🌐 服务访问

部署成功后可通过以下地址访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| Mem0 API | http://localhost:18888/docs | API文档和测试界面 |
| PostgreSQL | localhost:15432 | 数据库连接 |
| Neo4j | http://localhost:17474 | 图数据库管理界面 |
| Minio | http://localhost:19001 | 对象存储管理界面 |

## 📁 文件结构

```
server/
├── docker/                     # Docker配置文件目录
│   ├── docker-compose.dev.yaml   # 开发环境Docker Compose配置
│   ├── docker-compose.prod.yaml  # 生产环境Docker Compose配置
│   ├── dev.Dockerfile             # 开发环境Dockerfile
│   ├── prod.Dockerfile            # 生产环境Dockerfile
│   ├── start.dev.sh               # 开发启动脚本
│   └── start.prod.sh              # 生产启动脚本
├── database/                   # 数据库相关模块
├── scripts/                    # 管理脚本目录
│   ├── manage.sh              # 综合管理脚本
│   ├── build.sh               # 构建脚本
│   ├── run.sh                 # 运行脚本
│   ├── remove.sh              # 清理脚本
│   └── test.sh                # 测试脚本
├── .env.prod                   # 生产环境配置
├── logs/                       # 日志文件目录（自动创建）
├── data/                       # 数据持久化目录（自动创建）
└── backups/                    # 备份目录（自动创建）
```

## 📊 监控和日志

### 查看日志

```bash
# 实时查看应用日志
./scripts/manage.sh logs mem0

# 查看日志文件
tail -f logs/mem0.log      # 应用日志
tail -f logs/access.log    # 访问日志
tail -f logs/error.log     # 错误日志
```

### 健康检查

```bash
# 检查服务状态
./scripts/manage.sh status

# 手动健康检查
curl -f http://localhost:18888/docs
```

## 🔧 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   lsof -i :18888
   
   # 修改docker-compose.prod.yaml中的端口映射
   ```

2. **服务启动失败**
   ```bash
   # 查看详细日志
   ./scripts/manage.sh logs
   
   # 检查配置文件
   cat .env.prod
   ```

3. **数据库连接失败**
   ```bash
   # 检查PostgreSQL状态
   ./scripts/manage.sh logs postgres
   
   # 进入数据库容器
   ./scripts/manage.sh shell postgres
   ```

### 重新部署

```bash
# 完全重新部署（会删除所有数据）
./scripts/manage.sh remove --all
./scripts/manage.sh build
./scripts/manage.sh run
```

## 🔒 安全建议

1. **修改默认密码**：确保修改所有默认密码
2. **API密钥安全**：不要将API密钥提交到版本控制
3. **网络安全**：考虑使用反向代理和SSL证书
4. **定期备份**：定期执行数据备份
5. **日志轮转**：配置日志轮转防止磁盘空间耗尽

## 📈 性能优化

### 资源配置

根据服务器资源调整以下配置：

```bash
# .env.prod
WORKERS=4                    # Gunicorn worker数量
MAX_CONNECTIONS=100          # 最大连接数
POOL_SIZE=20                # 数据库连接池大小
```

### 数据库优化

```sql
-- PostgreSQL性能调优（根据服务器内存调整）
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
```

## 🔄 更新流程

```bash
# 拉取最新代码并更新
./scripts/manage.sh update
```

## 📞 支持

如遇问题，请检查：
1. 日志文件：`./logs/`
2. 服务状态：`./scripts/manage.sh status`
3. 配置文件：`.env.prod`

---

**注意**：生产环境部署前请确保充分测试，并做好数据备份。