# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM eclipse-temurin:17-jdk-alpine AS builder
WORKDIR /build

# Cache dependencies layer
COPY pom.xml .
RUN apk add --no-cache maven && \
    mvn dependency:go-offline -q

COPY src ./src
RUN mvn package -DskipTests -q && \
    ls -lh target/flink-job-*-uber.jar

# ── Stage 2: Flink Runtime ────────────────────────────────────────────────────
FROM flink:1.18.1-scala_2.12-java17

LABEL maintainer="ILbuy Platform <platform@ilbuy.com>"
LABEL description="ILbuy Product Analytics Flink Job"

# Non-root user
ARG UID=1001
RUN groupadd -g ${UID} flink-job && \
    useradd -u ${UID} -g flink-job -s /bin/sh -m flink-job

# Copy uber JAR into Flink usrlib (auto-loaded by Flink)
COPY --from=builder /build/target/flink-job-1.0.0-uber.jar /opt/flink/usrlib/flink-job.jar

USER flink-job

# Flink job is submitted via `flink run`, not directly executed.
# The ENTRYPOINT here is for standalone (non-cluster) local testing only.
ENTRYPOINT ["flink", "run", \
    "--class", "com.ilbuy.flink.FlinkJobMain", \
    "/opt/flink/usrlib/flink-job.jar"]

# Default arguments — override at runtime
CMD ["--rabbitmq-host", "rabbitmq", "--rabbitmq-port", "5672", \
     "--clickhouse-url", "jdbc:clickhouse://clickhouse:8123/ilbuy_analytics"]
