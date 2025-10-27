"""
Memory Item - 记忆项数据结构
从 memory-networkx/organs/memory_item.py 改造
"""
from datetime import datetime
from typing import List


META_TAG_MARK = ":"
DATETIME_META = "DATETIME:"


class MemoryItem:
    """记忆项"""
    
    def __init__(self, summary: str, tags: List[str]):
        self._summary = summary
        self._tags = tags
        self._created_time = datetime.now()
        self._init_created_time()
        self._adjust_tags()
    
    def _init_created_time(self):
        """从标签中提取创建时间"""
        for tag in self._tags:
            if tag.startswith(DATETIME_META):
                time_str = tag.replace(DATETIME_META, "")
                try:
                    self._created_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    return
                except ValueError:
                    pass
        # 如果没有时间标签，使用当前时间
        self._created_time = datetime.now()
    
    def _adjust_tags(self):
        """调整标签，移除元标签"""
        self._tags = [tag for tag in self._tags if META_TAG_MARK not in tag or tag.startswith(DATETIME_META)]
    
    def tags(self) -> List[str]:
        """获取标签列表"""
        return [tag for tag in self._tags if not tag.startswith(DATETIME_META)]
    
    def summary(self) -> str:
        """获取摘要"""
        return self._summary
    
    def time(self) -> datetime:
        """获取创建时间"""
        return self._created_time
