# AGENTS.md

## Cursor Cloud specific instructions

This repository contains **ILbuy (我来购) AI智能体微服务平台**, a cloud-native microservices e-commerce platform.

### Project structure

```
ilbuy-microservices/
├── pom.xml                      # 父 POM (Spring Boot 3.2.5 + Spring Cloud 2023.0.1)
├── access-layer/                # 接入层 - API网关 (Spring Cloud Gateway) - port 8080
├── ai-decision-hub/             # AI决策中枢 (Spring Boot Web) - port 8081
├── business-logic-layer/        # 业务逻辑层 (Spring Boot Web) - port 8082
├── data-layer/                  # 数据层 (Spring Data JPA + H2) - port 8083
├── support-and-ops-layer/       # 支撑运维层 (健康聚合/仪表盘) - port 8084
├── config-repo/                 # Spring Cloud Config 集中配置 (YAML)
├── docker/                      # 各服务 Dockerfile
└── docker-compose.yml           # 一键部署
```

### Environment

- **Java**: OpenJDK 21
- **Maven**: 3.9.6 at `/opt/apache-maven-3.9.6`, symlinked to `/usr/local/bin/mvn`
- **Docker**: required for `docker compose` deployment

### Quick start

```bash
cd /workspace/ilbuy-microservices
mvn clean package -DskipTests
sudo docker compose up -d --build
```

### Common commands (from `/workspace/ilbuy-microservices`)

| Action | Command |
|--------|---------|
| Compile all | `mvn compile` |
| Test all | `mvn test` |
| Package all | `mvn package -DskipTests` |
| Docker deploy | `sudo docker compose up -d --build` |
| Docker stop | `sudo docker compose down` |
| Docker logs | `sudo docker compose logs -f [service]` |

### Service ports

| Service | Port | Description |
|---------|------|-------------|
| access-layer | 8080 | API 网关 |
| ai-decision-hub | 8081 | AI 决策中枢 |
| business-logic-layer | 8082 | 业务逻辑 |
| data-layer | 8083 | 数据持久化 (H2) |
| support-and-ops-layer | 8084 | 运维监控 |

### Notes

- The gateway (access-layer) runs on Netty (reactive), not Tomcat.
- data-layer uses H2 in-memory DB; data resets on restart.
- support-and-ops-layer aggregates health from all services every 30s.
- Docker images use `eclipse-temurin:21-jre-alpine`.
- `docker-compose.yml` has health checks with `depends_on` ordering.
