# xjping-8871698
我的梦想刚刚开始

## 查看 Docker 日志

使用以下命令查看 `ilbuy-microservices-config-server` 容器的日志（带时间戳）：

```bash
docker logs -t ilbuy-microservices-config-server
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `docker logs` | 获取容器的日志输出 |
| `-t` | 显示每条日志的时间戳 |
| `ilbuy-microservices-config-server` | 容器名称 |

### 常用扩展用法

```bash
# 查看日志并显示时间戳（实时跟踪）
docker logs -t -f ilbuy-microservices-config-server

# 查看最近 100 行日志（带时间戳）
docker logs -t --tail 100 ilbuy-microservices-config-server

# 查看指定时间之后的日志
docker logs -t --since 2024-01-01T00:00:00 ilbuy-microservices-config-server
```

> **注意**：`ilbuy-microservices-config-server:latest` 是镜像名称，查看运行中容器的日志需使用容器名称或容器 ID，而非镜像名称。
