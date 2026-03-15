# decision-svc — AI决策引擎微服务

ILbuy L2 AI决策中枢的核心引擎，实现**AI决策八步流程**，支持 B2B、B2C已定品牌、B2C未定品牌三大评分场景。

## 功能概述

- **AI决策八步流程**：输入验证 → 场景判断 → 上下文富化 → 规则过滤 → 评分计算 → LLM洞察 → 可解释性 → 结果编译
- **三大评分模型**：B2B（6维度）、B2C Known（5维度）、B2C Unknown（5维度）
- **Drools风格规则引擎**：库存/预算/品牌/质量等8条硬规则
- **SHAP启发可解释性**：特征重要性排名 + 反事实推断
- **结构化报告生成**：JSON / Markdown双格式

## 快速启动

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8012 --reload
```

## API端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET  | /health | 健康检查 |
| POST | /decision/analyze | 完整八步决策分析 |
| POST | /decision/score | 仅评分（无解释） |
| POST | /decision/rules | 仅规则检查 |
| GET  | /decision/report/{id} | 获取缓存决策报告 |
| POST | /decision/report/generate | 生成决策报告 |

## 请求示例

```bash
curl -X POST http://localhost:8012/decision/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess-001",
    "intent": "PRODUCT_INQUIRY",
    "entities": {"category": "手机", "budget_max": 4000},
    "brand_status": "UNKNOWN"
  }'
```

## 评分场景判断

| 条件 | 场景 |
|------|------|
| 意图为 PURCHASE_INQUIRY/CUSTOM_ORDER 或 customer_type=enterprise 或数量≥50 | B2B |
| brand_status=KNOWN | B2C_KNOWN |
| 其他 | B2C_UNKNOWN |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| ENV | development | 部署环境 |
| PORT | 8012 | 监听端口 |
| LLM_SVC_URL | http://llm-svc:8011 | 大模型服务URL |
| L3_DATA_SVC_URL | http://l3-data-svc:8020 | L3数据服务URL |
| LOG_LEVEL | INFO | 日志级别 |

## 运行测试

```bash
pytest tests/ -v
```
