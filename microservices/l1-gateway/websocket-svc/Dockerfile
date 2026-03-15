# ======== 构建阶段 ========
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /build

COPY pom.xml .
COPY src ./src

RUN --mount=type=cache,target=/root/.m2 \
    mvn package -DskipTests -q

# ======== 运行阶段 ========
FROM eclipse-temurin:21-jre-alpine
LABEL maintainer="ilbuy-team"
LABEL service="websocket-svc"
LABEL version="1.0.0"

RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy
USER ilbuy

WORKDIR /app

COPY --from=builder /build/target/websocket-svc-*.jar app.jar

ENV JAVA_OPTS="-server \
  -XX:+UseG1GC \
  -XX:MaxRAMPercentage=75.0 \
  -XX:+UseContainerSupport \
  -Djava.security.egd=file:/dev/./urandom"

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8002/actuator/health | grep -q '"status":"UP"' || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar app.jar"]
