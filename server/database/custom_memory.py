import os
from typing import Any, Dict, Optional
from mem0 import Memory
from mem0.configs.base import MemoryConfig
from .storage_factory import StorageFactory
import logging

logger = logging.getLogger(__name__)


class CustomMemory(Memory):
    """使用自定义存储的Memory类"""
    
    def __init__(self, config: MemoryConfig = MemoryConfig()):
        # 调用父类初始化，但不使用默认的SQLiteManager
        super().__init__(config)
        
        # 替换存储管理器
        if hasattr(self, 'db'):
            self.db.close()
        
        # 使用工厂创建存储实例
        self.db = StorageFactory.create_storage()
        logger.info(f"CustomMemory initialized with {type(self.db).__name__}")


def create_memory_with_pg_storage(config_dict: Dict[str, Any]) -> CustomMemory:
    """创建使用PostgreSQL存储的Memory实例"""
    try:
        config = MemoryConfig(**config_dict)
        return CustomMemory(config)
    except Exception as e:
        logger.error(f"Failed to create CustomMemory: {e}")
        raise