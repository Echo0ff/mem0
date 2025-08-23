import os
from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@postgres:5432/postgres"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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