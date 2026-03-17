# b-monetize-svc — B端商业变现服务

## 概述
L7商业变现层 B端服务。提供企业级SaaS年费订阅、API调用计费、定制服务报价功能。

**端口**: 8073
**上游依赖**: monetize-gateway-svc(8071), L5 ORDER_SVC(8051)

## 核心功能
- SaaS年费订单（企业年度订阅）
- 支付成功后自动激活SaaS合同
- API调用用量统计（按调用次数计费）
- 月度用量账单查询

## API
| Method | Path | 描述 |
|--------|------|------|
| POST | /internal/v1/b-orders | 创建B端订单 |
| GET  | /internal/v1/b-orders/{orderNo} | 查询订单 |
| POST | /internal/v1/api-usage | 记录API调用 |
| GET  | /internal/v1/api-usage/corps/{corpId}/monthly | 月度用量 |
| GET  | /internal/v1/api-usage/corps/{corpId}/contract | 有效合同 |

## 本地启动
```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```
