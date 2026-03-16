# ---- Build Stage ----
FROM eclipse-temurin:17-jdk-alpine AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN apk add --no-cache maven && \
    mvn -B -q package -DskipTests -Dmaven.repo.local=/root/.m2

# ---- Runtime Stage ----
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy
# Install fontconfig for PDF rendering
RUN apk add --no-cache fontconfig ttf-dejavu

COPY --from=builder /app/target/format-output-svc-*.jar app.jar
RUN chown ilbuy:ilbuy app.jar
USER ilbuy

EXPOSE 8062

ENV JAVA_OPTS="-Xms512m -Xmx1g -XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"
ENV SPRING_PROFILES_ACTIVE=prod

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD wget -qO- http://localhost:8062/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
