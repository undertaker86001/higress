"""
Memory Engine - 记忆引擎核心实现
"""
import asyncio
import json
import logging
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
import redis.asyncio as redis
import numpy as np

from app.memory_graph import MemoryGraph
from app.memory_item import MemoryItem
from app.text_processor import TextProcessor

logger = logging.getLogger(__name__)


class MemoryEngine:
    """记忆引擎 - 管理单个会话的记忆"""
    
    def __init__(
        self,
        session_id: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_db: int = 0
    ):
        self.session_id = session_id
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.redis_db = redis_db
        
        # 初始化组件
        self.memory_graph = MemoryGraph()
        self.text_processor = TextProcessor()
        
        # Redis 客户端（延迟初始化）
        self._redis_client: Optional[redis.Redis] = None
        
        # 短期记忆缓存
        self.short_term_memory: List[Dict[str, Any]] = []
        self.short_term_memory_size = 20
        
        # 长期记忆列表
        self.long_term_memory: List[MemoryItem] = []
        
        # 配置参数
        self.retrieve_top_n = 5
        self.summary_max_tags = 30
        
        logger.info(f"记忆引擎已初始化: session_id={session_id}")
    
    async def _get_redis_client(self) -> redis.Redis:
        """获取 Redis 客户端（懒加载）"""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=self.redis_db,
                decode_responses=True
            )
            # 测试连接
            await self._redis_client.ping()
            logger.info(f"Redis 连接成功: {self.redis_host}:{self.redis_port}")
        return self._redis_client
    
    async def add_conversation(
        self,
        question: str,
        answer: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        添加对话到记忆系统
        
        Args:
            question: 用户问题
            answer: AI 回答
            metadata: 元数据
        """
        try:
            # 添加到短期记忆
            conversation = {
                "role": "user",
                "content": question,
                "timestamp": datetime.now().isoformat()
            }
            self.short_term_memory.append(conversation)
            
            conversation = {
                "role": "assistant",
                "content": answer,
                "timestamp": datetime.now().isoformat()
            }
            self.short_term_memory.append(conversation)
            
            # 如果短期记忆超出限制，转换为长期记忆
            if len(self.short_term_memory) >= self.short_term_memory_size:
                await self._convert_to_long_term_memory()
            
            # 保存到 Redis
            await self._save_to_redis()
            
        except Exception as e:
            logger.error(f"添加对话失败: {e}", exc_info=True)
            raise
    
    async def _tag_conversations(
        self,
        conversations: List[Dict[str, Any]],
        summary_flag: bool
    ) -> Tuple[str, List[str]]:
        """
        标记对话 - 生成摘要和标签
        
        这是原始 memory-networkx 的核心方法，用于：
        1. summary_flag=True: 生成完整摘要（转换长期记忆时）
        2. summary_flag=False: 快速提取标签（对话提取时）
        
        Args:
            conversations: 对话列表
            summary_flag: 是否生成完整摘要
            
        Returns:
            (摘要, 标签列表)
        """
        try:
            if summary_flag:
                # 完整模式：生成摘要和标签
                conversation_text = "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in conversations[-10:]  # 取最近10条
                ])
                summary = await self.text_processor.generate_summary(conversation_text)
                tags = await self.text_processor.extract_tags(conversation_text)
            else:
                # 快速模式：仅提取标签
                conversation_text = "\n".join([
                    msg['content']
                    for msg in conversations[-5:]  # 取最近5条
                ])
                summary = conversation_text[:100]  # 简单摘要
                tags = await self.text_processor.extract_tags(conversation_text)
            
            logger.debug(f"标记对话完成: summary_len={len(summary)}, tags_count={len(tags)}")
            return summary, tags
            
        except Exception as e:
            logger.error(f"标记对话失败: {e}", exc_info=True)
            return "", []
    
    async def _convert_to_long_term_memory(self) -> None:
        """将短期记忆转换为长期记忆"""
        try:
            # 使用 _tag_conversations 生成摘要和标签
            summary, tags = await self._tag_conversations(
                self.short_term_memory,
                summary_flag=True
            )
            
            # 添加时间标签
            tags.extend(self._generate_time_tags())
            tags = list(set(tags))  # 去重
            
            # 限制标签数量
            if len(tags) > self.summary_max_tags:
                tags = tags[:self.summary_max_tags]
            
            # 添加时间标签
            now = datetime.now()
            time_tag = f"DATETIME:{now.strftime('%Y-%m-%d %H:%M:%S')}"
            tags.append(time_tag)
            
            # 创建记忆项
            memory_item = MemoryItem(summary=summary, tags=tags)
            self.long_term_memory.append(memory_item)
            
            # 更新知识图谱
            self.memory_graph.add_memory(memory_item)
            
            # 清理部分短期记忆
            self.short_term_memory = self.short_term_memory[-10:]
            
            logger.info(f"已转换长期记忆: tags={len(tags)}, summary_len={len(summary)}")
            
        except Exception as e:
            logger.error(f"转换长期记忆失败: {e}", exc_info=True)
    
    def _generate_time_tags(self) -> List[str]:
        """
        生成时间标签
        
        Returns:
            时间标签列表 ["2024年", "1月", "15日", "上午"]
        """
        now = datetime.now()
        
        period = "上午"
        if now.hour >= 12:
            period = "下午"
        
        year_tag = f"{now.year}年"
        month_tag = f"{now.month}月"
        day_tag = f"{now.day}日"
        period_tag = period
        
        return [year_tag, month_tag, day_tag, period_tag]
    
    async def retrieve_relevant_context(
        self,
        query: str,
        top_k: int = 5
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        检索相关上下文
        
        Args:
            query: 查询文本
            top_k: 返回的记忆数量
            
        Returns:
            (相关记忆列表, 元数据字典)
        """
        try:
            # 提取查询关键词
            query_tags = await self.text_processor.extract_tags(query)
            
            if not query_tags:
                logger.warning("查询未提取到关键词")
                return [], {"query_tags": []}
            
            # 使用知识图谱扩展关键词
            expanded_tags = self.memory_graph.get_related_keywords(set(query_tags))
            
            # 合并查询关键词和扩展关键词
            all_tags = set(query_tags + expanded_tags[:20])  # 限制扩展数量
            
            logger.info(f"查询关键词: {query_tags}")
            logger.info(f"扩展关键词: {expanded_tags[:10]}")
            
            # 计算每个记忆的相关性得分
            scored_memories = []
            for memory in self.long_term_memory:
                memory_tags = set(memory.tags())
                
                # 计算 Jaccard 相似度
                intersection = len(memory_tags & all_tags)
                union = len(memory_tags | all_tags)
                jaccard = intersection / union if union > 0 else 0
                
                # 时间衰减因子
                time_diff = (datetime.now() - memory.time()).total_seconds()
                time_decay = np.exp(-time_diff / (7 * 24 * 3600))  # 7天半衰期
                
                # 综合得分
                score = jaccard * 0.7 + time_decay * 0.3
                
                if score > 0:
                    scored_memories.append((memory, score))
            
            # 排序并取 top_k
            scored_memories.sort(key=lambda x: x[1], reverse=True)
            top_memories = scored_memories[:top_k]
            
            # 提取摘要
            context = [memory.summary() for memory, score in top_memories]
            
            # 构建元数据
            metadata = {
                "query_tags": query_tags,
                "expanded_tags": expanded_tags[:10],
                "retrieved_count": len(context),
                "scores": [float(score) for _, score in top_memories]
            }
            
            logger.info(f"检索到 {len(context)} 条相关记忆")
            
            return context, metadata
            
        except Exception as e:
            logger.error(f"检索上下文失败: {e}", exc_info=True)
            return [], {"error": str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            "total_memories": len(self.long_term_memory),
            "graph_nodes": self.memory_graph.get_node_count(),
            "graph_edges": self.memory_graph.get_edge_count(),
            "avg_degree": self.memory_graph.get_avg_degree()
        }
    
    async def _save_to_redis(self) -> None:
        """保存记忆到 Redis"""
        try:
            client = await self._get_redis_client()
            
            # 保存短期记忆
            key = f"memory:{self.session_id}:short_term"
            await client.set(key, json.dumps(self.short_term_memory))
            
            # 保存长期记忆
            key = f"memory:{self.session_id}:long_term"
            long_term_data = [
                {
                    "summary": mem.summary(),
                    "tags": mem.tags(),
                    "time": mem.time().isoformat()
                }
                for mem in self.long_term_memory
            ]
            await client.set(key, json.dumps(long_term_data))
            
        except Exception as e:
            logger.error(f"保存到 Redis 失败: {e}", exc_info=True)
    
    async def clear_all(self) -> None:
        """清除所有记忆"""
        self.short_term_memory.clear()
        self.long_term_memory.clear()
        self.memory_graph.clear()
        
        # 从 Redis 删除
        try:
            client = await self._get_redis_client()
            await client.delete(
                f"memory:{self.session_id}:short_term",
                f"memory:{self.session_id}:long_term"
            )
        except Exception as e:
            logger.error(f"从 Redis 删除失败: {e}", exc_info=True)
    
    async def close(self) -> None:
        """关闭记忆引擎"""
        if self._redis_client:
            await self._redis_client.close()
            logger.info(f"记忆引擎已关闭: session_id={self.session_id}")
