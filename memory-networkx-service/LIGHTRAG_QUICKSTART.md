# LightRAG 集成快速入门指南

本指南帮助您快速启动集成了 LightRAG 的 Memory Enhancement Service。

## 🎯 30分钟快速部署

### 步骤 1：环境准备（5分钟）

```bash
# 1. 确保已安装 Python 3.11+
python --version

# 2. 创建虚拟环境
cd memory-networkx-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements-lightrag.txt
```

### 步骤 2：配置 OpenAI API（5分钟）

```bash
# 复制环境变量配置
cp deploy/env-lightrag.example .env

# 编辑 .env 文件，填入您的 OpenAI API Key
# 最少需要配置：
# OPENAI_API_KEY=sk-your-api-key
# USE_LIGHTRAG=true
```

**重要**：如果没有 OpenAI API Key，可以：
- 使用兼容的 API（如 DeepSeek、Qwen 等）
- 设置 `USE_LIGHTRAG=false` 仅使用 NetworkX 模式

### 步骤 3：本地启动服务（5分钟）

```bash
# 启动服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 看到以下输出表示成功：
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8080
```

### 步骤 4：测试 LightRAG 集成（10分钟）

#### 4.1 健康检查

```bash
curl http://localhost:8080/health
# 预期输出：{"status":"healthy"}
```

#### 4.2 添加知识

```bash
# 第一条对话
curl -X POST http://localhost:8080/api/v1/memory/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-lightrag",
    "question": "什么是 LightRAG？",
    "answer": "LightRAG 是一个轻量级的 RAG 框架，它使用双层检索架构，结合了实体级别和主题级别的检索，能够实现更准确的知识检索和图增强生成。"
  }'

# 第二条对话（继续积累）
curl -X POST http://localhost:8080/api/v1/memory/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-lightrag",
    "question": "LightRAG 的优势是什么？",
    "answer": "LightRAG 的主要优势包括：1. 双层检索架构提供更精确的检索；2. 图增强生成支持多跳推理；3. 增量更新适合对话场景；4. 高性能的向量检索和图算法。"
  }'

# 继续添加直到触发长期记忆转换（默认需要 20 条对话）
# 或者修改 SHORT_TERM_MEMORY_SIZE=4 加快测试
```

#### 4.3 检索知识

```bash
# 语义检索测试
curl -X POST http://localhost:8080/api/v1/memory/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-lightrag",
    "query": "介绍一下 RAG 框架的特点",
    "top_k": 3
  }'

# 预期输出（使用 LightRAG）：
# {
#   "status": "success",
#   "context": [
#     "...关于 LightRAG 的相关内容...",
#     "...双层检索架构...",
#     "...图增强生成..."
#   ],
#   "metadata": {
#     "method": "lightrag_hybrid",
#     "retrieved_count": 3
#   }
# }
```

#### 4.4 查看统计信息

```bash
curl http://localhost:8080/api/v1/memory/stats/test-lightrag

# 预期输出：
# {
#   "session_id": "test-lightrag",
#   "total_memories": 2,
#   "graph_nodes": 15,
#   "graph_edges": 30,
#   "avg_degree": 4.0,
#   "use_lightrag": true,
#   "lightrag_enabled": true
# }
```

### 步骤 5：验证 LightRAG 数据（5分钟）

```bash
# 查看 LightRAG 生成的数据
ls -lh lightrag_data/test-lightrag/

# 应该看到：
# - vdb/ (向量数据库)
# - graph_chunk_entity_relation.graphml (知识图谱)
# - full_docs.json (原始文档)
# - text_chunks.json (文本块)
# - entities.json (实体)
# - relationships.json (关系)
```

## 🐳 Docker 部署（生产环境）

### 快速启动

```bash
# 1. 构建镜像
docker build -t memory-service-lightrag:latest \
  -f Dockerfile .

# 2. 运行容器
docker run -d \
  --name memory-service \
  -p 8080:8080 \
  -e OPENAI_API_KEY=sk-your-key \
  -e USE_LIGHTRAG=true \
  -v $(pwd)/lightrag_data:/app/lightrag_data \
  memory-service-lightrag:latest

# 3. 查看日志
docker logs -f memory-service

# 4. 测试
curl http://localhost:8080/health
```

## ☸️ Kubernetes 部署

```bash
# 1. 创建 Secret（OpenAI API Key）
kubectl create secret generic openai-secret \
  --from-literal=api-key=sk-your-key \
  -n higress-system

# 2. 部署服务
kubectl apply -f deploy/kubernetes-lightrag.yaml

# 3. 检查状态
kubectl get pods -n higress-system -l app=memory-service
kubectl logs -n higress-system -l app=memory-service --tail=50

# 4. 端口转发测试
kubectl port-forward -n higress-system svc/memory-service 8080:8080

# 5. 测试
curl http://localhost:8080/health
```

## 🔧 配置选项

### 基础配置（最小化）

```bash
# .env
OPENAI_API_KEY=sk-your-key
USE_LIGHTRAG=true
```

### 推荐配置（生产环境）

