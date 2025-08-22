import os
import logging
from typing import Protocol, Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageProtocol(Protocol):
    """存储协议接口"""
    
    def add_history(
        self,
        memory_id: str,
        old_memory: Optional[str],
        new_memory: Optional[str],
        event: str,
        *,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        is_deleted: int = 0,
        actor_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> None:
        """添加历史记录"""
        ...

    def get_history(self, memory_id: str) -> List[Dict[str, Any]]:
        """获取记忆历史"""
        ...

    def reset(self) -> None:
        """重置存储"""
        ...

    def close(self) -> None:
        """关闭存储连接"""
        ...


class StorageFactory:
    """存储工厂类"""
    
    @staticmethod
    def create_storage() -> StorageProtocol:
        """根据环境变量创建相应的存储实例"""
        storage_type = os.getenv("STORAGE_TYPE", "sqlite")
        
        if storage_type.lower() == "postgresql":
            from .pg_storage import PostgreSQLManager
            database_url = os.getenv(
                "DATABASE_URL", 
                "postgresql://postgres:postgres@postgres:5432/postgres"
            )
            logger.info(f"Using PostgreSQL storage with URL: {database_url}")
            return PostgreSQLManager(database_url)
        else:
            # 导入原始的SQLiteManager
            import sys
            sys.path.append('../mem0/memory')
            from mem0.memory.storage import SQLiteManager
            
            db_path = os.getenv("HISTORY_DB_PATH", "/app/history/history.db")
            logger.info(f"Using SQLite storage with path: {db_path}")
            return SQLiteManager(db_path)