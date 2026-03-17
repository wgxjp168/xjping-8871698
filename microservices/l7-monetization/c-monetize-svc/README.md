# c-monetize-svc — C端商业变现服务

## 概述
L7商业变现层 C端服务。提供单次决策付费和会员订阅功能，与支付网关对接，监听支付结果事件。

**端口**: 8072
**上游依赖**: L5 ORDER_SVC(8051), L6 REPORT_SVC(8061), monetize-gateway-svc(8071)

## 核心功能
- 单次报告付费（¥99/份）
- 会员订阅（月/季/年计划）
- 支付结果自动处理（RabbitMQ监听）
- 订阅到期自动检查（定时任务）

## API
| Method | Path | 描述 |
|--------|------|------|
| POST | /internal/v1/c-orders | 创建C端订单 |
| GET  | /internal/v1/c-orders/{orderNo} | 查询订单 |
| GET  | /internal/v1/c-orders/user/{userId} | 用户订单列表 |
| GET  | /internal/v1/plans | 获取会员计划 |
| GET  | /internal/v1/subscriptions/user/{userId} | 查询用户订阅 |
| GET  | /internal/v1/subscriptions/user/{userId}/valid | 校验会员有效性 |

## 本地启动
```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
# 需要 monetize-gateway-svc 在 8071 启动
```
