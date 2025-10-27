"""
Memory Graph - 基于 NetworkX 的知识图谱
从 memory-networkx/organs/memory_graph.py 改造
"""
import networkx as nx
import heapq
from itertools import combinations
import math
import logging
from typing import Set, List
from app.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class MemoryGraph:
    """记忆知识图谱"""
    
    def __init__(self):
        # 使用 NetworkX 图表示记忆连接
        self._graph = nx.Graph()
        self._base_decay = 0.6
        self._noise_threshold = 0.2
        self._max_edges_per_node = 30
        self._need_update_noise = True
        self._add_cnt = 0
        self._add_cnt_limit = 1000
    
    def add_memory(self, memory: MemoryItem):
        """添加记忆到图中"""
        tags = set(memory.tags())
        
        # 添加节点（关键词）
        current_node = self._graph.number_of_nodes()
        self._graph.add_nodes_from(tags)
        after_node = self._graph.number_of_nodes()
        
        # 更新所有标签对之间的边
        self._update_edges(tags)
        
        # 每一千个节点，进行一次裁剪
        self._add_cnt += after_node - current_node
        if self._add_cnt >= self._add_cnt_limit:
            self._prune_graph()
            self._add_cnt = 0
    
    def get_node_count(self) -> int:
        """获取节点数量"""
        return self._graph.number_of_nodes()
    
    def get_edge_count(self) -> int:
        """获取边数量"""
        return self._graph.number_of_edges()
    
    def get_avg_degree(self) -> float:
        """计算图的平均度数"""
        if self._graph.number_of_nodes() == 0:
            return 0.0
        return sum(dict(self._graph.degree()).values()) / self._graph.number_of_nodes()
    
    def _update_edges(self, keywords: Set[str]):
        """更新图的边权重"""
        edges_to_update = []
        
        # 统计共现次数
        for i, j in combinations(keywords, 2):
            if self._graph.has_edge(i, j):
                self._graph[i][j]['cooccurrence'] += 1
            else:
                self._graph.add_edge(i, j, cooccurrence=1)
            edges_to_update.append((i, j))
        
        # 改进的 PMI 权重计算
        total_edges = max(1, self._graph.number_of_edges())
        for i, j in edges_to_update:
            degree_i = max(1, self._graph.degree[i])
            degree_j = max(1, self._graph.degree[j])
            cooccurrence = self._graph[i][j]['cooccurrence']
            
            # PMI 计算
            pmi = math.log2((cooccurrence * total_edges) / (degree_i * degree_j))
            
            # 平滑和归一化
            smoothing = 0.2
            norm_factor = math.log2(total_edges) + smoothing
            
            # 综合权重
            freq_factor = math.log2(1 + cooccurrence) / math.log2(total_edges)
            pmi_factor = (pmi + smoothing) / norm_factor
            
            alpha = 0.7
            weight = alpha * pmi_factor + (1 - alpha) * freq_factor
            weight = max(0.01, min(1.0, weight))
            
            self._graph[i][j]['weight'] = weight
        
        self._need_update_noise = True
    
    def _prune_graph(self):
        """定期清理低权重边"""
        self._update_noise_threshold()
        
        # 移除低权重边
        for u, v, data in list(self._graph.edges(data=True)):
            if data['weight'] < self._noise_threshold:
                self._graph.remove_edge(u, v)
        
        # 限制节点边数
        self._limit_node_edges()
        
        # 移除孤立节点
        isolated_nodes = [node for node, degree in self._graph.degree() if degree == 0]
        self._graph.remove_nodes_from(isolated_nodes)
        
        self._need_update_noise = True
        
        logger.info(f"图裁剪完成: 节点={self._graph.number_of_nodes()}, "
                   f"边={self._graph.number_of_edges()}, "
                   f"平均度数={self.get_avg_degree():.2f}")
    
    def _update_noise_threshold(self):
        """动态调整噪声阈值"""
        if not self._need_update_noise:
            return
        
        self._need_update_noise = False
        
        if self._graph.number_of_edges() == 0:
            self._noise_threshold = 0.2
            return
        
        # 使用分位数计算阈值
        weights = [data['weight'] for _, _, data in self._graph.edges(data=True)]
        if weights:
            import numpy as np
            lower_quartile = np.percentile(weights, 25)
            avg_degree = self.get_avg_degree()
            max_threshold = 0.4 + 0.1 * math.log2(avg_degree) if avg_degree > 0 else 0.4
            self._noise_threshold = max(0.1, min(max_threshold, lower_quartile))
    
    def _limit_node_edges(self):
        """限制每个节点的最大边数"""
        for node in self._graph.nodes():
            edges = list(self._graph.edges(node, data=True))
            if len(edges) > self._max_edges_per_node:
                edges = sorted(edges, key=lambda x: -x[2]['weight'])
                for edge in edges[self._max_edges_per_node:]:
                    self._graph.remove_edge(edge[0], edge[1])
    
    def get_related_keywords(self, keywords: Set[str]) -> List[str]:
        """
        基于海马体特性的记忆扩散算法
        
        Args:
            keywords: 输入关键词集合
            
        Returns:
            扩散得到的相关关键词列表
        """
        valid_keywords = {k for k in keywords if self._graph.has_node(k)}
        if not valid_keywords:
            logger.info("无效关键词，无法联想")
            return []
        
        self._update_noise_threshold()
        
        # 初始化优先队列
        need_search = []
        for k in valid_keywords:
            heapq.heappush(need_search, (-1.0, k, 0, k))
        
        related: dict[str, float] = {}
        max_strength = {}
        
        while len(need_search) > 0:
            neg_strength, curr, depth, from_node = heapq.heappop(need_search)
            curr_strength = -neg_strength
            
            if curr_strength <= self._noise_threshold:
                break
            
            if curr_strength <= max_strength.get(curr, 0):
                continue
            
            max_strength[curr] = curr_strength
            related[curr] = curr_strength
            
            # 获取邻居节点
            neighbors = self._get_valid_neighbors(curr)
            if not neighbors:
                continue
            
            # 计算平均权重
            avg_weight = sum(self._get_edge_weight(curr, n) for n in neighbors) / len(neighbors)
            
            for neighbor in neighbors:
                edge_weight = self._get_edge_weight(curr, neighbor)
                
                # 动态衰减
                weight_ratio = edge_weight / max(0.01, avg_weight)
                dynamic_decay = self._base_decay + 0.2 * min(1.0, weight_ratio)
                dynamic_decay = min(dynamic_decay, 0.8)
                
                decay_rate = dynamic_decay ** depth
                new_strength = curr_strength * decay_rate * edge_weight
                
                if new_strength > 0:
                    heapq.heappush(need_search, (-new_strength, neighbor, depth + 1, curr))
        
        # 归一化并排序
        if related:
            max_value = max(related.values())
            normalized = {k: v / max_value for k, v in related.items()}
            sorted_related = sorted(normalized.items(), key=lambda x: -x[1])
            
            # 排除输入标签并返回
            return [k for k, v in sorted_related if k not in valid_keywords]
        
        return []
    
    def _get_valid_neighbors(self, keyword: str) -> List[str]:
        """获取有效邻居节点"""
        if not self._graph.has_node(keyword):
            return []
        
        edges = self._graph.edges(keyword, data=True)
        sorted_edges = sorted(edges, key=lambda x: -x[2]['weight'])[:self._max_edges_per_node]
        sorted_edges = [edge for edge in sorted_edges if edge[2]['weight'] > self._noise_threshold]
        
        return [edge[1] for edge in sorted_edges]
    
    def _get_edge_weight(self, key1: str, key2: str) -> float:
        """获取边的权重"""
        if self._graph.has_edge(key1, key2):
            return self._graph[key1][key2]['weight']
        return 0.0
    
    def clear(self):
        """清除图中的所有数据"""
        self._graph.clear()
        logger.info("知识图谱已清空")
