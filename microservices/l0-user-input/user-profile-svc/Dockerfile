# ==============================================================
# 构建方式（必须从项目根目录执行）：
#   docker build -f microservices/l0-user-input/user-profile-svc/Dockerfile \
#                -t user-profile-svc:1.0.0 .
# ==============================================================

# ===== 阶段1: 构建 =====
FROM maven:3.9.6-eclipse-temurin-21-alpine AS builder
WORKDIR /workspace

COPY pom.xml ./pom.xml
COPY common/common-core    ./common/common-core
COPY common/common-security ./common/common-security
COPY common/common-redis   ./common/common-redis
COPY common/common-mybatis  ./common/common-mybatis
COPY common/common-openfeign ./common/common-openfeign

RUN mvn install -pl common/common-core,common/common-security,common/common-redis,\
common/common-mybatis,common/common-openfeign -am -DskipTests -B -q

COPY microservices/l0-user-input/user-profile-svc \
     ./microservices/l0-user-input/user-profile-svc

RUN mvn package -pl microservices/l0-user-input/user-profile-svc \
    -DskipTests -B -q

# ===== 阶段2: 运行 =====
FROM eclipse-temurin:21-jre-alpine
LABEL maintainer="ilbuy-team@example.com"
LABEL service="user-profile-svc"
LABEL version="1.0.0"

RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy
USER ilbuy

WORKDIR /app
COPY --from=builder \
     /workspace/microservices/l0-user-input/user-profile-svc/target/user-profile-svc-*.jar \
     app.jar

ENV JAVA_OPTS="\
  -XX:+UseContainerSupport \
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
