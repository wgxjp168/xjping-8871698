# 惠东县区域公卫体检集中系统
## 完整运营体系文档 · 总目录

**文档版本**: V1.0.0
**编制日期**: 2026-03-25
**适用范围**: 系统运维团队、卫生院信息科、公卫科、县卫健局
**密级**: 内部使用

---

## 文档目录

| 编号 | 文档名称 | 文件 |
|------|---------|------|
| 01 | 项目建设成果总结 | [OPS-01-ACHIEVEMENTS.md](docs/OPS-01-ACHIEVEMENTS.md) |
| 02 | 生产环境部署架构 | [OPS-02-DEPLOYMENT.md](docs/OPS-02-DEPLOYMENT.md) |
| 03 | 系统上线交付步骤 | [OPS-03-DELIVERY.md](docs/OPS-03-DELIVERY.md) |
| 04 | 业务运营全流程 | [OPS-04-BUSINESS-FLOW.md](docs/OPS-04-BUSINESS-FLOW.md) |
| 05 | 日常操作手册 | [OPS-05-OPERATION-MANUAL.md](docs/OPS-05-OPERATION-MANUAL.md) |
| 06 | 权限运营体系 | [OPS-06-PERMISSION.md](docs/OPS-06-PERMISSION.md) |
| 07 | 设备接入与运维 | [OPS-07-DEVICE.md](docs/OPS-07-DEVICE.md) |
| 08 | 数据质量管控 | [OPS-08-DATA-QUALITY.md](docs/OPS-08-DATA-QUALITY.md) |
| 09 | 系统运维保障 | [OPS-09-MAINTENANCE.md](docs/OPS-09-MAINTENANCE.md) |
| 10 | 验收标准与考核 | [OPS-10-ACCEPTANCE.md](docs/OPS-10-ACCEPTANCE.md) |
| 11 | 长期迭代规划 | [OPS-11-ROADMAP.md](docs/OPS-11-ROADMAP.md) |
| 12 | 风险点与应对措施 | [OPS-12-RISK.md](docs/OPS-12-RISK.md) |

---

## 系统核心参数速查

```
【服务地址】
  前端入口:    http://[服务器IP]:3000  (生产: https://phcheck.huidong.gov.cn)
  API网关:     http://[服务器IP]:9090
  认证服务:    http://[服务器IP]:8001
  居民服务:    http://[服务器IP]:8002
  设备服务:    http://[服务器IP]:8003  + TCP:7100(ASTM设备)
  体检服务:    http://[服务器IP]:8004
  DR服务:      http://[服务器IP]:8005

【数据库】
  MySQL 8.0:   localhost:3306  库名: hd_public_health
  Redis 6.x:   localhost:6379  (JWT黑名单/缓存)

【默认账号】
  超级管理员:  admin / hd2024
  医生示例:    doctor01 / hd2024

【紧急联系】
  运维热线:    0752-XXXXXXX
  值班手机:    138-XXXX-XXXX
```
