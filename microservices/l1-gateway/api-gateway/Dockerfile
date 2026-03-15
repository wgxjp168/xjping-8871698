# ======== 构建阶段 ========
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /build

COPY pom.xml .
COPY src ./src

# 离线构建（CI 环境已预热本地仓库）
RUN --mount=type=cache,target=/root/.m2 \
    mvn package -DskipTests -q

# ======== 运行阶段 ========
FROM eclipse-temurin:21-jre-alpine
LABEL maintainer="ilbuy-team"
LABEL service="api-gateway"
LABEL version="1.0.0"

# 安全：非 root 用户运行
RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy
USER ilbuy

WORKDIR /app

COPY --from=builder /build/target/api-gateway-*.jar app.jar

# JVM 调优：G1GC + 容器感知内存
ENV JAVA_OPTS="-server \
  -XX:+UseG1GC \
  -XX:MaxRAMPercentage=75.0 \
  -XX:+UseContainerSupport \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/tmp/heap-dump.hprof \
  -Djava.security.egd=file:/dev/./urandom"

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:80/actuator/health | grep -q '"status":"UP"' || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar app.jar"]
