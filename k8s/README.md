# 昆仑创作引擎 — Kubernetes 部署指南

## 前置条件

- Kubernetes 集群 (v1.25+)
- kubectl 已配置并连接到集群
- 已构建 Docker 镜像 `kunlun-engine:latest`

## 快速部署

```bash
# 1. 创建命名空间
kubectl create namespace kunlun

# 2. 编辑密钥模板，填入真实 API 密钥
#    将 <PLACEHOLDER> 替换为实际值
vim k8s/secret.yaml

# 3. 按顺序应用所有资源
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 4. 检查部署状态
kubectl -n kunlun get pods
kubectl -n kunlun get svc

# 5. 查看日志
kubectl -n kunlun logs -f deployment/kunlun-deployment
```

## 外部访问

默认启用 ClusterIP（仅集群内访问）。如需外部访问，编辑 `service.yaml`，取消 LoadBalancer 部分的注释：

```bash
kubectl apply -f k8s/service.yaml
kubectl -n kunlun get svc kunlun-service-lb
# 等待 EXTERNAL-IP 分配后即可通过该 IP 访问
```

## 资源清单

| 文件 | 用途 |
|------|------|
| `deployment.yaml` | 单副本 deployment + PVC，含 liveness/readiness probe |
| `service.yaml` | ClusterIP + LoadBalancer 双模式（LoadBalancer 默认注释） |
| `configmap.yaml` | 非敏感配置（阈值、Host、端口等） |
| `secret.yaml` | 模板文件，含 API 密钥占位符，部署前必须替换 |

## 依赖服务

应用依赖以下外部服务，需在集群内或集群外单独部署：

| 服务 | 用途 | K8s 内地址示例 |
|------|------|---------------|
| Neo4j 5.x | 图数据库（可选，有 SQLite 降级） | `neo4j-service:7687` |
| Qdrant | 向量检索 | 本地文件模式（无外部依赖） |
| Redis 7.x | 缓存 | `redis-service:6379` |
| NATS 2.x | 消息队列 | `nats-service:4222` |

> 上述服务可使用 `docker-compose.yml` 在集群外独立运行，或通过 Helm chart 部署到集群内。

## 健康检查

```bash
# 端口转发到本地测试
kubectl -n kunlun port-forward svc/kunlun-service 8000:8000

# 检查健康状态
curl http://localhost:8000/api/v1/status
```
