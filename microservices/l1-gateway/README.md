# L1 接入网关层（ILbuy Platform）

## 服务清单

| 服务 | 端口 | 技术栈 | 说明 |
|------|------|--------|------|
| api-gateway | **80** | Spring Cloud Gateway 4.x (Reactive WebFlux) | 统一入口：路由/JWT鉴权/限流/熔断 |
| auth-svc | **8001** | Spring Boot 3.2 + Spring Security + MyBatis-Plus | JWT签发/刷新/吊销/Token自省 |
| websocket-svc | **8002** | Spring Boot 3.2 + WebSocket | WebSocket长连接/实时对话/L2对接预留 |

## 数据流转图

```
L0 用户输入（TEXT/VOICE/IMAGE/LINK）
    │
    ▼
api-gateway (port 80)
    ├── JWT鉴权（JwtAuthGlobalFilter, order=-200）
    ├── 请求日志（RequestLoggingFilter, order=-300）
    ├── B端限流 1000req/min/IP（RateLimitGlobalFilter, order=-100）
    ├── C端限流 100req/min/用户
    │
    ├── /auth/**  ────────────────→ auth-svc (8001)
    │                               ├── POST /auth/login
    │                               ├── POST /auth/refresh
    │                               ├── POST /auth/logout
    │                               └── POST /auth/introspect
    │
    ├── /ws/**   ────────────────→ websocket-svc (8002)
    │                               └── /ws/chat (JWT握手鉴权)
    │
    ├── /api/v1/input/** ──────→ multimodal-input-svc (L0, 8010)
    ├── /api/v1/profile/** ─────→ user-profile-svc (L0, 8011)
    ├── /api/v1/user/** ────────→ user-svc (L5, 8051)
    └── /api/v1/chat/** ────────→ conversation-svc (L2, 8021) [预留]
```

## 目录结构

```
microservices/l1-gateway/
├── pom.xml                     # L1层父POM
├── api-gateway/                # API网关服务（port 80）
│   ├── src/main/java/com/ilbuy/gateway/
│   │   ├── ApiGatewayApplication.java
│   │   ├── config/
│   │   │   ├── GatewayRouteConfig.java   # 路由配置（Java DSL）
│   │   │   ├── JwtProperties.java
│   │   │   └── RateLimitProperties.java
│   │   ├── filter/
│   │   │   ├── JwtAuthGlobalFilter.java  # JWT鉴权（order=-200）
│   │   │   ├── RateLimitGlobalFilter.java # 限流（order=-100）
│   │   │   └── RequestLoggingFilter.java  # 审计日志（order=-300）
│   │   └── handler/
│   │       └── FallbackController.java   # 熔断降级响应
│   ├── src/main/resources/
│   │   ├── application.yml / application-dev.yml / application-prod.yml
│   ├── src/test/...
│   └── Dockerfile
├── auth-svc/                   # 认证授权服务（port 8001）
│   ├── src/main/java/com/ilbuy/auth/
│   │   ├── api/AuthController.java
│   │   ├── service/AuthService.java + impl/
│   │   ├── entity/UserCredential.java
│   │   ├── mapper/UserCredentialMapper.java
│   │   ├── dto/LoginRequest/Response/TokenRefreshRequest/TokenIntrospectResponse
│   │   ├── util/JwtUtils.java
│   │   └── config/JwtProperties.java + SecurityConfig.java
│   ├── src/main/resources/
│   │   ├── application*.yml
│   │   └── db/migration/V1__create_user_credential.sql
│   ├── src/test/...
│   └── Dockerfile
├── websocket-svc/              # WebSocket服务（port 8002）
│   ├── src/main/java/com/ilbuy/websocket/
│   │   ├── config/WebSocketConfig.java + SecurityConfig.java + JwtProperties.java
│   │   ├── handler/ChatWebSocketHandler.java + ChatHandshakeInterceptor.java
│   │   ├── service/SessionManagerService.java + L2ConversationService.java
│   │   ├── service/impl/SessionManagerServiceImpl.java + L2ConversationServiceStub.java
│   │   ├── api/WebSocketStatusController.java
│   │   └── dto/ChatMessage.java + SessionInfo.java
│   ├── src/main/resources/application*.yml
│   ├── src/test/...
│   └── Dockerfile
└── k8s/
    ├── namespace.yaml
    ├── secret.yaml
    ├── api-gateway/  (deployment.yaml / service.yaml / hpa.yaml)
    ├── auth-svc/     (deployment.yaml / service.yaml / hpa.yaml)
    └── websocket-svc/(deployment.yaml / service.yaml / hpa.yaml)
```

## 本地启动

### 前置条件

```bash
# 启动依赖服务
docker run -d --name nacos -p 8848:8848 -e MODE=standalone nacos/nacos-server:v2.3.0
docker run -d --name redis -p 6379:6379 redis:7-alpine
docker run -d --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root mysql:8.3
```

### 初始化数据库

```bash
mysql -h localhost -u root -proot < microservices/l1-gateway/auth-svc/src/main/resources/db/migration/V1__create_user_credential.sql
```

### 启动顺序

```bash
# 1. auth-svc（先启动，gateway依赖其路由）
cd microservices/l1-gateway/auth-svc
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 2. websocket-svc
cd microservices/l1-gateway/websocket-svc
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 3. api-gateway（最后启动）
cd microservices/l1-gateway/api-gateway
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

### 功能验证

```bash
# 1. 登录获取 Token
curl -X POST http://localhost:8001/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"loginId":"consumer@ilbuy.com","password":"Test@123456"}'

# 2. 通过网关访问（使用返回的 accessToken）
curl http://localhost/api/v1/user/profile \
  -H 'Authorization: Bearer <accessToken>'

# 3. WebSocket 连接测试（wscat 工具）
wscat -c "ws://localhost:8002/ws/chat?token=<accessToken>"
# 发送: {"type":"PING"}
# 发送: {"type":"TEXT","sessionId":"test-001","content":"帮我推荐一款笔记本电脑"}

# 4. 验证限流（100次/分，C端用户）
for i in {1..110}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost/api/v1/user/profile -H "Authorization: Bearer <token>"; done
```

## K8s 部署

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml       # 先更新 secret.yaml 中的密钥

kubectl apply -f k8s/api-gateway/
kubectl apply -f k8s/auth-svc/
kubectl apply -f k8s/websocket-svc/

# 查看状态
kubectl get pods -n ilbuy -l layer=l1-gateway
```

## API 文档

- auth-svc Swagger UI: http://localhost:8001/swagger-ui.html
- websocket-svc Swagger UI: http://localhost:8002/swagger-ui.html
