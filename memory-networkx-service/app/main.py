"""
Memory Enhancement Service - 基于 NetworkX 的增强记忆服务
用于与 Higress ai-history 插件集成
"""
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from app.memory_engine import MemoryEngine
from app.config import Settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="Memory Enhancement Service",
    description="基于 NetworkX 的 AI 对话记忆增强服务",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载配置
settings = Settings()

# 全局记忆引擎实例（按 session_id 分组）
memory_engines: Dict[str, MemoryEngine] = {}


# ========== 请求/响应模型 ==========

class MemoryEnhanceRequest(BaseModel):
    """增强记忆请求"""
    session_id: str
    question: str
    answer: str
    metadata: Optional[Dict[str, Any]] = None


class MemoryRetrieveRequest(BaseModel):
    """检索记忆请求"""
    session_id: str
    query: str
    top_k: Optional[int] = 5


class MemoryEnhanceResponse(BaseModel):
    """增强记忆响应"""
    status: str
    message: str
    session_id: str


class MemoryRetrieveResponse(BaseModel):
    """检索记忆响应"""
    status: str
    context: List[str]
    metadata: Dict[str, Any]
    session_id: str


class MemoryStatsResponse(BaseModel):
    """记忆统计响应"""
    session_id: str
    total_memories: int
    graph_nodes: int
    graph_edges: int
    avg_degree: float


# ========== 辅助函数 ==========

def get_memory_engine(session_id: str) -> MemoryEngine:
    """获取或创建指定 session 的记忆引擎"""
    if session_id not in memory_engines:
        logger.info(f"创建新的记忆引擎: session_id={session_id}")
        memory_engines[session_id] = MemoryEngine(
            session_id=session_id,
            redis_host=settings.redis_host,
            redis_port=settings.redis_port,
            redis_password=settings.redis_password,
            redis_db=settings.redis_db
        )
    return memory_engines[session_id]


# ========== API 端点 ==========

@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "Memory Enhancement Service",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


@app.post("/api/v1/memory/enhance", response_model=MemoryEnhanceResponse)
async def enhance_memory(request: MemoryEnhanceRequest):
    """
    接收对话，更新知识图谱
    
    Args:
        request: 包含 session_id, question, answer 的请求
        
    Returns:
        增强记忆的响应
    """
    try:
        logger.info(f"收到增强记忆请求: session_id={request.session_id}")
        
        # 获取记忆引擎
        engine = get_memory_engine(request.session_id)
        
        # 添加对话到记忆系统
        await engine.add_conversation(
            question=request.question,
            answer=request.answer,
            metadata=request.metadata or {}
        )
        
        logger.info(f"成功添加记忆: session_id={request.session_id}")
        
        return MemoryEnhanceResponse(
            status="success",
            message="Memory enhanced successfully",
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"增强记忆失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memory/retrieve", response_model=MemoryRetrieveResponse)
async def retrieve_context(request: MemoryRetrieveRequest):
    """
    检索增强上下文
    
    Args:
        request: 包含 session_id, query, top_k 的请求
        
    Returns:
        检索到的相关记忆上下文
    """
    try:
        logger.info(f"收到检索请求: session_id={request.session_id}, query={request.query[:50]}...")
        
        # 获取记忆引擎
        engine = get_memory_engine(request.session_id)
        
        # 检索相关上下文
        context, metadata = await engine.retrieve_relevant_context(
            query=request.query,
            top_k=request.top_k or 5
        )
        
        logger.info(f"成功检索 {len(context)} 条记忆")
        
        return MemoryRetrieveResponse(
            status="success",
            context=context,
            metadata=metadata,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"检索记忆失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memory/stats/{session_id}", response_model=MemoryStatsResponse)
async def get_memory_stats(session_id: str):
    """
    获取记忆统计信息
    
    Args:
        session_id: 会话 ID
        
    Returns:
        记忆统计信息
    """
    try:
        engine = get_memory_engine(session_id)
        stats = await engine.get_stats()
        
        return MemoryStatsResponse(
            session_id=session_id,
            **stats
        )
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/memory/{session_id}")
async def delete_memory(session_id: str):
    """
    删除指定会话的所有记忆
    
    Args:
        session_id: 会话 ID
        
    Returns:
        删除结果
    """
    try:
        if session_id in memory_engines:
            await memory_engines[session_id].clear_all()
            del memory_engines[session_id]
            logger.info(f"已删除会话记忆: session_id={session_id}")
            
        return {
            "status": "success",
            "message": f"Memory for session {session_id} deleted",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"删除记忆失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Memory Enhancement Service 启动中...")
    logger.info(f"Redis 配置: {settings.redis_host}:{settings.redis_port}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Memory Enhancement Service 关闭中...")
    # 清理所有记忆引擎
    for session_id, engine in memory_engines.items():
        await engine.close()
    logger.info("所有记忆引擎已关闭")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
