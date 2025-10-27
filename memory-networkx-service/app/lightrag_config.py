"""
LightRAG 配置和初始化模块
"""
from typing import Optional, Callable
from pydantic import BaseModel
import os
import logging

try:
    from lightrag import LightRAG, QueryParam
    from lightrag.llm import openai_complete_if_cache, openai_embedding
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False
    LightRAG = None
    QueryParam = None

logger = logging.getLogger(__name__)


class LightRAGConfig(BaseModel):
    """LightRAG 配置"""
    # LLM 配置
    llm_model: str = "gpt-4o-mini"
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    
    # Embedding 配置
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    
    # 存储配置
    working_dir: str = "./lightrag_data"
    vector_storage: str = "local"  # local, chroma, qdrant, weaviate
    graph_storage: str = "networkx"  # networkx, neo4j
    
    # 检索配置
    top_k: int = 10
    max_token_for_text_unit: int = 4000
    max_token_for_global_context: int = 4000
    max_token_for_local_context: int = 4000
    
    # 缓存配置
    enable_llm_cache: bool = True
    cache_dir: str = "./lightrag_cache"


class LightRAGManager:
    """LightRAG 管理器 - 单例模式"""
    
    _instance = None
    _rag_instances = {}  # session_id -> LightRAG 实例
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            if not LIGHTRAG_AVAILABLE:
                logger.warning("LightRAG 库未安装，将使用降级模式")
                self.config = None
                self.initialized = True
                return
            
            self.config = LightRAGConfig(
                llm_api_key=os.getenv("OPENAI_API_KEY", ""),
                llm_api_base=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
                llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                working_dir=os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_data"),
                cache_dir=os.getenv("LIGHTRAG_CACHE_DIR", "./lightrag_cache"),
            )
            
            # 创建必要的目录
            os.makedirs(self.config.working_dir, exist_ok=True)
            os.makedirs(self.config.cache_dir, exist_ok=True)
            
            self.initialized = True
            logger.info("LightRAG 管理器已初始化")
    
    def is_available(self) -> bool:
        """检查 LightRAG 是否可用"""
        return LIGHTRAG_AVAILABLE and self.config is not None
    
    def get_rag_instance(self, session_id: str):
        """获取或创建指定 session 的 LightRAG 实例"""
        if not self.is_available():
            logger.warning("LightRAG 不可用，返回 None")
            return None
        
        if session_id not in self._rag_instances:
            working_dir = os.path.join(self.config.working_dir, session_id)
            os.makedirs(working_dir, exist_ok=True)
            
            try:
                self._rag_instances[session_id] = LightRAG(
                    working_dir=working_dir,
                    llm_model_func=self._create_llm_func(),
                    embedding_func=self._create_embedding_func(),
                    # 可以添加更多配置
                    # max_async=4,
                    # max_tokens=self.config.max_token_for_text_unit,
                )
                logger.info(f"创建 LightRAG 实例: session_id={session_id}")
            except Exception as e:
                logger.error(f"创建 LightRAG 实例失败: {e}", exc_info=True)
                return None
        
        return self._rag_instances[session_id]
    
    def _create_llm_func(self) -> Callable:
        """创建 LLM 函数"""
        async def llm_func(
            prompt: str, 
            system_prompt: Optional[str] = None, 
            history_messages: list = None,
            **kwargs
        ) -> str:
            """LLM 调用函数"""
            if history_messages is None:
                history_messages = []
            
            try:
                result = await openai_complete_if_cache(
                    model=self.config.llm_model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    api_key=self.config.llm_api_key,
                    base_url=self.config.llm_api_base,
                    **kwargs
                )
                return result
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}", exc_info=True)
                raise
        
        return llm_func
    
    def _create_embedding_func(self) -> Callable:
        """创建 Embedding 函数"""
        async def embedding_func(texts: list[str]):
            """Embedding 生成函数"""
            try:
                import numpy as np
                
                result = await openai_embedding(
                    texts=texts,
                    model=self.config.embedding_model,
                    api_key=self.config.llm_api_key,
                    base_url=self.config.llm_api_base,
                )
                
                # 确保返回正确的格式
                if isinstance(result, list):
                    return np.array(result)
                return result
            except Exception as e:
                logger.error(f"Embedding 生成失败: {e}", exc_info=True)
                raise
        
        return embedding_func
    
    def remove_instance(self, session_id: str):
        """移除指定 session 的 RAG 实例"""
        if session_id in self._rag_instances:
            try:
                # LightRAG 实例可能需要清理资源
                del self._rag_instances[session_id]
                logger.info(f"移除 LightRAG 实例: session_id={session_id}")
            except Exception as e:
                logger.error(f"移除 LightRAG 实例失败: {e}")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_instances": len(self._rag_instances),
            "active_sessions": list(self._rag_instances.keys()),
            "lightrag_available": self.is_available(),
        }
