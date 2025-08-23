import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os

logger = logging.getLogger(__name__)

Base = declarative_base()


class History(Base):
    __tablename__ = "history"

    id = Column(String, primary_key=True, index=True)
    memory_id = Column(String, index=True)
    old_memory = Column(Text, nullable=True)
    new_memory = Column(Text, nullable=True)
    event = Column(String)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    is_deleted = Column(Integer, default=0)
    actor_id = Column(String, nullable=True)
    role = Column(String, nullable=True)


class PostgreSQLManager:
    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL", 
                "postgresql://postgres:postgres@postgres:5432/postgres"
            )
        
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建表（如果不存在）
        Base.metadata.create_all(bind=self.engine)

    def get_db(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

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
        db = self.get_db()
        try:
            # 处理时间戳
            created_at_dt = None
            updated_at_dt = None
            
            if created_at:
                try:
                    created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid created_at format: {created_at}")
                    created_at_dt = datetime.utcnow()
            
            if updated_at:
                try:
                    updated_at_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid updated_at format: {updated_at}")
                    updated_at_dt = None

            history_record = History(
                id=str(uuid.uuid4()),
                memory_id=memory_id,
                old_memory=old_memory,
                new_memory=new_memory,
                event=event,
                created_at=created_at_dt,
                updated_at=updated_at_dt,
                is_deleted=is_deleted,
                actor_id=actor_id,
                role=role,
            )
            
            db.add(history_record)
            db.commit()
            logger.debug(f"Added history record for memory_id: {memory_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to add history record: {e}")
            raise
        finally:
            db.close()

    def get_history(self, memory_id: str) -> List[Dict[str, Any]]:
        """获取记忆历史"""
        db = self.get_db()
        try:
            history_records = (
                db.query(History)
                .filter(History.memory_id == memory_id)
                .order_by(History.created_at.asc(), History.updated_at.asc())
                .all()
            )

            return [
                {
                    "id": record.id,
                    "memory_id": record.memory_id,
                    "old_memory": record.old_memory,
                    "new_memory": record.new_memory,
                    "event": record.event,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                    "is_deleted": bool(record.is_deleted),
                    "actor_id": record.actor_id,
                    "role": record.role,
                }
                for record in history_records
            ]
            
        except Exception as e:
            logger.error(f"Failed to get history for memory_id {memory_id}: {e}")
            raise
        finally:
            db.close()

    def reset(self) -> None:
        """重置历史表（删除所有数据）"""
        db = self.get_db()
        try:
            db.query(History).delete()
            db.commit()
            logger.info("History table reset successfully")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to reset history table: {e}")
            raise
        finally:
            db.close()

    def close(self) -> None:
        """关闭数据库连接"""
        if hasattr(self, 'engine'):
            self.engine.dispose()

    def __del__(self):
        self.close()