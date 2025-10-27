# Memory Enhancement Service

基于 NetworkX 的 AI 对话记忆增强服务，用于与 Higress ai-history 插件集成。

## 功能特性

- **知识图谱构建**：使用 NetworkX 构建对话关键词的知识图谱
- **记忆扩散算法**：基于海马体特性的记忆检索算法
- **动态权重管理**：自动调整记忆权重和图结构
- **Redis 持久化**：支持将记忆数据持久化到 Redis
- **RESTful API**：提供简单的 HTTP API 接口

## 架构说明

```
AI Client → Higress Gateway → ai-history Plugin (WASM Go)
                                      ↓
                            Memory Enhancement Service (Python + NetworkX)
                                      ↓
                                   Redis
```

### 工作流程

1. **请求阶段**：ai-history 插件从 Memory Service 检索相关记忆并注入到请求中
2. **响应阶段**：ai-history 插件将新的对话异步发送到 Memory Service
3. **记忆处理**：Memory Service 提取关键词、更新知识图谱、存储记忆

## 快速开始

### 1. 本地开发

```bash
# 安装依赖
cd memory-networkx-service
pip install -r requirements.txt

# 启动服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 2. Docker 部署

```bash
# 构建镜像
docker build -t memory-enhancement-service:latest .

# 运行容器
docker run -d \
  -p 8080:8080 \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  --name memory-service \
  memory-enhancement-service:latest
```

### 3. Kubernetes 部署

```bash
# 部署服务
kubectl apply -f deploy/kubernetes.yaml

# 检查部署状态
kubectl get pods -n higress-system -l app=memory-service
kubectl logs -n higress-system -l app=memory-service
```

## API 接口

### 增强记忆

**POST** `/api/v1/memory/enhance`

添加对话到记忆系统。

**请求体：**
```json
{
  "session_id": "user-123",
  "question": "什么是 NetworkX？",
  "answer": "NetworkX 是一个用于创建、操作和研究复杂网络的 Python 库。"
}
```

**响应：**
```json
{
  "status": "success",
  "message": "Memory enhanced successfully",
  "session_id": "user-123"
}
```

### 检索记忆

**POST** `/api/v1/memory/retrieve`

检索相关记忆上下文。

**请求体：**
```json
{
  "session_id": "user-123",
  "query": "如何使用图数据库？",
  "top_k": 5
}
```

**响应：**
```json
{
  "status": "success",
  "context": [
    "讨论了 NetworkX 的基本用法...",
    "介绍了图数据结构的特点..."
  ],
  "metadata": {
    "query_tags": ["图数据库", "使用"],
    "expanded_tags": ["networkx", "数据结构", "算法"],
    "retrieved_count": 2,
    "scores": [0.85, 0.72]
  },
  "session_id": "user-123"
}
```

### 获取统计信息

**GET** `/api/v1/memory/stats/{session_id}`

获取指定会话的记忆统计信息。

**响应：**
```json
{
  "session_id": "user-123",
  "total_memories": 15,
  "graph_nodes": 120,
  "graph_edges": 450,
  "avg_degree": 7.5
}
```

### 删除记忆

**DELETE** `/api/v1/memory/{session_id}`

删除指定会话的所有记忆。

**响应：**
```json
{
  "status": "success",
  "message": "Memory for session user-123 deleted",
  "session_id": "user-123"
}
```

## ai-history 插件配置

在原有 ai-history 插件配置基础上，添加 Memory Service 配置：

```yaml
apiVersion: extensions.higress.io/v1alpha1
kind: WasmPlugin
metadata:
  name: ai-history
  namespace: higress-system
spec:
  defaultConfig:
    redis:
      serviceName: redis.higress-system.svc.cluster.local
      servicePort: 6379
      timeout: 2000
    # Memory Enhancement Service 配置
    memoryService:
      enabled: true  # 启用记忆增强功能
      serviceName: memory-service.higress-system.svc.cluster.local
      servicePort: 8080
      timeout: 5000  # 超时时间（毫秒）
      topK: 5        # 检索记忆数量
```

## 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `REDIS_HOST` | Redis 主机地址 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_PASSWORD` | Redis 密码 | ` ` |
| `REDIS_DB` | Redis 数据库编号 | `0` |
| `SERVICE_PORT` | 服务端口 | `8080` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `SHORT_TERM_MEMORY_SIZE` | 短期记忆大小 | `20` |
| `RETRIEVE_TOP_N` | 默认检索数量 | `5` |
| `SUMMARY_MAX_TAGS` | 最大标签数量 | `30` |

## 技术栈

- **FastAPI**：高性能 Web 框架
- **NetworkX**：图论和复杂网络分析库
- **Redis**：内存数据库，用于持久化
- **Pydantic**：数据验证和配置管理
- **Uvicorn**：ASGI 服务器

## 核心算法

### 记忆图谱构建

基于共现关系构建关键词的知识图谱：
- 使用 PMI（点互信息）计算边权重
- 动态调整噪声阈值过滤低权重边
- 限制每个节点的最大边数避免过拟合

### 记忆检索

基于海马体特性的记忆扩散算法：
1. 从查询关键词开始扩散
2. 根据边权重和路径深度动态衰减
3. 过滤低相关性节点
4. 返回得分最高的记忆

### 相关性计算

综合考虑：
- Jaccard 相似度（70%）
- 时间衰减因子（30%）

## 性能优化

- **异步处理**：Memory Service 调用不阻塞主请求流
- **缓存机制**：使用 LRU 缓存避免重复计算
- **批处理**：支持批量更新记忆
- **图剪枝**：定期清理低权重边和孤立节点

## 故障排查

### 查看日志

```bash
# Kubernetes
kubectl logs -n higress-system -l app=memory-service --tail=100 -f

# Docker
docker logs -f memory-service
```

### 常见问题

**Q: Memory Service 连接失败？**

A: 检查以下配置：
1. 服务名称是否正确（包括命名空间）
2. 端口是否匹配
3. 网络策略是否允许访问

**Q: 记忆检索没有结果？**

A: 可能原因：
1. 短期记忆还未转换为长期记忆（需要积累一定对话数量）
2. 查询关键词与记忆标签匹配度低
3. 图结构还未建立（刚启动服务）

**Q: 性能较慢？**

A: 优化建议：
1. 调整 `SHORT_TERM_MEMORY_SIZE` 减少转换频率
2. 降低 `RETRIEVE_TOP_N` 减少检索数量
3. 增加服务副本数（Kubernetes 中调整 replicas）

## 开发指南

### 项目结构

```
memory-networkx-service/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── memory_engine.py     # 记忆引擎核心
│   ├── memory_graph.py      # NetworkX 图结构
│   ├── memory_item.py       # 记忆项数据结构
│   └── text_processor.py    # 文本处理
├── deploy/
│   └── kubernetes.yaml      # K8s 部署配置
├── Dockerfile               # Docker 镜像
├── requirements.txt         # Python 依赖
└── README.md               # 本文档
```

### 扩展功能

可以通过替换 `TextProcessor` 类来集成 LLM API 或专业的中文分词工具（如 jieba）以提升关键词提取质量。

## License

本项目基于 memory-networkx 改造，遵循原项目的许可协议。

## 致谢

- 基于 [Higress](https://github.com/alibaba/higress) ai-history 插件
- 使用 [NetworkX](https://networkx.org/) 图论库
- 参考 Waifu 项目的记忆系统设计
