#!/bin/bash
set -e

echo "Starting Mem0 application..."

# 运行数据库迁移
echo "Running database migrations..."
cd database && python run_migrations.py && cd ..

# 启动应用
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload