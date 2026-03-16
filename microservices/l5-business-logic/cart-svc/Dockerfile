# ─── Stage 1: Build ──────────────────────────────────────────────────────────
FROM golang:1.21-alpine AS builder

RUN apk add --no-cache git ca-certificates tzdata

WORKDIR /build

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-w -s" -o cart-svc ./main.go

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM alpine:3.19 AS runtime

RUN apk add --no-cache ca-certificates tzdata && \
    addgroup -S ilbuy && adduser -S ilbuy -G ilbuy

WORKDIR /app

COPY --from=builder /build/cart-svc .

RUN chown ilbuy:ilbuy /app/cart-svc

USER ilbuy

EXPOSE 8025

ENV GIN_MODE=release

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:8025/actuator/health || exit 1

ENTRYPOINT ["./cart-svc"]
