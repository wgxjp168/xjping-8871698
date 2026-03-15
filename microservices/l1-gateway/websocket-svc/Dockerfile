# Build from project root:
# docker build -f microservices/l1-gateway/websocket-svc/Dockerfile -t ilbuy/websocket-svc:1.0.0 .

# ======== 构建阶段 ========
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /build

# 1. 复制根POM和公共模块POM（利用Docker层缓存加速依赖下载）
COPY pom.xml ./pom.xml
COPY common/common-core/pom.xml ./common/common-core/pom.xml
COPY common/common-security/pom.xml ./common/common-security/pom.xml
COPY common/common-mybatis/pom.xml ./common/common-mybatis/pom.xml
COPY common/common-redis/pom.xml ./common/common-redis/pom.xml
COPY common/common-openfeign/pom.xml ./common/common-openfeign/pom.xml
COPY microservices/l1-gateway/pom.xml ./microservices/l1-gateway/pom.xml
COPY microservices/l1-gateway/websocket-svc/pom.xml ./microservices/l1-gateway/websocket-svc/pom.xml
COPY microservices/l1-gateway/api-gateway/pom.xml ./microservices/l1-gateway/api-gateway/pom.xml
COPY microservices/l1-gateway/auth-svc/pom.xml ./microservices/l1-gateway/auth-svc/pom.xml
COPY microservices/l5-business-logic/user-svc/pom.xml ./microservices/l5-business-logic/user-svc/pom.xml
COPY microservices/l0-user-input/multimodal-input-svc/pom.xml ./microservices/l0-user-input/multimodal-input-svc/pom.xml
COPY microservices/l0-user-input/user-profile-svc/pom.xml ./microservices/l0-user-input/user-profile-svc/pom.xml

# 2. 复制所有源代码
COPY common/ ./common/
COPY microservices/l1-gateway/websocket-svc/src/ ./microservices/l1-gateway/websocket-svc/src/

# 3. 构建（先安装公共模块，再打包目标服务）
RUN --mount=type=cache,target=/root/.m2 \
    mvn install -pl common/common-core,common/common-security,common/common-redis,common/common-openfeign \
        -DskipTests -q && \
    mvn package -pl microservices/l1-gateway/websocket-svc \
        -DskipTests -q

# ======== 运行阶段 ========
FROM eclipse-temurin:21-jre-alpine
LABEL maintainer="ilbuy-team"
LABEL service="websocket-svc"
LABEL version="1.0.0"

RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy
USER ilbuy

WORKDIR /app

COPY --from=builder /build/microservices/l1-gateway/websocket-svc/target/websocket-svc-*.jar app.jar

ENV JAVA_OPTS="-server \
  -XX:+UseG1GC \
  -XX:MaxRAMPercentage=75.0 \
  -XX:+UseContainerSupport \
  -Djava.security.egd=file:/dev/./urandom"

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8002/actuator/health | grep -q '"status":"UP"' || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar app.jar"]
