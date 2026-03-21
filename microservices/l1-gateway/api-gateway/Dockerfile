# =============================================================
#  api-gateway 多阶段构建 Dockerfile
#  构建命令：docker build -t ilbuy/api-gateway:1.0.0 .
#  运行命令：docker run -p 8080:8080 --env-file .env ilbuy/api-gateway:1.0.0
# =============================================================

# ── 阶段 1：构建（使用 Maven 缓存层加速增量构建） ──
FROM maven:3.9.6-eclipse-temurin-17-alpine AS builder

WORKDIR /build

# 先只复制 pom.xml，利用 Docker 层缓存跳过依赖下载
COPY pom.xml                                ../../pom.xml
COPY ../../pom.xml                          ../../l1-gateway-parent.pom.xml
RUN true

# 实际上在单模块构建时，只需父级和当前模块 pom
COPY pom.xml ./pom.xml
# 预下载依赖（只有 pom 变化时才重新下载）
RUN mvn dependency:go-offline -B --no-transfer-progress 2>/dev/null || true

# 复制源码并构建（跳过测试，CI 流水线单独执行测试）
COPY src ./src
RUN mvn package -DskipTests -B --no-transfer-progress \
    && ls -lh target/*.jar

# ── 阶段 2：运行时镜像（最小化，仅 JRE） ──
FROM eclipse-temurin:17-jre-alpine AS runtime

# 安全：以非 root 用户运行
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# 从构建阶段复制 fat-jar
COPY --from=builder /build/target/*.jar app.jar

# 修改文件属主
RUN chown -R appuser:appgroup /app

USER appuser

# 暴露端口
EXPOSE 8080

# JVM 调优（G1GC + 容器感知内存限制）
ENV JAVA_OPTS="\
  -server \
  -XX:+UseContainerSupport \
  -XX:MaxRAMPercentage=75.0 \
  -XX:InitialRAMPercentage=50.0 \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=200 \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/tmp/heapdump.hprof \
  -Djava.security.egd=file:/dev/./urandom \
  -Dfile.encoding=UTF-8"

# 健康检查（容器级别，K8s 另有探针）
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -q --spider http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
