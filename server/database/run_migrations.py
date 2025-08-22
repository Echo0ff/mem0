#!/usr/bin/env python3
"""
数据库迁移脚本
在Docker容器启动时运行，确保PostgreSQL数据库结构是最新的
"""
import os
import sys
import logging
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """运行Alembic数据库迁移"""
    try:
        # 检查是否使用PostgreSQL
        storage_type = os.getenv("STORAGE_TYPE", "sqlite")
        if storage_type.lower() != "postgresql":
            logger.info("Not using PostgreSQL, skipping migrations")
            return

        # 配置Alembic
        alembic_cfg = Config("alembic.ini")
        
        # 设置数据库URL
        database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:postgres@postgres:5432/postgres"
        )
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        logger.info(f"Running migrations with database URL: {database_url}")
        
        # 运行迁移
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()