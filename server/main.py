import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from mem0 import Memory
from database import create_memory_with_pg_storage

# Load environment variables
load_dotenv()

# 配置日志
def setup_logging():
    """配置应用日志"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 根据环境配置日志
    if os.getenv("ENVIRONMENT") == "production":
        # 生产环境：仅输出到 stdout/stderr（交给 Docker 收集），避免文件句柄在多进程中的竞争
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[logging.StreamHandler()]
        )
    else:
        # 开发环境：只输出到控制台
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format
        )

setup_logging()


# Milvus configuration
MILVUS_HOST = os.environ.get("MILVUS_HOST", "milvus-standalone")
MILVUS_PORT = os.environ.get("MILVUS_PORT", "19530")
MILVUS_COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION_NAME", "memories")

# Neo4j configuration (保持与 docker-compose.prod.yaml 的 NEO4J_AUTH 一致)
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "mem0_graph_password_2024")

# GLM-4 configuration
GLM_API_KEY = os.environ.get("GLM_API_KEY")
GLM_BASE_URL = os.environ.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
GLM_MODEL = os.environ.get("GLM_MODEL", "glm-4-flash-250414")

# SiliconFlow Embedding configuration
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")

HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "/app/history/history.db")

# 不再需要设置全局环境变量，通过配置参数传递

# 使用 OpenAI provider 但配置自定义 base URL
DEFAULT_CONFIG = {
    "version": "v1.1",
    "vector_store": {
        "provider": "milvus",
        "config": {
            "url": f"http://{MILVUS_HOST}:{MILVUS_PORT}",
            "collection_name": MILVUS_COLLECTION_NAME,
            "embedding_model_dims": 1024,  # BAAI/bge-large-zh-v1.5 model outputs 1024 dimensions
        },
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {"url": NEO4J_URI, "username": NEO4J_USERNAME, "password": NEO4J_PASSWORD},
    },
    "llm": {
        "provider": "openai",
        "config": {
            "api_key": GLM_API_KEY or "sk-dummy-key",
            "model": GLM_MODEL,  # 使用实际的 GLM 模型名称
            "temperature": 0.2,
            "openai_base_url": GLM_BASE_URL,  # 指定 GLM API 的 base URL
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "api_key": SILICONFLOW_API_KEY or "sk-dummy-key",
            "model": EMBEDDING_MODEL,  # 使用实际的 embedding 模型名称
            "openai_base_url": SILICONFLOW_BASE_URL,  # 指定 SiliconFlow API 的 base URL
            "embedding_dims": 1024,  # Explicitly set to match BAAI/bge-large-zh-v1.5 model dimensions
        }
    },
    "history_db_path": HISTORY_DB_PATH,
}


# 根据环境变量选择存储类型
STORAGE_TYPE = os.environ.get("STORAGE_TYPE", "sqlite")

try:
    if STORAGE_TYPE.lower() == "postgresql":
        MEMORY_INSTANCE = create_memory_with_pg_storage(DEFAULT_CONFIG)
    else:
        MEMORY_INSTANCE = Memory.from_config(DEFAULT_CONFIG)
except Exception as e:
    logging.error("Failed to initialize MEMORY_INSTANCE", exc_info=True)
    raise e

app = FastAPI(
    title="Mem0 REST APIs",
    description="A REST API for managing and searching memories for your AI Agents and Apps.",
    version="1.0.0",
)


class Message(BaseModel):
    role: str = Field(..., description="Role of the message (user or assistant).")
    content: str = Field(..., description="Message content.")


class MemoryCreate(BaseModel):
    messages: List[Message] = Field(..., description="List of messages to store.")
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query.")
    user_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


@app.post("/configure", summary="Configure Mem0")
def set_config(config: Dict[str, Any]):
    """Set memory configuration."""
    global MEMORY_INSTANCE
    try:
        # Merge with default config to ensure all required fields are present
        merged_config = DEFAULT_CONFIG.copy()
        
        # Update with provided config
        for key, value in config.items():
            if key in merged_config:
                if isinstance(value, dict) and isinstance(merged_config[key], dict):
                    merged_config[key].update(value)
                else:
                    merged_config[key] = value
            else:
                merged_config[key] = value
                
        MEMORY_INSTANCE = Memory.from_config(merged_config)
        return {"message": "Configuration set successfully"}
    except Exception as e:
        logging.exception("Error in set_config:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories", summary="Create memories")
def add_memory(memory_create: MemoryCreate):
    """Store new memories."""
    if not any([memory_create.user_id, memory_create.agent_id, memory_create.run_id]):
        raise HTTPException(status_code=400, detail="At least one identifier (user_id, agent_id, run_id) is required.")

    params = {k: v for k, v in memory_create.model_dump().items() if v is not None and k != "messages"}
    try:
        response = MEMORY_INSTANCE.add(messages=[m.model_dump() for m in memory_create.messages], **params)
        return JSONResponse(content=response)
    except Exception as e:
        logging.exception("Error in add_memory:")  # This will log the full traceback
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories", summary="Get memories")
def get_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Retrieve stored memories."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(status_code=400, detail="At least one identifier is required.")
    try:
        params = {
            k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None
        }
        return MEMORY_INSTANCE.get_all(**params)
    except Exception as e:
        logging.exception("Error in get_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}", summary="Get a memory")
def get_memory(memory_id: str):
    """Retrieve a specific memory by ID."""
    try:
        return MEMORY_INSTANCE.get(memory_id)
    except Exception as e:
        logging.exception("Error in get_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", summary="Search memories")
def search_memories(search_req: SearchRequest):
    """Search for memories based on a query."""
    try:
        params = {k: v for k, v in search_req.model_dump().items() if v is not None and k != "query"}
        return MEMORY_INSTANCE.search(query=search_req.query, **params)
    except Exception as e:
        logging.exception("Error in search_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/memories/{memory_id}", summary="Update a memory")
def update_memory(memory_id: str, updated_memory: Dict[str, Any]):
    """Update an existing memory with new content.
    
    Args:
        memory_id (str): ID of the memory to update
        updated_memory (str): New content to update the memory with
        
    Returns:
        dict: Success message indicating the memory was updated
    """
    try:
        return MEMORY_INSTANCE.update(memory_id=memory_id, data=updated_memory)
    except Exception as e:
        logging.exception("Error in update_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}/history", summary="Get memory history")
def memory_history(memory_id: str):
    """Retrieve memory history."""
    try:
        return MEMORY_INSTANCE.history(memory_id=memory_id)
    except Exception as e:
        logging.exception("Error in memory_history:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories/{memory_id}", summary="Delete a memory")
def delete_memory(memory_id: str):
    """Delete a specific memory by ID."""
    try:
        MEMORY_INSTANCE.delete(memory_id=memory_id)
        return {"message": "Memory deleted successfully"}
    except Exception as e:
        logging.exception("Error in delete_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories", summary="Delete all memories")
def delete_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Delete all memories for a given identifier."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(status_code=400, detail="At least one identifier is required.")
    try:
        params = {
            k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None
        }
        MEMORY_INSTANCE.delete_all(**params)
        return {"message": "All relevant memories deleted"}
    except Exception as e:
        logging.exception("Error in delete_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset", summary="Reset all memories")
def reset_memory():
    """Completely reset stored memories."""
    try:
        MEMORY_INSTANCE.reset()
        return {"message": "All memories reset"}
    except Exception as e:
        logging.exception("Error in reset_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
def home():
    """Redirect to the OpenAPI documentation."""
    return RedirectResponse(url="/docs")
