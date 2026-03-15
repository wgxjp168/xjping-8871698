# ===== 阶段1: 构建 =====
FROM maven:3.9.6-eclipse-temurin-21-alpine AS builder
WORKDIR /workspace

# 优先拷贝pom.xml利用Docker层缓存
COPY pom.xml .
COPY ../../../pom.xml /workspace/parent-pom.xml

# 下载依赖（仅pom变化时重新下载）
RUN mvn dependency:go-offline -B -f pom.xml || true

# 拷贝源码并构建
COPY src ./src
RUN mvn clean package -DskipTests -B -f pom.xml

# ===== 阶段2: 运行 =====
FROM eclipse-temurin:21-jre-alpine
LABEL maintainer="ilbuy-team@example.com"
LABEL service="multimodal-input-svc"
LABEL version="1.0.0"

# 创建非root用户运行
RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy
USER ilbuy

WORKDIR /app

# 拷贝jar
COPY --from=builder /workspace/target/multimodal-input-svc-*.jar app.jar

# JVM调优参数（容器感知内存）
ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:+UseG1GC \
               -XX:+HeapDumpOnOutOfMemoryError \
               -XX:HeapDumpPath=/tmp/heap-dump.hprof \
               -Djava.security.egd=file:/dev/./urandom \
               -Dspring.profiles.active=prod"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget -qO- http://localhost:8000/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar app.jar"]
