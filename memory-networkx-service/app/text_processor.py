"""
Text Processor - 文本处理器
用于生成摘要和提取关键词
"""
import logging
from typing import List
import re

logger = logging.getLogger(__name__)


class TextProcessor:
    """文本处理器 - 简化版本，可根据需要集成 LLM"""
    
    def __init__(self):
        # 停用词列表（中文常见停用词）
        self.stop_words = {
            '的', '了', '在', '是', '我', '你', '他', '她', '它',
            '们', '这', '那', '有', '个', '就', '都', '也', '还',
            '要', '会', '着', '过', '吗', '吧', '呢', '啊', '哦'
        }
    
    async def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        生成文本摘要
        
        简化实现：提取前 max_length 个字符
        生产环境可替换为调用 LLM API
        """
        # 清理文本
        cleaned_text = text.strip()
        
        # 如果文本较短，直接返回
        if len(cleaned_text) <= max_length:
            return cleaned_text
        
        # 截断到指定长度
        summary = cleaned_text[:max_length]
        
        # 在句号处截断
        last_period = summary.rfind('。')
        if last_period > max_length // 2:
            summary = summary[:last_period + 1]
        
        logger.debug(f"生成摘要: {len(summary)} 字符")
        return summary
    
    async def extract_tags(self, text: str, max_tags: int = 30) -> List[str]:
        """
        提取关键词标签
        
        简化实现：基于分词和词频
        生产环境可替换为调用 LLM API 或使用 jieba 分词
        """
        # 简单的中文分词（按标点和空格分割）
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text)
        
        # 过滤停用词和短词
        filtered_words = [
            word for word in words
            if len(word) >= 2 and word not in self.stop_words
        ]
        
        # 统计词频
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按词频排序
        sorted_words = sorted(word_freq.items(), key=lambda x: -x[1])
        
        # 取前 max_tags 个
        tags = [word for word, freq in sorted_words[:max_tags]]
        
        logger.debug(f"提取标签: {len(tags)} 个")
        return tags