```bash
# .env
# OpenAI 配置
OPENAI_API_KEY=sk-your-key
OPENAI_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini           # 性价比高
EMBEDDING_MODEL=text-embedding-3-small

# LightRAG 配置
USE_LIGHTRAG=true
LIGHTRAG_WORKING_DIR=/data/lightrag
ENABLE_LLM_CACHE=true

# 记忆配置
SHORT_TERM_MEMORY_SIZE=20       # 20条对话转长期记忆
RETRIEVE_TOP_N=5

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
```

### 高性能配置

```bash
# 使用更强大的模型
LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-large

# 调整并发
MAX_ASYNC_REQUESTS=8

# 启用向量数据库（Qdrant）
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

## 📊 验证 LightRAG 效果

### 对比测试

```python
# test_comparison.py
import asyncio
import requests

async def test_comparison():
    # 1. 先禁用 LightRAG 测试
    response = requests.post(
        "http://localhost:8080/api/v1/memory/retrieve",
        json={
            "session_id": "test-session",
            "query": "如何实现图增强检索？",
            "top_k": 3
        }
    )
    networkx_result = response.json()
    print("NetworkX 结果:", networkx_result["metadata"])
    
    # 2. 启用 LightRAG 测试
    # 在 .env 中设置 USE_LIGHTRAG=true 并重启服务
    response = requests.post(
        "http://localhost:8080/api/v1/memory/retrieve",
        json={
            "session_id": "test-session",
            "query": "如何实现图增强检索？",
            "top_k": 3
        }
    )
    lightrag_result = response.json()
    print("LightRAG 结果:", lightrag_result["metadata"])

asyncio.run(test_comparison())
```

### 查看 LightRAG 生成的知识图谱

```python
# view_graph.py
import json
import networkx as nx
import matplotlib.pyplot as plt

# 读取 LightRAG 生成的图谱
G = nx.read_graphml("lightrag_data/test-session/graph_chunk_entity_relation.graphml")

# 打印统计
print(f"节点数: {G.number_of_nodes()}")
print(f"边数: {G.number_of_edges()}")

# 可视化（小图）
if G.number_of_nodes() < 100:
    plt.figure(figsize=(12, 8))
    nx.draw(G, with_labels=True, node_color='lightblue', 
            node_size=500, font_size=8, arrows=True)
    plt.savefig("knowledge_graph.png")
    print("图谱已保存到 knowledge_graph.png")
```

## 🚨 常见问题

### Q1: LightRAG 初始化失败

**错误**：`LightRAG initialization failed`

**解决**：
```bash
# 检查 API Key
echo $OPENAI_API_KEY

# 测试 API 连接
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'
```

### Q2: 记忆检索没有结果

**原因**：短期记忆还未转换为长期记忆

**解决**：
```bash
# 方法1：降低转换阈值
export SHORT_TERM_MEMORY_SIZE=4

# 方法2：添加更多对话直到达到阈值（默认20条）
```

### Q3: 成本过高

**解决**：
```bash
# 使用更便宜的模型
export LLM_MODEL=gpt-4o-mini           # OpenAI 最便宜
# 或
export OPENAI_API_BASE=https://api.deepseek.com
export LLM_MODEL=deepseek-chat         # 更便宜

# 启用缓存减少重复调用
export ENABLE_LLM_CACHE=true
```

### Q4: 想回退到 NetworkX 模式

```bash
# 设置环境变量
export USE_LIGHTRAG=false

# 重启服务
# 系统会自动使用 NetworkX 进行检索
```

## 📈 性能基准

基于 gpt-4o-mini 模型的性能参考：

| 操作 | 延迟 | 成本（每次） | 说明 |
|------|------|-------------|------|
| 添加对话 | 50-100ms | $0 | 仅保存到短期记忆 |
| 转换长期记忆 | 2-5s | $0.001-0.003 | 提取实体+生成向量 |
| 语义检索 | 100-300ms | $0 | 纯向量检索 |
| 混合检索 | 200-500ms | $0.0005 | 向量+LLM生成 |

**优化建议**：
- 批量转换：将多条对话合并后一次性转换
- 缓存开启：减少重复的 LLM 调用
- 向量数据库：使用专业向量数据库提升检索速度

## 🎯 下一步

1. **集成到 ai-history 插件**
   - 参考 [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
   - 配置 ai-history 插件调用 Memory Service

2. **性能调优**
   - 阅读 [LIGHTRAG_INTEGRATION.md](./LIGHTRAG_INTEGRATION.md) 的性能优化章节
   - 根据负载调整资源配置

3. **生产部署**
   - 配置持久化存储（PV/PVC）
   - 设置监控和告警
   - 实施备份策略

4. **进阶功能**
   - 使用 Neo4j 作为图数据库
   - 集成 Qdrant 作为向量数据库
   - 添加自定义实体提取规则

## 📚 相关文档

- [完整集成方案](./LIGHTRAG_INTEGRATION.md)
- [集成指南](./INTEGRATION_GUIDE.md)
- [基础 README](./README.md)
- [LightRAG 官方文档](https://github.com/HKUDS/LightRAG)

---

**提示**：如果您在部署过程中遇到问题，请查看日志：
```bash
# Docker
docker logs -f memory-service

# Kubernetes
kubectl logs -f -n higress-system -l app=memory-service

# 本地
# 日志会输出到终端
```
