# AGENTS.md

## Cursor Cloud specific instructions

This repository contains **ILbuy (我来购) AI智能体微服务平台**, a microservices-based e-commerce platform.

### Project structure

```
ilbuy-microservices/
├── pom.xml                  # 父 POM (Spring Boot 3.2.5 + Spring Cloud 2023.0.1)
├── access-layer/            # API网关接入层 (Spring Cloud Gateway) - port 8080
│   ├── pom.xml
│   └── src/
└── ai-decision-hub/         # AI智能决策中心 (Spring Boot Web) - port 8081
    ├── pom.xml
    └── src/
```

### Environment

- **Java**: OpenJDK 21 (pre-installed)
- **Maven**: 3.9.6 at `/opt/apache-maven-3.9.6`, symlinked to `/usr/local/bin/mvn`
- `MAVEN_HOME` and `PATH` are configured in `~/.bashrc`

### Common commands

All commands run from `/workspace/ilbuy-microservices`:

| Action | Command |
|--------|---------|
| Compile | `mvn compile` |
| Test | `mvn test` |
| Package | `mvn package -DskipTests` |
| Run access-layer | `java -jar access-layer/target/access-layer-1.0.0-SNAPSHOT.jar` |
| Run ai-decision-hub | `java -jar ai-decision-hub/target/ai-decision-hub-1.0.0-SNAPSHOT.jar` |

### access-layer endpoints (port 8080)

- `GET /` — service info
- `GET /health` — health check
- `GET /actuator/health` — Spring Actuator health
- `GET /actuator/gateway/routes` — list configured gateway routes

### ai-decision-hub endpoints (port 8081)

- `GET /api/ai/status` — service status and capabilities
- `POST /api/ai/recommendations` — 商品智能推荐
- `GET /api/ai/recommendations/{userId}` — 按用户ID获取推荐
- `POST /api/ai/pricing` — AI智能定价
- `POST /api/ai/decide` — 通用AI决策 (purchase_intent / fraud_detection / user_segment)

### Gateway routes (configured, downstream services not yet deployed)

- `/api/users/**` → `lb://user-service`
- `/api/products/**` → `lb://product-service`
- `/api/orders/**` → `lb://order-service`
- `/api/ai/**` → `lb://ai-agent-service`

### Notes

- The gateway runs on Netty (reactive stack), not Tomcat. It uses `spring-cloud-starter-gateway` (WebFlux-based).
- Discovery client shows UNKNOWN status because no service registry (Eureka/Nacos) is configured yet — this is expected for standalone dev.
- CORS is configured to allow all origins in dev mode.
