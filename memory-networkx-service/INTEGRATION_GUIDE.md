# Memory Enhancement Service 集成指南

本指南将帮助您将 Memory Enhancement Service 与 Higress ai-history 插件集成。

## 系统架构

```
┌─────────────┐
│  AI Client  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Higress Gateway                  │
│  ┌───────────────────────────────────┐  │
│  │   ai-history Plugin (WASM Go)     │  │
│  │                                   │  │
│  │  1. 检索增强记忆 ────────┐       │  │
│  │  2. 注入上下文            │       │  │
│  │  3. 异步保存记忆 ────┐   │       │  │
│  └─────────────────────┼───┼───────┘  │
└────────────────────────┼───┼──────────┘
                         │   │
       ┌─────────────────┘   └─────────────────┐
       ▼                                       ▼
┌──────────────────────┐            ┌──────────────────┐
│ Memory Enhancement   │            │  Redis (对话历史) │
│ Service (Python)     │◄───────────┤                  │
│                      │            └──────────────────┘
│ - NetworkX 图谱      │
│ - 记忆检索算法       │
│ - 关键词提取         │
└──────────────────────┘
```

## 工作流程

### 请求流程

1. **用户请求** → Higress Gateway
2. **ai-history 插件** 拦截请求
3. **检索记忆**：调用 Memory Service `/api/v1/memory/retrieve`
4. **注入上下文**：将检索到的记忆插入到 `messages` 中
5. **转发请求** → LLM Provider
6. **返回响应** → 用户

### 响应流程

1. **LLM 响应** → Higress Gateway
2. **ai-history 插件** 拦截响应
3. **保存对话**：保存到 Redis（原有功能）
4. **异步增强**：调用 Memory Service `/api/v1/memory/enhance`
5. **更新图谱**：Memory Service 提取关键词、更新 NetworkX 图
6. **返回响应** → 用户

## 部署步骤

### 步骤 1：准备环境

确保您已安装：
- Kubernetes 集群
- Higress Gateway
- kubectl 命令行工具

### 步骤 2：构建 Memory Service 镜像

```bash
cd memory-networkx-service

# 构建 Docker 镜像
docker build -t your-registry/memory-enhancement-service:latest .

# 推送到镜像仓库
docker push your-registry/memory-enhancement-service:latest
```

### 步骤 3：部署 Memory Service

```bash
# 修改 deploy/complete-deployment.yaml 中的镜像地址
# 将 your-registry 替换为您的实际镜像仓库地址

# 部署所有组件
kubectl apply -f deploy/complete-deployment.yaml

# 检查部署状态
kubectl get pods -n higress-system
```

### 步骤 4：验证部署

```bash
# 查看 Memory Service 日志
kubectl logs -n higress-system -l app=memory-service --tail=50

# 检查服务健康状态
kubectl exec -it -n higress-system deployment/memory-enhancement-service -- \
  curl http://localhost:8080/health

# 预期输出: {"status":"healthy"}
```

### 步骤 5：配置 ai-history 插件

ai-history 插件已在原代码基础上扩展，支持 Memory Service 配置。

**重要**：需要重新编译 ai-history 插件：

```bash
cd plugins/wasm-go/extensions/ai-history

# 编译插件
GOOS=wasip1 GOARCH=wasm go build -o main.wasm .

# 构建 OCI 镜像
docker build -t your-registry/ai-history:1.0.0 -f Dockerfile .
docker push your-registry/ai-history:1.0.0
```

**Dockerfile 示例**（在 ai-history 目录下创建）：
```dockerfile
FROM scratch
COPY main.wasm plugin.wasm
```

### 步骤 6：应用插件配置

```bash
# 修改 deploy/ai-history-plugin-config.yaml 中的镜像地址
# 应用配置
kubectl apply -f deploy/ai-history-plugin-config.yaml

# 验证插件已加载
kubectl get wasmplugin -n higress-system ai-history
```

## 配置说明

### Memory Service 配置项

在 ai-history 插件配置中添加 `memoryService` 部分：

```yaml
memoryService:
  enabled: true                    # 是否启用记忆增强（默认：false）
  serviceName: memory-service....  # 服务地址（FQDN）
  servicePort: 8080                # 服务端口（默认：8080）
  timeout: 5000                    # 超时时间，毫秒（默认：5000）
  topK: 5                          # 检索记忆数量（默认：5）
```

### 环境变量配置

Memory Service 支持以下环境变量（在 ConfigMap 中配置）：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `REDIS_HOST` | Redis 主机地址 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `REDIS_PASSWORD` | Redis 密码（可选） | `""` |
| `REDIS_DB` | Redis 数据库编号 | `0` |
| `SHORT_TERM_MEMORY_SIZE` | 短期记忆大小（对话数） | `20` |
| `RETRIEVE_TOP_N` | 默认检索数量 | `5` |
| `SUMMARY_MAX_TAGS` | 每个记忆的最大标签数 | `30` |

