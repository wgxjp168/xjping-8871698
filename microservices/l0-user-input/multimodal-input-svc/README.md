# multimodal-input-svc — 多模态输入适配服务

## 概述

L0 用户输入层核心服务，接收终端用户的四种输入模态，统一解析为标准化 `ParsedInput` 对象后向 L1 API 网关传递。

| 属性 | 值 |
|------|-----|
| 服务名 | `multimodal-input-svc` |
| 端口 | **8000** |
| 层级 | L0 用户输入层 |
| Spring Boot | 3.2.3 |

## 业务能力

| 输入类型 | 处理逻辑 | 关键输出 |
|---------|---------|---------|
| **文本** | 正则+规则提取关键词、预算区间 | productKeyword, budgetMin/Max |
| **图片** | 调用 cv-recognition-svc 识别商品分类 | detectedLabels, productKeyword |
| **链接** | 解析7大电商平台URL，提取商品ID | platform, platformProductId, normalizedUrl |
| **语音** | 百度/讯飞语音转文本，再走文本解析 | transcribedText + 文本解析结果 |

### 支持的电商平台（链接解析）

| 平台 | 域名示例 | 提取字段 |
|------|---------|---------|
| 淘宝 | `item.taobao.com/item.htm?id=xxx` | item id |
| 天猫 | `detail.tmall.com/item.htm?id=xxx` | item id |
| 京东 | `item.jd.com/{skuId}.html` | sku id |
| 拼多多 | `mobile.yangkeduo.com/goods.html?goods_id=xxx` | goods id |
| 苏宁 | `product.suning.com/{catalog}/{product}.html` | catalog+product |
| 亚马逊中国 | `amazon.cn/dp/{ASIN}/` | ASIN |
| 小红书 | `xiaohongshu.com/explore/{noteId}` | note id |

## 核心接口

```
POST /api/v0/input/parse        - 单条解析（需JWT）
POST /api/v0/input/parse/batch  - 批量解析，最多10条（需JWT）
GET  /api/v0/input/health       - 健康检查（L1网关心跳）
GET  /actuator/health           - Kubernetes探针
GET  /swagger-ui.html           - Swagger API文档
```

## 与 L1 网关对接接口

| 方向 | 接口 | 说明 |
|------|------|------|
| L0→L1 下行 | `POST /api/v1/decision/start` | 将 ParsedInput 推送至 L1 启动决策 |
| L1→L0 上行 | `GET /api/v0/input/health` | L1 心跳探测 L0 健康状态 |

## 本地启动

### 前置依赖
- JDK 21+
- Maven 3.9+
- Redis（本地 6379 或 Docker）
- Nacos（本地 8848）

### 启动命令

```bash
# 1. 从项目根目录构建公共组件（首次）
cd /path/to/ilbuy-platform
mvn install -pl common/common-core,common/common-security,common/common-redis,common/common-openfeign -am -DskipTests

# 2. 启动服务（dev模式，语音/图像识别均为Mock）
cd microservices/l0-user-input/multimodal-input-svc
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 3. 验证启动
curl http://localhost:8000/actuator/health
```

### 快速测试（文本解析）

```bash
# 获取JWT Token（先通过auth-svc登录）
TOKEN="eyJhbGci..."

# 文本输入解析
curl -X POST http://localhost:8000/api/v0/input/parse \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputType":"text","textContent":"我想买一台5000元以内的游戏本"}'

# 链接输入解析
curl -X POST http://localhost:8000/api/v0/input/parse \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputType":"link","rawUrl":"https://item.jd.com/100012345678.html"}'
```

## 容器部署

```bash
# 构建镜像
docker build -t multimodal-input-svc:1.0.0 .

# 本地运行（dev模式，无需真实API Key）
docker run -d \
  -p 8000:8000 \
  -e SPRING_PROFILES_ACTIVE=dev \
  -e REDIS_HOST=host.docker.internal \
  -e NACOS_ADDR=host.docker.internal:8848 \
  -e IMAGE_MOCK_ENABLED=true \
  --name multimodal-input-svc \
  multimodal-input-svc:1.0.0
```

## K8s 部署

```bash
# 创建命名空间（首次）
kubectl create namespace ilbuy-prod

# 部署 ConfigMap 和 Secret（参考 k8s/ 目录模板）
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 查看状态
kubectl -n ilbuy-prod get pods -l app=multimodal-input-svc
kubectl -n ilbuy-prod logs -f deploy/multimodal-input-svc
```

## 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `JWT_SECRET` | ✅ Prod | `ilbuy-jwt-secret...` | JWT签名密钥 |
| `REDIS_HOST` | ✅ Prod | `redis-cluster` | Redis地址 |
| `REDIS_PASSWORD` | ✅ Prod | - | Redis密码 |
| `NACOS_ADDR` | ✅ Prod | `nacos:8848` | Nacos地址 |
| `BAIDU_VOICE_ENABLED` | 语音功能必填 | `false` | 启用百度语音 |
| `BAIDU_VOICE_API_KEY` | 语音功能必填 | - | 百度语音API Key |
| `BAIDU_VOICE_SECRET_KEY` | 语音功能必填 | - | 百度语音Secret |
| `IMAGE_MOCK_ENABLED` | - | `true` | 关闭后调用cv-recognition-svc |
| `CV_SERVICE_URL` | Prod图像识别 | `http://cv-recognition-svc:9300` | 图像识别服务地址 |

## 运行单元测试

```bash
mvn test
```
