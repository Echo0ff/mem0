import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
import time
import random
import threading
from collections import deque
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from mem0 import Memory
from database import create_memory_with_pg_storage

# Load environment variables
load_dotenv()

# 配置日志
import logging
import sys

def setup_logging():
    """根据环境配置应用日志，生产环境支持文件和控制台双输出"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除所有现有的 handlers，避免冲突
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(log_format)

    if os.getenv("ENVIRONMENT") == "production":
        print("Production logging configured for both file and console.")
        # 生产环境 1: 文件 Handler
        log_dir = "/app/logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(f"{log_dir}/mem0.log")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # 生产环境 2: 控制台 Handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    else:
        # 开发环境: 只输出到控制台
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        print("Development logging configured. Logs will be printed to the console.")

    # 调整其他库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("gunicorn.error").setLevel(logging.INFO)

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
    # 事实抽取提示词（用于 add 流程的 facts 识别）：严格 JSON，键为 facts，最多 10 条
    "custom_fact_extraction_prompt": (
        "你是事实抽取引擎。必须严格输出 JSON，不得包含任何解释、代码块或 Markdown。\n"
        "规则：\n"
        "1) 从输入文本中抽取独立、可记忆的简短事实（陈述句），每条≤20字。\n"
        "2) 去重、去同义改写；严禁臆造上下文不存在的信息。\n"
        "3) 最多返回 10 条。\n\n"
        "输出格式（仅此 JSON）：\n"
        "{\n  \"facts\": [\n    \"喜欢周杰伦\",\n    \"最近在玩原神\"\n  ]\n}\n\n"
        "输入：\n{INPUT_TEXT}"
    ),
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
        # 关系抽取补强提示（会注入 EXTRACT_RELATIONS_PROMPT 的 CUSTOM_PROMPT）
        "custom_prompt": (
            "关系抽取要求（严格遵守）：\n"
            "1) 只在已抽取的实体列表之间建立关系，不得引入新实体。\n"
            "2) 关系三元组格式：{\\\"source\\\":..., \\\"relationship\\\":..., \\\"destination\\\":...}。\n"
            "3) source/destination 必须来自给定实体列表。\n"
            "4) relationship 用中文动词或动宾短语（如：喜爱、观看、练习钢琴、就职于、学习于、创作…）；无法匹配明确谓词则跳过。\n"
            "5) 最多返回 10 条高置信三元组；置信不足或语义含糊的关系不要返回；不得跨句强联。\n"
            "6) 严禁臆造文本中不存在的关系或隐含前提。\n"
            "7) 仅输出 JSON，不要任何解释。\n"
            "输出格式：{\\\"entities\\\":[{\\\"source\\\":\\\"user_01\\\",\\\"relationship\\\":\\\"喜欢\\\",\\\"destination\\\":\\\"周杰伦\\\"}]}"
        ),
        # 关系抽取使用常规 openai 适配，function call 未命中时将走 JSON fallback
        "llm": {
            "provider": "openai",
            "config": {
                "api_key": GLM_API_KEY or "sk-dummy-key",
                "model": GLM_MODEL,
                "temperature": 0.2,
                "openai_base_url": GLM_BASE_URL,
            },
        },
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
    # 更新决策提示：控制 ADD/UPDATE/DELETE 与 NONE
    "custom_update_memory_prompt": (
        "根据‘新事实’与‘已存在记忆’生成操作列表。\n"
        "规则：\n"
        "1) 去重：如与已存事实语义等价（或同义改写），返回 NONE。\n"
        "2) 冲突：同一槽位冲突时用 UPDATE（携带 previous_memory），不要重复 ADD。\n"
        "3) 归一：记忆用简短陈述（≤20字），避免形容词堆砌。\n"
        "4) 一次最多 8 条操作。\n"
        "仅输出 JSON：{\\\"memory\\\":[{\\\"id\\\":\\\"0\\\",\\\"event\\\":\\\"ADD\\\",\\\"text\\\":\\\"喜欢周杰伦\\\"}]}"
    ),
    "history_db_path": HISTORY_DB_PATH,
}


# 根据环境变量选择存储类型（延迟初始化，避免在进程 fork 前建立连接）
STORAGE_TYPE = os.environ.get("STORAGE_TYPE", "sqlite")

# 惰性实例，占位
MEMORY_INSTANCE: Optional[Memory] = None

def build_memory_instance() -> Memory:
    if STORAGE_TYPE.lower() == "postgresql":
        return create_memory_with_pg_storage(DEFAULT_CONFIG)
    return Memory.from_config(DEFAULT_CONFIG)

def _ensure_memory() -> None:
    global MEMORY_INSTANCE
    if MEMORY_INSTANCE is None:
        try:
            MEMORY_INSTANCE = build_memory_instance()
        except Exception as e:
            logging.error("Failed to initialize MEMORY_INSTANCE", exc_info=True)
            raise e

app = FastAPI(
    title="Mem0 REST APIs",
    description="A REST API for managing and searching memories for your AI Agents and Apps.",
    version="1.0.0",
)

# 添加CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
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
    limit: Optional[int] = 20
    threshold: Optional[float] = 1.3


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
                
        # 重新构建实例
        MEMORY_INSTANCE = Memory.from_config(merged_config)
        return {"message": "Configuration set successfully"}
    except Exception as e:
        logging.exception("Error in set_config:")
        raise HTTPException(status_code=500, detail=str(e))


def _run_add_background(messages: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
    # ---- 轻量并发与限流控制 ----
    global _BG_SEM, _RATE_BUCKET
    try:
        _BG_SEM.acquire()

        # 简单令牌桶：保证每秒调用不超过 BG_RPS 次
        _rate_limit_consume()

        # 惰性初始化内存实例
        _ensure_memory()

        # 重试策略：指数退避 + 抖动
        max_retries = int(os.getenv("BG_MAX_RETRIES", "2"))
        base_sleep = float(os.getenv("BG_RETRY_BASE", "0.6"))

        attempt = 1
        while True:
            try:
                resp = MEMORY_INSTANCE.add(messages=messages, **params)
                logging.info(f"[bg-add] success: {resp}")
                break
            except Exception as e:
                if attempt >= max_retries:
                    logging.exception("[bg-add] failed (max retries reached)")
                    break
                sleep_s = base_sleep * (2 ** (attempt - 1))
                sleep_s = sleep_s + random.uniform(0, 0.3)
                logging.warning(f"[bg-add] retry #{attempt} in {sleep_s:.2f}s due to: {e}")
                time.sleep(sleep_s)
                attempt += 1
    except Exception:
        logging.exception("[bg-add] fatal error")
    finally:
        try:
            _BG_SEM.release()
        except Exception:
            pass


# ---- 全局限流器与并发控制 ----
_BG_MAX_CONCURRENCY = int(os.getenv("BG_MAX_CONCURRENCY", "2"))
_BG_SEM = threading.Semaphore(_BG_MAX_CONCURRENCY)

_BG_RPS = float(os.getenv("BG_RPS", "1"))  # 每秒最大调用次数（LLM/API保护）
_RATE_BUCKET = deque(maxlen=1024)  # 存放最近调用时间戳
_RATE_LOCK = threading.Lock()


def _rate_limit_consume():
    """阻塞等待直到满足 RPS 限制。"""
    if _BG_RPS <= 0:
        return
    with _RATE_LOCK:
        now = time.time()
        window_start = now - 1.0
        # 清理窗口外的时间戳
        while _RATE_BUCKET and _RATE_BUCKET[0] < window_start:
            _RATE_BUCKET.popleft()
        if len(_RATE_BUCKET) >= _BG_RPS:
            sleep_s = _RATE_BUCKET[0] + 1.0 - now
            if sleep_s > 0:
                time.sleep(sleep_s)
        # 记录本次调用时间
        _RATE_BUCKET.append(time.time())


@app.post("/memories", summary="Create memories")
def add_memory(memory_create: MemoryCreate):
    """Store new memories."""
    if not any([memory_create.user_id, memory_create.agent_id, memory_create.run_id]):
        raise HTTPException(status_code=400, detail="At least one identifier (user_id, agent_id, run_id) is required.")

    params = {k: v for k, v in memory_create.model_dump().items() if v is not None and k != "messages"}
    try:
        _ensure_memory()
        response = MEMORY_INSTANCE.add(messages=[m.model_dump() for m in memory_create.messages], **params)
        return JSONResponse(content=response)
    except Exception as e:
        logging.exception("Error in add_memory:")  # This will log the full traceback
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/async", summary="Create memories asynchronously (non-blocking)")
def add_memory_async(memory_create: MemoryCreate, background_tasks: BackgroundTasks):
    if not any([memory_create.user_id, memory_create.agent_id, memory_create.run_id]):
        raise HTTPException(status_code=400, detail="At least one identifier (user_id, agent_id, run_id) is required.")

    params = {k: v for k, v in memory_create.model_dump().items() if v is not None and k != "messages"}
    messages = [m.model_dump() for m in memory_create.messages]

    try:
        background_tasks.add_task(_run_add_background, messages, params)
        return JSONResponse(content={"accepted": True}, status_code=202)
    except Exception as e:
        logging.exception("Error in add_memory_async:")
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
        _ensure_memory()
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
        _ensure_memory()
        return MEMORY_INSTANCE.get(memory_id)
    except Exception as e:
        logging.exception("Error in get_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", summary="Search memories")
def search_memories(search_req: SearchRequest):
    """Search for memories based on a query."""
    try:
        _ensure_memory()
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
        _ensure_memory()
        return MEMORY_INSTANCE.update(memory_id=memory_id, data=updated_memory)
    except Exception as e:
        logging.exception("Error in update_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}/history", summary="Get memory history")
def memory_history(memory_id: str):
    """Retrieve memory history."""
    try:
        _ensure_memory()
        return MEMORY_INSTANCE.history(memory_id=memory_id)
    except Exception as e:
        logging.exception("Error in memory_history:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memories/{memory_id}", summary="Delete a memory")
def delete_memory(memory_id: str):
    """Delete a specific memory by ID."""
    try:
        _ensure_memory()
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
        _ensure_memory()
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
        _ensure_memory()
        MEMORY_INSTANCE.reset()
        return {"message": "All memories reset"}
    except Exception as e:
        logging.exception("Error in reset_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
def home():
    """Redirect to the OpenAPI documentation."""
    return RedirectResponse(url="/docs")

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
