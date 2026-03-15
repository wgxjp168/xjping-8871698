# ─── Stage 1: Build ─────────────────────────────────────────────────────────
FROM eclipse-temurin:17-jdk-alpine AS builder

WORKDIR /build

# 先复制 pom 利用 Docker 层缓存
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 \
    mvn dependency:go-offline -q 2>/dev/null || true

COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn package -DskipTests -q && \
    java -Djarmode=layertools -jar target/data-svc-1.0.0.jar extract

# Maven 在 builder 阶段需要可用
RUN apk add --no-cache maven 2>/dev/null; \
    which mvn || (apk add --no-cache wget && \
    wget -q https://archive.apache.org/dist/maven/maven-3/3.9.6/binaries/apache-maven-3.9.6-bin.tar.gz && \
    tar -xf apache-maven-3.9.6-bin.tar.gz -C /opt && \
    ln -s /opt/apache-maven-3.9.6/bin/mvn /usr/local/bin/mvn)

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM eclipse-temurin:17-jre-alpine AS runtime

# 安全加固
RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy

WORKDIR /app

# 分层 JAR 复制（Docker 缓存友好）
COPY --from=builder /build/dependencies/          ./
COPY --from=builder /build/spring-boot-loader/    ./
COPY --from=builder /build/snapshot-dependencies/ ./
COPY --from=builder /build/application/           ./

RUN mkdir -p /app/logs && chown -R ilbuy:ilbuy /app

USER ilbuy

EXPOSE 8035

ENV JAVA_OPTS="-server -Xms256m -Xmx512m -XX:+UseG1GC \
               -XX:MaxGCPauseMillis=200 \
               -Djava.security.egd=file:/dev/./urandom"

ENV ENV=production

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD wget -qO- http://localhost:8035/health || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS org.springframework.boot.loader.launch.JarLauncher"]
