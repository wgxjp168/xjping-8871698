# =============================================================
#  websocket-gateway 多阶段构建 Dockerfile
#  构建命令：docker build -t ilbuy/websocket-gateway:1.0.0 .
# =============================================================

# ── 阶段 1：构建 ──
FROM maven:3.9.6-eclipse-temurin-17-alpine AS builder

WORKDIR /build

COPY pom.xml ./pom.xml
RUN mvn dependency:go-offline -B --no-transfer-progress 2>/dev/null || true

COPY src ./src
RUN mvn package -DskipTests -B --no-transfer-progress \
    && ls -lh target/*.jar

# ── 阶段 2：运行时 ──
FROM eclipse-temurin:17-jre-alpine AS runtime

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

COPY --from=builder /build/target/*.jar app.jar

RUN chown -R appuser:appgroup /app

USER appuser

# WebSocket 网关端口
EXPOSE 8090

# JVM 调优（WebSocket 长连接场景内存需求稍低）
ENV JAVA_OPTS="\
  -server \
  -XX:+UseContainerSupport \
  -XX:MaxRAMPercentage=70.0 \
  -XX:InitialRAMPercentage=40.0 \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=100 \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/tmp/heapdump.hprof \
  -Djava.security.egd=file:/dev/./urandom \
  -Dfile.encoding=UTF-8"

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -q --spider http://localhost:8090/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
