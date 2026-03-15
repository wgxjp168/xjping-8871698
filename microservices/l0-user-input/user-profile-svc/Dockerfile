# ===== 阶段1: 构建 =====
FROM maven:3.9.6-eclipse-temurin-21-alpine AS builder
WORKDIR /workspace

COPY pom.xml .
RUN mvn dependency:go-offline -B -f pom.xml || true

COPY src ./src
RUN mvn clean package -DskipTests -B -f pom.xml

# ===== 阶段2: 运行 =====
FROM eclipse-temurin:21-jre-alpine
LABEL maintainer="ilbuy-team@example.com"
LABEL service="user-profile-svc"
LABEL version="1.0.0"

RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy
USER ilbuy

WORKDIR /app
COPY --from=builder /workspace/target/user-profile-svc-*.jar app.jar

ENV JAVA_OPTS="-XX:+UseContainerSupport \
               -XX:MaxRAMPercentage=75.0 \
               -XX:+UseG1GC \
               -XX:+HeapDumpOnOutOfMemoryError \
               -XX:HeapDumpPath=/tmp/heap-dump.hprof \
               -Djava.security.egd=file:/dev/./urandom \
               -Dspring.profiles.active=prod"

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget -qO- http://localhost:8001/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar app.jar"]
