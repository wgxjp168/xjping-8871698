# monetize-gateway-svc — 统一支付网关

## 概述
L7商业变现层的统一支付入口。集成微信支付V3、支付宝、银联，处理支付订单创建、回调、退款。

**端口**: 8071
**技术栈**: Spring Boot 3.2.5 · PostgreSQL · Redis · RabbitMQ

## 核心功能
- 统一下单（微信 JSAPI/Native、支付宝 App/页面、银联快捷）
- 支付回调处理（签名验证 + 幂等）
- 退款申请
- 支付结果事件发布（RabbitMQ）

## API
| Method | Path | 描述 |
|--------|------|------|
| POST | /api/v1/payments | 创建支付订单 |
| GET  | /api/v1/payments/{paymentNo} | 查询支付状态 |
| POST | /api/v1/payments/{paymentNo}/refund | 申请退款 |
| POST | /api/v1/payments/wechat/notify | 微信支付回调 |
| POST | /api/v1/payments/alipay/notify | 支付宝回调 |

## 本地启动
```bash
# 依赖
docker run -d -p 5432:5432 -e POSTGRES_DB=ilbuy_l7 -e POSTGRES_USER=ilbuy -e POSTGRES_PASSWORD=ilbuy123 postgres:15
docker run -d -p 6379:6379 redis:7
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# 启动
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

## 支付回调配置
生产环境需在各支付平台配置回调URL：
- 微信支付: `https://api.ilbuy.com/api/v1/payments/wechat/notify`
- 支付宝: `https://api.ilbuy.com/api/v1/payments/alipay/notify`