## 测试验证

### 1. 手动测试 Memory Service

```bash
# 端口转发
kubectl port-forward -n higress-system svc/memory-service 8080:8080

# 测试健康检查
curl http://localhost:8080/health

# 测试添加记忆
curl -X POST http://localhost:8080/api/v1/memory/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "question": "什么是 NetworkX？",
    "answer": "NetworkX 是一个用于创建、操作和研究复杂网络的 Python 库。"
  }'

# 测试检索记忆
curl -X POST http://localhost:8080/api/v1/memory/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "query": "如何使用图数据库？",
    "top_k": 5
  }'

# 查看统计信息
curl http://localhost:8080/api/v1/memory/stats/test-session
```

### 2. 端到端测试

发送 AI 对话请求：

```bash
# 通过 Higress Gateway 发送请求
curl -X POST http://your-higress-gateway/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "介绍一下 NetworkX"}
    ]
  }'
```

检查日志验证集成：

```bash
# 查看 ai-history 插件日志（在 Higress 日志中）
kubectl logs -n higress-system -l app=higress-gateway --tail=100 | grep "ai-history"

# 应该看到类似日志：
# retrieved 3 enhanced memories
# memory enhanced successfully for session: xxx

# 查看 Memory Service 日志
kubectl logs -n higress-system -l app=memory-service --tail=100

# 应该看到：
# 收到增强记忆请求: session_id=xxx
# 收到检索请求: session_id=xxx, query=...
# 检索到 N 条相关记忆
```

## 故障排查

### Memory Service 无法启动

**症状**：Pod 处于 CrashLoopBackOff 状态

**排查步骤**：
```bash
# 查看详细日志
kubectl logs -n higress-system -l app=memory-service --tail=200

# 常见原因：
# 1. Redis 连接失败 - 检查 Redis 服务是否运行
kubectl get svc -n higress-system redis

# 2. 镜像拉取失败 - 检查镜像仓库凭证
kubectl describe pod -n higress-system -l app=memory-service
```

### 记忆检索没有结果

**可能原因**：
1. 对话数量不足，尚未转换为长期记忆
2. 查询关键词与记忆标签匹配度低

**解决方案**：
```bash
# 查看记忆统计
curl http://localhost:8080/api/v1/memory/stats/your-session-id

# 如果 total_memories 为 0，说明还没有长期记忆
# 需要积累更多对话（默认 20 条短期记忆才会转换）
```

### ai-history 插件未调用 Memory Service

**排查步骤**：
```bash
# 1. 检查插件配置
kubectl get wasmplugin -n higress-system ai-history -o yaml

# 确认 memoryService.enabled 为 true

# 2. 检查服务连通性
kubectl exec -it -n higress-system deployment/higress-gateway -- \
  curl -v http://memory-service.higress-system.svc.cluster.local:8080/health

# 3. 检查 Higress 日志
kubectl logs -n higress-system -l app=higress-gateway | grep -i "memory"
```

## 性能优化

### 1. 调整副本数

根据负载调整 Memory Service 副本数：

```bash
kubectl scale deployment memory-enhancement-service \
  -n higress-system --replicas=5
```

### 2. 资源限制

根据实际使用情况调整资源配置：

```yaml
resources:
  requests:
    memory: "512Mi"  # 增加内存
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### 3. Redis 优化

```bash
# 使用 Redis Cluster 提升性能
# 或使用 Redis 持久化避免数据丢失

# 添加 Redis 配置
kubectl create configmap redis-config \
  --from-literal=maxmemory=256mb \
  --from-literal=maxmemory-policy=allkeys-lru \
  -n higress-system
```

## 监控和告警

### Prometheus 指标

Memory Service 暴露以下指标（通过 FastAPI）：

```
# 请求计数
http_requests_total{method="POST",path="/api/v1/memory/enhance"}
http_requests_total{method="POST",path="/api/v1/memory/retrieve"}

# 响应时间
http_request_duration_seconds{method="POST",path="/api/v1/memory/enhance"}
```

### 日志级别调整

```yaml
# 在 ConfigMap 中修改
data:
  LOG_LEVEL: "DEBUG"  # 改为 DEBUG 获取更详细日志
```

## 最佳实践

1. **分离环境**：开发、测试、生产环境使用不同的 Redis 数据库编号
2. **备份策略**：定期备份 Redis 数据
3. **性能测试**：在生产环境前进行压力测试
4. **监控告警**：配置 Memory Service 和 Redis 的监控告警
5. **降级策略**：Memory Service 不可用时，ai-history 应能正常工作（仅使用 Redis 对话历史）

## 下一步

- 集成专业的中文分词工具（如 jieba）提升关键词提取质量
- 使用 LLM API 进行摘要生成
- 添加更多图算法（如社区发现、中心性分析）
- 实现记忆的主动推送机制
