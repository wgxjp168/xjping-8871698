# ---- Build stage ----
FROM eclipse-temurin:17-jdk-alpine AS builder

RUN apk add --no-cache maven

WORKDIR /build

COPY pom.xml .
RUN mvn dependency:go-offline -q

COPY src ./src
RUN mvn package -DskipTests -q

# ---- Runtime stage ----
FROM eclipse-temurin:17-jre-alpine AS runtime

RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy

WORKDIR /app

COPY --from=builder /build/target/data-monetize-svc-*.jar app.jar

RUN chown ilbuy:ilbuy app.jar

USER ilbuy

EXPOSE 8074

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8074/actuator/health/liveness || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
