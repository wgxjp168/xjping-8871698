# ---- Build Stage ----
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# ---- Runtime Stage ----
FROM node:20-alpine
WORKDIR /app

RUN addgroup -S ilbuy && adduser -S ilbuy -G ilbuy

COPY --from=builder /app/node_modules ./node_modules
COPY src ./src
COPY package.json ./

RUN chown -R ilbuy:ilbuy /app
USER ilbuy

EXPOSE 8063

ENV NODE_ENV=production

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget -qO- http://localhost:8063/actuator/health/liveness || exit 1

CMD ["node", "src/app.js"]
