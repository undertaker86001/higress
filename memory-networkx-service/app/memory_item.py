"""
Memory Item - 记忆项数据结构
从 memory-networkx/organs/memory_item.py 改造

核心功能：
1. 存储记忆摘要和标签
2. 从标签中提取时间信息
3. 过滤元标签（包含冒号的特殊标签）
4. 提供标准接口访问记忆数据
"""
from datetime import datetime
from typing import List


# 元标签标记（包含冒号的标签被视为元标签）
META_TAG_MARK = ":"
# 时间元标签前缀
DATETIME_META = "DATETIME:"
# 备用时间戳（当没有时间标签时使用）
BACKOFF_TIMESTAMP = 1745069038  # 2025-04-19 00:00:00 (UTC+8)


class MemoryItem:
    """
    记忆项 - 存储单条长期记忆
    
    Attributes:
        _summary: 记忆摘要文本
        _tags: 标签列表（包含元标签）
        _created_time: 记忆创建时间
    
    元标签类型：
        - DATETIME:2024-01-15 10:30:00  # 时间标签
        - PRIORITY:high                  # 优先级标签
        - PADDING:0                      # 填充标签
    """
    
    def __init__(self, summary: str, tags: List[str]):
        """
        初始化记忆项
        
        Args:
            summary: 记忆摘要
            tags: 标签列表（可包含元标签）
        """
        self._summary = summary
        self._tags = tags
        self._created_time = datetime.now()
        
        # 从标签中提取时间
        self._init_created_time()
        # 调整标签（移除非时间的元标签）
        self._adjust_tags()
    
    def _init_created_time(self) -> None:
        """
        从标签中提取创建时间
        
        查找 DATETIME: 开头的标签，解析其时间信息
        如果没有找到，使用备用时间戳
        """
        for tag in self._tags:
            if tag.startswith(DATETIME_META):
                time_str = tag.replace(DATETIME_META, "")
                try:
                    self._created_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    return
                except ValueError:
                    # 时间格式错误，继续查找
                    continue
        
        # 如果没有找到有效的时间标签，使用备用时间戳
        self._created_time = datetime.fromtimestamp(BACKOFF_TIMESTAMP)
    
    def _adjust_tags(self) -> None:
        """
        调整标签列表，移除非时间的元标签
        
        规则：
        - 移除所有包含冒号的标签（元标签）
        - 但保留 DATETIME: 时间标签（用于时间提取）
        
        注意：这个方法只在内部使用，tags() 方法会进一步过滤
        """
        # 只保留：不包含冒号的标签 或 DATETIME 时间标签
        self._tags = [
            tag for tag in self._tags 
            if META_TAG_MARK not in tag or tag.startswith(DATETIME_META)
        ]
    
    def tags(self) -> List[str]:
        """
        获取标签列表（不包含任何元标签）
        
        Returns:
            过滤后的标签列表（不包含 DATETIME 等元标签）
        """
        # 过滤掉所有元标签（包含冒号的标签）
        return [
            tag for tag in self._tags 
            if META_TAG_MARK not in tag
        ]
    
    def all_tags(self) -> List[str]:
        """
        获取所有标签（包含元标签）
        
        Returns:
            完整的标签列表（包含 DATETIME 等元标签）
        """
        return self._tags.copy()
    
    def summary(self) -> str:
        """
        获取记忆摘要
        
        Returns:
            摘要文本
        """
        return self._summary
    
    def time(self) -> datetime:
        """
        获取记忆创建时间
        
        Returns:
            创建时间（datetime 对象）
        """
        return self._created_time
    
    def __repr__(self) -> str:
        """
        字符串表示（用于调试）
        
        Returns:
            记忆项的字符串表示
        """
        return f"MemoryItem(summary='{self._summary[:50]}...', tags={len(self._tags)}, time={self._created_time.strftime('%Y-%m-%d %H:%M:%S')})"
    
    def to_dict(self) -> dict:
        """
        转换为字典（用于序列化）
        
        Returns:
            包含记忆数据的字典
        """
        return {
            "summary": self._summary,
            "tags": self.all_tags(),
            "created_time": self._created_time.isoformat(),
            "tags_count": len(self.tags()),
        }
