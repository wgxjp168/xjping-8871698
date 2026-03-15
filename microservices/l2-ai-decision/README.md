# L2-AI 决策中枢 — ILbuy 我来购

## 服务清单

| 服务 | 技术栈 | 端口 | 职责 |
|------|--------|------|------|
| dialog-svc | Node.js 20 / Express 4 | **8013** | 多轮对话会话管理、L1 AUTH 集成 |
| intent-svc | Python 3.11 / FastAPI | **8010** | NLP 意图识别、实体提取、品牌检测 |
| llm-svc | Python 3.11 / FastAPI | **8011** | 大模型 API 封装（OpenAI/Claude/文心） |
| decision-svc | Python 3.11 / FastAPI | **8012** | Drools 规则引擎、三大评分模型、8步决策流程 |

## 目录结构总览

```
microservices/l2-ai-decision/
├── README.md
├── docker-compose.yml            # 本地开发环境
├── docker-compose.prod.yml       # 生产环境
├── .env.example
│
├── dialog-svc/                   # Node.js/Express :8013
│   ├── src/
│   │   ├── app.js                # Express 入口
│   │   ├── routes/
│   │   │   ├── dialog.js         # 对话路由
│   │   │   └── health.js
│   │   ├── services/
│   │   │   ├── dialogManager.js  # 多轮对话状态机
│   │   │   ├── sessionStore.js   # Redis 会话存储
│   │   │   └── intentClient.js   # 调用 intent-svc
│   │   ├── middleware/
│   │   │   ├── auth.js           # L1 AUTH_SVC 验证
│   │   │   └── errorHandler.js
│   │   ├── models/
│   │   │   └── dialog.js
│   │   └── config/
│   │       ├── default.js
│   │       └── production.js
│   ├── tests/
│   │   └── dialog.test.js
│   ├── package.json
│   ├── Dockerfile
│   ├── k8s/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── README.md
│
├── intent-svc/                   # Python/FastAPI :8010
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes.py         # /intent/recognize /entity/extract
│   │   │   └── deps.py
│   │   ├── services/
│   │   │   ├── intent_recognizer.py  # 意图分类（15类）
│   │   │   ├── entity_extractor.py   # 实体抽取（品牌/型号/预算等）
│   │   │   └── brand_detector.py     # 品牌已定/未定检测
│   │   ├── models/
│   │   │   └── schemas.py
│   │   └── core/
│   │       └── config.py
│   ├── tests/
│   │   └── test_intent.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── k8s/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── README.md
│
├── llm-svc/                      # Python/FastAPI :8011
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── routes.py         # /llm/chat /llm/analyze /llm/report
│   │   ├── services/
│   │   │   ├── llm_client.py     # 统一 LLM 客户端（OpenAI/Claude/文心）
│   │   │   ├── prompt_builder.py # 提示词工厂
│   │   │   └── response_parser.py
│   │   └── core/
│   │       └── config.py
│   ├── tests/
│   │   └── test_llm.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── k8s/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── README.md
│
└── decision-svc/                 # Python/FastAPI :8012
    ├── app/
    │   ├── main.py
    │   ├── api/
    │   │   └── routes.py         # /decision/analyze /decision/score /decision/report
    │   ├── services/
    │   │   ├── decision_engine.py    # AI决策八步流程
    │   │   ├── rule_engine.py        # Drools 规则引擎
    │   │   ├── report_generator.py   # 结构化报告生成
    │   │   ├── explainability.py     # 可解释性 NLP 引擎
    │   │   └── scoring/
    │   │       ├── b2b_scorer.py         # B2B 评分模型
    │   │       ├── b2c_known_scorer.py   # B2C 已定品牌评分
    │   │       └── b2c_unknown_scorer.py # B2C 未定品牌评分
    │   └── core/
    │       └── config.py
    ├── tests/
    │   └── test_decision.py
    ├── requirements.txt
    ├── Dockerfile
    ├── k8s/
    │   ├── deployment.yaml
    │   └── service.yaml
    └── README.md
```

## AI决策八步流程

```
Step 1: 用户输入接收          DIALOG_SVC:8013  → 会话管理+历史注入
Step 2: 意图识别+实体提取     INTENT_SVC:8010  → 15类意图+品牌/金额/参数
Step 3: 品牌状态检测          INTENT_SVC:8010  → 已定品牌 / 未定品牌 分流
Step 4: 大模型深度分析        LLM_SVC:8011     → 商品参数理解+行业知识
Step 5: 规则引擎过滤          DECISION_SVC:8012 → Drools规则+硬约束
Step 6: 评分模型计算          DECISION_SVC:8012 → B2B/B2C-Known/B2C-Unknown
Step 7: 可解释性生成          DECISION_SVC:8012 → SHAP值+自然语言解释
Step 8: 结构化报告输出        DECISION_SVC:8012 → JSON+Markdown报告→L3层预留
```

## 快速启动

```bash
cd microservices/l2-ai-decision
cp .env.example .env
# 填写 API Keys
docker-compose up -d
```

## 服务间数据流

```
L1 AUTH_SVC → dialog-svc:8013 → intent-svc:8010
                                    ↓
                              decision-svc:8012 ← llm-svc:8011
                                    ↓
                              [L3 数据采集预留接口]
```
