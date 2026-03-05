# 我来购（ILbuy）云原生微服务技术方案

> 版本：v1.0 | 日期：2026-03-05 | 定位：可直接落地的技术架构文档

---

## 目录

1. [整体架构描述](#1-整体架构描述)
2. [微服务拆分清单](#2-微服务拆分清单)
3. [各层职责与交互流程](#3-各层职责与交互流程)
4. [技术栈](#4-技术栈)
5. [数据库表结构设计](#5-数据库表结构设计)
6. [接口规范](#6-接口规范)
7. [Docker + K8s 部署方案](#7-docker--k8s-部署方案)

---

## 1. 整体架构描述

### 1.1 架构总览

ILbuy 采用**云原生五层微服务架构**，以 AI 决策中枢为核心能力，通过标准化接入层对外提供服务，业务逻辑层承载核心交易流程，数据层保障数据可靠存储与高效检索，支撑运维层提供全链路可观测性与自动化交付能力。

```
┌─────────────────────────────────────────────────────────────────────┐
│                     第一层：接入层（Gateway Layer）                    │
│   终端用户(C/B端)  ──►  Kong/Nginx API 网关  ──►  认证 / 限流           │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                   第二层：AI 决策中枢（AI Layer）                       │
│   对话管理(Node.js)  ►  意图识别(FastAPI/NLP)  ►  大模型(OpenAI/Claude)│
│                                  ►  决策引擎(Drools+ML)               │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                  第三层：业务逻辑层（Business Layer）                   │
│   用户服务  │  商品服务  │  订单服务  │  配置服务  │  通知服务  │ 文件服务 │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                    第四层：数据层（Data Layer）                         │
│   MySQL(主库) │ Redis(缓存) │ ES(搜索) │ MinIO(文件) │ ClickHouse(分析)│
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│               第五层：支撑与运维层（Infrastructure Layer）               │
│   Kubernetes │ Prometheus/Grafana │ ELK │ Jaeger │ Jenkins/GitLab CI │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

| 原则 | 实现方式 |
|------|----------|
| 服务自治 | 每个微服务独立部署、独立扩缩容、独立数据库 |
| API First | 所有服务通过 REST/gRPC 接口通信，契约先行 |
| 异步解耦 | 跨服务事件通过 RabbitMQ 异步传递 |
| 可观测性 | 全链路 Tracing + Metrics + Logging |
| 数据合规 | 外部平台数据仅通过官方开放 API 采集 |
| 安全纵深 | 网关鉴权 + 服务间 mTLS + Vault 密钥管理 |

---

## 2. 微服务拆分清单

### 2.1 服务总览

| # | 服务名称 | 英文标识 | 语言/框架 | 端口 | 核心职责 |
|---|----------|----------|-----------|------|----------|
| 1 | API 网关服务 | api-gateway | Kong/Nginx | 80/443 | 路由、鉴权、限流、日志 |
| 2 | 认证授权服务 | auth-service | Spring Boot | 8001 | JWT 签发、OAuth2.0、权限校验 |
| 3 | 对话管理服务 | dialog-service | Node.js | 8013 | 多轮对话上下文管理 |
| 4 | 意图识别服务 | intent-service | Python/FastAPI | 8010 | NLP 解析 + 实体提取 |
| 5 | 大模型调用服务 | llm-service | Python/FastAPI | 8011 | 封装 OpenAI/Claude API |
| 6 | 决策引擎服务 | decision-service | Python/FastAPI | 8012 | 规则引擎 + ML 模型评分 |
| 7 | 用户服务 | user-service | Spring Boot | 8020 | 注册/登录/用户画像 |
| 8 | 商品服务 | product-service | Go/Gin | 8021 | 商品聚合查询、比价 |
| 9 | 订单服务 | order-service | Spring Boot | 8022 | 下单/履约/状态追踪 |
| 10 | 配置服务 | config-service | Spring Boot | 8023 | 对接 Nacos 动态配置 |
| 11 | 通知服务 | notify-service | Node.js | 8040 | 短信/微信/Push 通知 |
| 12 | 文件服务 | file-service | Go | 8041 | 合同生成/MinIO 文件管理 |
| 13 | 数据采集服务 | crawler-service | Python/Scrapy | 8030 | 定时调用平台官方 API |
| 14 | ETL 清洗服务 | etl-service | Python | 8031 | 数据标准化/评分计算 |
| 15 | 反馈服务 | feedback-service | Node.js | 8050 | AI 满意度回访/数据反馈 |
| 16 | 模型迭代服务 | model-iteration | Python | 8051 | A/B 测试 + 模型重训 |

### 2.2 服务依赖关系

```
请求链路（C 端用户购物场景）：
用户请求 → API GW → Auth SVC(鉴权) → Dialog SVC
         → Intent SVC(意图识别)
         → LLM SVC(大模型理解)
         → Decision SVC(决策打分)
         → Product SVC(商品查询) → ES(搜索) + Redis(缓存)
         → Order SVC(创建订单) → MySQL + RabbitMQ
         → Notify SVC(发送通知)
         → 返回用户

数据采集链路：
外部平台 API → Crawler SVC → ETL SVC → MySQL + ES
MySQL → Canal(CDC) → RabbitMQ → ES(同步)
```

---

## 3. 各层职责与交互流程

### 3.1 第一层：接入层

**职责：**
- **路由分发**：根据 URL 前缀将请求路由到对应微服务
- **身份认证**：验证 JWT Token，转发至 Auth SVC 进行权限核查
- **限流熔断**：C 端 100 req/min，B 端 1000 req/min，超限返回 429
- **日志采集**：记录所有请求的 traceId、耗时、状态码
- **SSL 终止**：处理 HTTPS，向下游传递明文

**关键配置（Kong 示例）：**

```yaml
# Kong 路由规则
services:
  - name: dialog-service
    url: http://dialog-service:8013
    routes:
      - name: dialog-route
        paths: ["/api/v1/dialog"]
    plugins:
      - name: jwt
      - name: rate-limiting
        config:
          minute: 100
          policy: local
      - name: request-id
```

**交互流程：**
```
Client → HTTPS → Kong(SSL终止 + 路由匹配)
       → Plugin: JWT验证 → Auth SVC:8001/verify
       → Plugin: 限流检查 → Redis(计数器)
       → Plugin: 日志记录 → ELK
       → 转发至目标服务
```

---

### 3.2 第二层：AI 决策中枢

**职责：**
- **对话管理**（dialog-service）：维护多轮会话上下文，基于 Redis 存储 session
- **意图识别**（intent-service）：解析自然语言/图片/商品链接，提取购买意图和商品实体
- **大模型调用**（llm-service）：封装 OpenAI/Claude API，处理 prompt 工程、重试、降级
- **决策引擎**（decision-service）：结合规则引擎（Drools）和 ML 模型，对候选商品多维评分

**AI 决策五步流程：**

```
Step 1 [意图识别]
  输入：用户自然语言 / 图片 / 商品链接
  处理：NLP 分词 + 实体识别(品类/品牌/价格区间/质量要求)
  输出：结构化采购需求 JSON

Step 2 [标准生成]
  输入：意图 JSON
  处理：LLM 扩展理解 → 生成采购标准(规格/参数/排除条件)
  输出：标准化采购 Schema

Step 3 [决策打分]
  输入：候选商品列表 + 采购标准
  处理：Drools 规则引擎(硬性过滤) + ML 模型(软性评分)
  输出：商品评分排行榜

Step 4 [结果输出]
  处理：双档推荐(品质款 Top3 + 性价比款 Top3)
  输出：推荐结果 JSON

Step 5 [对话管理]
  处理：记录本轮对话到 Redis Session，支持追问
  输出：对话状态更新
```

**服务间调用：**
```
Dialog SVC --HTTP--> Intent SVC:8010/analyze
Intent SVC --HTTP--> LLM SVC:8011/completion
LLM SVC    --HTTP--> Decision SVC:8012/score
Decision SVC --HTTP--> Product SVC:8021/search
```

---

### 3.3 第三层：业务逻辑层

**各服务职责：**

| 服务 | 核心功能 | 对外接口数 |
|------|----------|-----------|
| user-service | 注册/登录/OAuth/用户画像/偏好管理 | 12 |
| product-service | 商品聚合查询/多平台价格比对/库存状态 | 8 |
| order-service | 创建订单/订单状态机/履约追踪/退款 | 15 |
| config-service | 动态配置读写/Nacos 热更新/灰度开关 | 6 |
| notify-service | 短信/微信模板消息/App Push/邮件 | 5 |
| file-service | 合同 PDF 生成/MinIO 上传下载/签名 | 4 |

**交互流程（下单场景）：**
```
Decision SVC 推荐商品
  → 用户确认 → Order SVC:createOrder
  → Order SVC → User SVC(验证用户状态)
  → Order SVC → Product SVC(锁定库存)
  → Order SVC → MySQL(持久化订单)
  → Order SVC → RabbitMQ(发布 order.created 事件)
  → Notify SVC(消费事件 → 发送确认通知)
  → File SVC(消费事件 → 生成采购合同)
  → Order SVC → 外部支付网关(微信/支付宝)
```

---

### 3.4 第四层：数据层

**存储组件分工：**

| 组件 | 版本 | 用途 | 容量规划 |
|------|------|------|----------|
| MySQL | 8.0 | 核心业务数据(用户/订单/配置) | 主从1:2，SSD 2TB |
| Redis | 7.2 | 会话缓存/限流计数/热点商品 | Cluster 3主3从，64GB |
| Elasticsearch | 8.11 | 商品全文检索/日志存储 | 3节点，1TB |
| MinIO | Latest | 合同/图片/附件对象存储 | 分布式10TB |
| ClickHouse | Latest | 用户行为分析/对话日志统计 | 2节点，2TB |
| Canal | Latest | MySQL CDC 增量同步 | — |
| RabbitMQ | 3.12 | 服务间异步消息队列 | 3节点集群 |

**数据流：**
```
外部平台官方 API
  → Crawler SVC(定时采集)
  → ETL SVC(清洗/标准化/评分)
  → MySQL(持久化) + ES(索引)

MySQL 变更
  → Canal(监听 binlog)
  → RabbitMQ(发布变更事件)
  → ES(更新索引) / 其他消费者

用户行为数据
  → Dialog SVC / Order SVC
  → ClickHouse(实时写入)
  → Model Iteration SVC(训练数据)
```

---

### 3.5 第五层：支撑与运维层

**可观测性三大支柱：**

```
Metrics：Prometheus 采集所有服务 /metrics 端点
         → Grafana 展示(QPS/延迟/错误率/资源占用)
         → AlertManager 告警(钉钉/短信/PagerDuty)

Logging：各服务结构化日志 → Filebeat → Logstash
         → Elasticsearch → Kibana(查询/分析)

Tracing：OpenTelemetry SDK 自动注入 traceId
         → Jaeger(分布式链路追踪/耗时分析)
```

**CI/CD 流水线：**
```
开发推代码 → GitLab CI
  → 单元测试(JUnit/pytest/Jest)
  → 代码扫描(SonarQube)
  → 镜像构建(Docker buildx)
  → 推送(Harbor 私有镜像仓库)
  → ArgoCD GitOps 自动部署
  → 冒烟测试
  → 生产发布(蓝绿/金丝雀)
```

---

## 4. 技术栈

### 4.1 前端

| 终端 | 框架 | 构建工具 | 状态管理 | UI 组件库 |
|------|------|----------|----------|-----------|
| H5/Web | React 18 + TypeScript | Vite | Zustand | Ant Design 5 |
| 微信小程序 | React Native / Taro | — | MobX | NutUI |
| B 端管理后台 | React 18 + TypeScript | Vite | Redux Toolkit | Ant Design Pro |

### 4.2 后端

| 服务类型 | 语言 | 框架 | 说明 |
|----------|------|------|------|
| Java 服务 | Java 17 | Spring Boot 3.x | user/order/config-service |
| Go 服务 | Go 1.21 | Gin | product/file-service（高并发） |
| Python 服务 | Python 3.11 | FastAPI | AI 相关服务 |
| Node.js 服务 | Node 20 | Express/Koa | dialog/notify-service（I/O密集） |

### 4.3 中间件与基础设施

| 类别 | 技术选型 | 版本 |
|------|----------|------|
| API 网关 | Kong + Nginx | Kong 3.x |
| 服务注册发现 | Nacos | 2.3 |
| 配置中心 | Nacos | 2.3 |
| 消息队列 | RabbitMQ | 3.12 |
| 缓存 | Redis Cluster | 7.2 |
| 搜索 | Elasticsearch | 8.11 |
| 对象存储 | MinIO | Latest |
| 数据同步 | Canal | Latest |
| 密钥管理 | Vault | Latest |
| 容器运行时 | Docker | 25+ |
| 容器编排 | Kubernetes | 1.29 |
| 镜像仓库 | Harbor | Latest |
| GitOps | ArgoCD | Latest |
| 监控 | Prometheus + Grafana | Latest |
| 日志 | ELK Stack | 8.x |
| 追踪 | Jaeger + OpenTelemetry | Latest |
| CI/CD | GitLab CI / Jenkins | Latest |

### 4.4 AI/ML 技术栈

| 组件 | 技术 |
|------|------|
| 大语言模型 | OpenAI GPT-4o / Claude 3.5 Sonnet |
| NLP 框架 | spaCy + HuggingFace Transformers |
| 规则引擎 | Drools 8.x |
| ML 框架 | scikit-learn / LightGBM |
| 向量检索 | ES dense_vector + kNN |
| A/B 测试 | 自研 + ClickHouse 分析 |

---

## 5. 数据库表结构设计

### 5.1 用户相关表

```sql
-- 用户主表
CREATE TABLE `t_user` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `open_id`       VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '微信 OpenID',
  `union_id`      VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '微信 UnionID',
  `mobile`        VARCHAR(20)     NOT NULL DEFAULT '' COMMENT '手机号(脱敏存储)',
  `mobile_hash`   CHAR(64)        NOT NULL DEFAULT '' COMMENT '手机号 SHA256（查询用）',
  `nickname`      VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '昵称',
  `avatar_url`    VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '头像URL',
  `user_type`     TINYINT         NOT NULL DEFAULT 1 COMMENT '用户类型 1:C端 2:B端',
  `status`        TINYINT         NOT NULL DEFAULT 1 COMMENT '状态 1:正常 2:禁用',
  `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mobile_hash` (`mobile_hash`),
  KEY `idx_open_id` (`open_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户主表';

-- 用户偏好画像
CREATE TABLE `t_user_profile` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`         BIGINT UNSIGNED NOT NULL,
  `prefer_category` JSON            COMMENT '偏好品类 [{"cat":"3C","weight":0.8}]',
  `price_range`     JSON            COMMENT '价格区间 {"min":100,"max":5000}',
  `quality_level`   TINYINT         NOT NULL DEFAULT 2 COMMENT '品质偏好 1:性价比 2:均衡 3:品质',
  `prefer_platform` JSON            COMMENT '偏好平台 ["taobao","jd"]',
  `updated_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户偏好画像';
```

### 5.2 商品相关表

```sql
-- 商品聚合表（来自各平台标准化后的数据）
CREATE TABLE `t_product` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `platform`      VARCHAR(20)     NOT NULL COMMENT '平台 taobao/jd/pdd/1688/vip',
  `platform_id`   VARCHAR(64)     NOT NULL COMMENT '平台商品ID',
  `title`         VARCHAR(256)    NOT NULL COMMENT '商品标题',
  `category_id`   INT             NOT NULL DEFAULT 0 COMMENT '标准品类ID',
  `brand`         VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '品牌',
  `price`         DECIMAL(12,2)   NOT NULL DEFAULT 0 COMMENT '当前价格',
  `origin_price`  DECIMAL(12,2)   NOT NULL DEFAULT 0 COMMENT '原价',
  `shop_name`     VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '店铺名',
  `shop_score`    DECIMAL(3,2)    NOT NULL DEFAULT 0 COMMENT '店铺评分',
  `sales_30d`     INT             NOT NULL DEFAULT 0 COMMENT '近30天销量',
  `rating_score`  DECIMAL(3,2)    NOT NULL DEFAULT 0 COMMENT '商品综合评分',
  `main_image`    VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '主图URL',
  `detail_url`    VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '商品详情页',
  `stock_status`  TINYINT         NOT NULL DEFAULT 1 COMMENT '库存状态 1:有货 2:预售 3:无货',
  `ai_score`      DECIMAL(5,2)    NOT NULL DEFAULT 0 COMMENT 'AI综合评分(0-100)',
  `is_active`     TINYINT         NOT NULL DEFAULT 1 COMMENT '是否有效',
  `fetched_at`    DATETIME        NOT NULL COMMENT '数据采集时间',
  `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_platform_product` (`platform`, `platform_id`),
  KEY `idx_category_score` (`category_id`, `ai_score`),
  KEY `idx_brand` (`brand`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品聚合表';

-- 商品属性扩展（KV 结构）
CREATE TABLE `t_product_attr` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id` BIGINT UNSIGNED NOT NULL,
  `attr_key`   VARCHAR(64)     NOT NULL COMMENT '属性名（颜色/尺寸/材质等）',
  `attr_value` VARCHAR(256)    NOT NULL COMMENT '属性值',
  PRIMARY KEY (`id`),
  KEY `idx_product_id` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品属性表';
```

### 5.3 订单相关表

```sql
-- 订单主表
CREATE TABLE `t_order` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_no`        VARCHAR(32)     NOT NULL COMMENT '订单号（全局唯一）',
  `user_id`         BIGINT UNSIGNED NOT NULL,
  `dialog_id`       VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '关联对话ID',
  `status`          TINYINT         NOT NULL DEFAULT 1
                    COMMENT '状态 1:待支付 2:已支付 3:履约中 4:已完成 5:已取消 6:退款中 7:已退款',
  `total_amount`    DECIMAL(12,2)   NOT NULL DEFAULT 0 COMMENT '订单总金额',
  `pay_amount`      DECIMAL(12,2)   NOT NULL DEFAULT 0 COMMENT '实付金额',
  `platform`        VARCHAR(20)     NOT NULL COMMENT '下单平台',
  `platform_order_no` VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '平台订单号',
  `pay_type`        TINYINT         NOT NULL DEFAULT 0 COMMENT '支付方式 1:微信 2:支付宝',
  `pay_time`        DATETIME                 COMMENT '支付时间',
  `delivery_time`   DATETIME                 COMMENT '发货时间',
  `finish_time`     DATETIME                 COMMENT '完成时间',
  `remark`          VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '备注',
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_user_id_status` (`user_id`, `status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单主表';

-- 订单商品明细
CREATE TABLE `t_order_item` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_id`    BIGINT UNSIGNED NOT NULL,
  `product_id`  BIGINT UNSIGNED NOT NULL,
  `product_name` VARCHAR(256)   NOT NULL,
  `platform`    VARCHAR(20)     NOT NULL,
  `price`       DECIMAL(12,2)   NOT NULL,
  `quantity`    INT             NOT NULL DEFAULT 1,
  `subtotal`    DECIMAL(12,2)   NOT NULL,
  `snapshot`    JSON            COMMENT '下单时商品快照',
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单商品明细';

-- 订单状态流转日志
CREATE TABLE `t_order_log` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_id`    BIGINT UNSIGNED NOT NULL,
  `from_status` TINYINT         NOT NULL,
  `to_status`   TINYINT         NOT NULL,
  `operator`    VARCHAR(64)     NOT NULL DEFAULT 'system' COMMENT '操作人',
  `remark`      VARCHAR(256)    NOT NULL DEFAULT '',
  `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单状态日志';
```

### 5.4 对话相关表

```sql
-- 对话会话表
CREATE TABLE `t_dialog_session` (
  `id`           VARCHAR(64)     NOT NULL COMMENT '会话ID(UUID)',
  `user_id`      BIGINT UNSIGNED NOT NULL,
  `status`       TINYINT         NOT NULL DEFAULT 1 COMMENT '1:进行中 2:已结束',
  `intent_json`  JSON            COMMENT '最终识别意图',
  `result_json`  JSON            COMMENT '推荐结果快照',
  `turn_count`   INT             NOT NULL DEFAULT 0 COMMENT '对话轮次',
  `created_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话会话表';

-- 对话消息记录
CREATE TABLE `t_dialog_message` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `session_id`  VARCHAR(64)     NOT NULL,
  `role`        VARCHAR(16)     NOT NULL COMMENT 'user/assistant/system',
  `content`     TEXT            NOT NULL COMMENT '消息内容',
  `msg_type`    TINYINT         NOT NULL DEFAULT 1 COMMENT '1:文本 2:图片 3:链接',
  `extra`       JSON            COMMENT '扩展数据（图片URL等）',
  `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话消息记录';
```

### 5.5 配置相关表

```sql
-- 系统配置表（备份 Nacos 配置）
CREATE TABLE `t_config` (
  `id`          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  `config_key`  VARCHAR(128)    NOT NULL COMMENT '配置键',
  `config_value` TEXT           NOT NULL COMMENT '配置值（支持JSON）',
  `description` VARCHAR(256)    NOT NULL DEFAULT '',
  `env`         VARCHAR(16)     NOT NULL DEFAULT 'prod' COMMENT '环境',
  `is_active`   TINYINT         NOT NULL DEFAULT 1,
  `updated_by`  VARCHAR(64)     NOT NULL DEFAULT '',
  `updated_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_key_env` (`config_key`, `env`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';
```

### 5.6 Redis 键值设计

```
# 用户会话 Token
key:   session:{userId}:{deviceId}
type:  String (JWT Token)
ttl:   7200s (2小时)

# 对话上下文（存储最近20轮）
key:   dialog:context:{sessionId}
type:  List
ttl:   3600s

# 商品缓存
key:   product:detail:{productId}
type:  Hash
ttl:   300s (5分钟)

# 限流计数器
key:   rate:{userId}:{minute}
type:  String (INCR)
ttl:   60s

# 热门品类缓存
key:   hot:category:list
type:  ZSet (score=搜索频次)
ttl:   3600s
```

---

## 6. 接口规范

### 6.1 全局约定

```
Base URL:   https://api.ilbuy.com
版本控制:   /api/v1/...
数据格式:   application/json
字符编码:   UTF-8
认证方式:   Bearer Token (JWT)
请求头:     X-Request-Id: {UUID}
            X-Device-Type: h5|app|miniprogram|b-portal
时间格式:   ISO 8601 (2026-03-05T10:00:00+08:00)
```

### 6.2 统一响应结构

```json
{
  "code":    200,
  "message": "success",
  "data":    {},
  "traceId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1741132800000
}
```

**业务状态码：**

| Code | 含义 |
|------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务端错误 |
| 1001 | 用户不存在 |
| 1002 | Token 过期 |
| 2001 | 商品库存不足 |
| 3001 | AI 服务暂时不可用 |

### 6.3 核心接口定义

#### 认证接口

```http
# 微信小程序登录
POST /api/v1/auth/wx-login
Content-Type: application/json

Request:
{
  "code": "wx_auth_code_from_client"
}

Response:
{
  "code": 200,
  "data": {
    "token":      "eyJhbGciOiJIUzI1NiJ9...",
    "expireAt":   1741219200000,
    "userInfo": {
      "userId":   10001,
      "nickname": "张三",
      "avatarUrl": "https://...",
      "isNewUser": false
    }
  }
}
```

#### 对话接口

```http
# 发起/继续对话（核心接口）
POST /api/v1/dialog/chat
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "sessionId":  "optional-existing-session-id",
  "msgType":    1,           // 1:文本 2:图片 3:商品链接
  "content":    "我想买一台适合学生用的笔记本电脑，预算5000以内",
  "imageUrl":   null,        // msgType=2时必填
  "productUrl": null         // msgType=3时必填
}

Response:
{
  "code": 200,
  "data": {
    "sessionId": "sess_20260305_abc123",
    "turnId":    1,
    "reply": {
      "text":     "好的，我来帮您找适合学生用的笔记本电脑...",
      "type":     "recommendation"
    },
    "intent": {
      "category":   "笔记本电脑",
      "priceRange": {"min": 0, "max": 5000},
      "useCase":    "学生",
      "confirmed":  true
    },
    "recommendations": {
      "quality": [
        {
          "productId":  123456,
          "platform":   "jd",
          "title":      "联想小新 Pro 14...",
          "price":      4999.00,
          "aiScore":    92.5,
          "highlights": ["性能强劲", "屏幕素质高", "京东自营"],
          "detailUrl":  "https://item.jd.com/..."
        }
      ],
      "costEffective": [...]
    },
    "followUpSuggestions": ["有没有更轻薄的？", "查一下这个型号的评价"]
  }
}
```

#### 商品接口

```http
# 商品搜索
GET /api/v1/products/search?keyword=笔记本电脑&categoryId=1001&minPrice=0&maxPrice=5000&platform=jd&sortBy=aiScore&page=1&pageSize=20
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "total":    256,
    "page":     1,
    "pageSize": 20,
    "list": [
      {
        "productId":   123456,
        "platform":    "jd",
        "title":       "联想小新 Pro 14 2025款",
        "price":       4999.00,
        "originPrice": 5499.00,
        "discount":    "91折",
        "shopName":    "联想京东自营旗舰店",
        "shopScore":   4.9,
        "sales30d":    12000,
        "ratingScore": 4.8,
        "aiScore":     92.5,
        "mainImage":   "https://img...",
        "detailUrl":   "https://item.jd.com/..."
      }
    ]
  }
}

# 商品详情
GET /api/v1/products/{productId}
Authorization: Bearer {token}
```

#### 订单接口

```http
# 创建订单
POST /api/v1/orders
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "sessionId":  "sess_20260305_abc123",
  "items": [
    {
      "productId": 123456,
      "quantity":  1
    }
  ],
  "payType":  1,
  "remark":   "帮我包装好点"
}

Response:
{
  "code": 200,
  "data": {
    "orderId":    987654,
    "orderNo":    "IL20260305987654",
    "status":     1,
    "totalAmount": 4999.00,
    "payAmount":   4999.00,
    "payUrl":     "https://wx.pay/..."    // 微信支付 URL
  }
}

# 查询订单列表
GET /api/v1/orders?status=&page=1&pageSize=10
Authorization: Bearer {token}

# 查询订单详情
GET /api/v1/orders/{orderId}
Authorization: Bearer {token}

# 取消订单
POST /api/v1/orders/{orderId}/cancel
Authorization: Bearer {token}
Content-Type: application/json
{"reason": "不想买了"}
```

#### 用户接口

```http
# 获取用户信息
GET /api/v1/users/me
Authorization: Bearer {token}

# 更新用户偏好
PUT /api/v1/users/me/profile
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "preferCategory": [{"cat": "3C", "weight": 0.8}],
  "priceRange":     {"min": 500, "max": 5000},
  "qualityLevel":   2,
  "preferPlatform": ["jd", "taobao"]
}
```

### 6.4 服务间内部接口（gRPC）

```protobuf
// intent-service proto
syntax = "proto3";
package intent;

service IntentService {
  rpc Analyze(AnalyzeRequest) returns (AnalyzeResponse);
}

message AnalyzeRequest {
  string session_id = 1;
  string content    = 2;
  int32  msg_type   = 3;
  string image_url  = 4;
}

message AnalyzeResponse {
  string category    = 1;
  double min_price   = 2;
  double max_price   = 3;
  string use_case    = 4;
  repeated string keywords = 5;
  bool   confirmed   = 6;
  string intent_json = 7;
}
```

---

## 7. Docker + K8s 部署方案

### 7.1 Dockerfile 规范（以 Java 服务为例）

```dockerfile
# user-service/Dockerfile
# 多阶段构建
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline -q
COPY src ./src
RUN mvn package -DskipTests -q

FROM eclipse-temurin:17-jre-alpine AS runtime
LABEL maintainer="ilbuy-team"
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /build/target/user-service-*.jar app.jar
RUN chown -R appuser:appgroup /app
USER appuser
EXPOSE 8020
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8020/actuator/health | grep -q '"status":"UP"'
ENTRYPOINT ["java", \
  "-XX:MaxRAMPercentage=75.0", \
  "-XX:+UseG1GC", \
  "-Djava.security.egd=file:/dev/./urandom", \
  "-jar", "app.jar"]
```

```dockerfile
# intent-service/Dockerfile（Python FastAPI）
FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser
EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://localhost:8010/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "4"]
```

```dockerfile
# product-service/Dockerfile（Go）
FROM golang:1.21-alpine AS builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o product-service ./cmd/main.go

FROM scratch
COPY --from=builder /build/product-service /product-service
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
EXPOSE 8021
HEALTHCHECK --interval=30s CMD ["/product-service", "health"]
ENTRYPOINT ["/product-service"]
```

### 7.2 Kubernetes 部署配置

#### Namespace 规划

```yaml
# namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ilbuy-prod
  labels:
    env: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: ilbuy-infra
  labels:
    env: infrastructure
```

#### 服务部署示例（user-service）

```yaml
# user-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
  namespace: ilbuy-prod
  labels:
    app: user-service
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: user-service
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port:   "8020"
        prometheus.io/path:   "/actuator/prometheus"
    spec:
      serviceAccountName: ilbuy-service-account
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: user-service
                topologyKey: kubernetes.io/hostname
      containers:
        - name: user-service
          image: harbor.ilbuy.internal/ilbuy/user-service:1.0.0
          ports:
            - containerPort: 8020
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: "prod"
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: redis-secret
                  key: password
          resources:
            requests:
              cpu:    "500m"
              memory: "512Mi"
            limits:
              cpu:    "2000m"
              memory: "2Gi"
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8020
            initialDelaySeconds: 20
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8020
            initialDelaySeconds: 40
            periodSeconds: 15
            failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: user-service
  namespace: ilbuy-prod
spec:
  selector:
    app: user-service
  ports:
    - port: 8020
      targetPort: 8020
  type: ClusterIP
---
# 水平自动扩缩容
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: user-service-hpa
  namespace: ilbuy-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

#### AI 服务部署示例（intent-service，GPU 场景）

```yaml
# intent-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: intent-service
  namespace: ilbuy-prod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: intent-service
  template:
    metadata:
      labels:
        app: intent-service
    spec:
      containers:
        - name: intent-service
          image: harbor.ilbuy.internal/ilbuy/intent-service:1.0.0
          ports:
            - containerPort: 8010
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: ai-secrets
                  key: openai-key
            - name: MODEL_NAME
              value: "gpt-4o"
          resources:
            requests:
              cpu:    "1000m"
              memory: "2Gi"
            limits:
              cpu:    "4000m"
              memory: "8Gi"
          readinessProbe:
            httpGet:
              path: /health
              port: 8010
            initialDelaySeconds: 30
```

#### Ingress 配置

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ilbuy-ingress
  namespace: ilbuy-prod
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - api.ilbuy.com
      secretName: ilbuy-tls
  rules:
    - host: api.ilbuy.com
      http:
        paths:
          - path: /api/v1/auth
            pathType: Prefix
            backend:
              service:
                name: auth-service
                port:
                  number: 8001
          - path: /api/v1/dialog
            pathType: Prefix
            backend:
              service:
                name: dialog-service
                port:
                  number: 8013
          - path: /api/v1/products
            pathType: Prefix
            backend:
              service:
                name: product-service
                port:
                  number: 8021
          - path: /api/v1/orders
            pathType: Prefix
            backend:
              service:
                name: order-service
                port:
                  number: 8022
          - path: /api/v1/users
            pathType: Prefix
            backend:
              service:
                name: user-service
                port:
                  number: 8020
```

#### ConfigMap 与 Secret 管理

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ilbuy-config
  namespace: ilbuy-prod
data:
  NACOS_SERVER: "nacos.ilbuy-infra:8848"
  REDIS_HOST:   "redis-cluster.ilbuy-infra"
  REDIS_PORT:   "6379"
  ES_HOST:      "elasticsearch.ilbuy-infra:9200"
  RABBITMQ_HOST: "rabbitmq.ilbuy-infra"
  LOG_LEVEL:    "INFO"
---
# secret 由 Vault 动态注入，示例结构
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
  namespace: ilbuy-prod
type: Opaque
data:
  host:     <base64>
  password: <base64>
```

#### 存储（MySQL 主从 StatefulSet）

```yaml
# mysql-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: ilbuy-infra
spec:
  serviceName: mysql
  replicas: 3          # 1主2从
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
        - name: mysql
          image: mysql:8.0
          ports:
            - containerPort: 3306
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-root-secret
                  key: password
          resources:
            requests:
              cpu:    "2000m"
              memory: "4Gi"
            limits:
              cpu:    "4000m"
              memory: "8Gi"
          volumeMounts:
            - name: mysql-data
              mountPath: /var/lib/mysql
  volumeClaimTemplates:
    - metadata:
        name: mysql-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: "ssd-storage"
        resources:
          requests:
            storage: 500Gi
```

### 7.3 ArgoCD GitOps 配置

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ilbuy-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://gitlab.ilbuy.internal/ilbuy/k8s-manifests.git
    targetRevision: main
    path: overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: ilbuy-prod
  syncPolicy:
    automated:
      prune:    true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - RespectIgnoreDifferences=true
```

### 7.4 监控告警配置

```yaml
# prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ilbuy-alerts
  namespace: ilbuy-prod
spec:
  groups:
    - name: ilbuy.api
      rules:
        - alert: HighErrorRate
          expr: |
            rate(http_requests_total{status=~"5.."}[5m])
            / rate(http_requests_total[5m]) > 0.05
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "服务错误率超过5%: {{ $labels.service }}"

        - alert: HighLatency
          expr: |
            histogram_quantile(0.99,
              rate(http_request_duration_seconds_bucket[5m])
            ) > 2
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "P99 延迟超过 2s: {{ $labels.service }}"

        - alert: PodCrashLooping
          expr: |
            rate(kube_pod_container_status_restarts_total[15m]) > 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Pod 频繁重启: {{ $labels.pod }}"

        - alert: AIServiceDown
          expr: up{job="intent-service"} == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "AI 意图识别服务不可用"
```

### 7.5 资源规划总览

| 服务 | 副本数(最小) | CPU Request | Memory Request | 扩容上限 |
|------|-------------|-------------|----------------|---------|
| api-gateway(Kong) | 2 | 500m | 512Mi | 6 |
| auth-service | 2 | 500m | 512Mi | 6 |
| dialog-service | 3 | 500m | 512Mi | 10 |
| intent-service | 2 | 1000m | 2Gi | 8 |
| llm-service | 2 | 1000m | 2Gi | 6 |
| decision-service | 2 | 1000m | 2Gi | 6 |
| user-service | 3 | 500m | 512Mi | 10 |
| product-service | 3 | 1000m | 1Gi | 15 |
| order-service | 3 | 500m | 1Gi | 10 |
| config-service | 2 | 250m | 256Mi | 4 |
| notify-service | 2 | 250m | 256Mi | 6 |
| file-service | 2 | 250m | 512Mi | 4 |
| crawler-service | 2 | 500m | 1Gi | 4 |
| etl-service | 2 | 1000m | 2Gi | 6 |

### 7.6 发布流程

```
开发完成 → push to feature/* branch
         → GitLab CI Pipeline 触发
            ├── lint & unit test
            ├── SonarQube 代码扫描
            ├── docker build (multi-arch)
            └── push image to Harbor (tag: sha-xxxxxxx)

合并到 main branch
         → GitLab CI 触发 staging 部署
            ├── ArgoCD 同步 staging 环境
            ├── 集成测试 / 冒烟测试
            └── 通知测试团队

测试通过 → 手动触发 production 发布
         → ArgoCD 金丝雀发布 (5% → 20% → 100%)
         → Prometheus 监控错误率
         → 异常自动回滚
```

---

## 附录：项目目录结构建议

```
ilbuy/
├── gateway/                    # Kong 配置
│   └── kong.yaml
├── services/
│   ├── auth-service/           # Spring Boot
│   ├── user-service/           # Spring Boot
│   ├── order-service/          # Spring Boot
│   ├── config-service/         # Spring Boot
│   ├── product-service/        # Go
│   ├── file-service/           # Go
│   ├── dialog-service/         # Node.js
│   ├── notify-service/         # Node.js
│   ├── intent-service/         # Python/FastAPI
│   ├── llm-service/            # Python/FastAPI
│   ├── decision-service/       # Python/FastAPI
│   ├── crawler-service/        # Python/Scrapy
│   └── etl-service/            # Python
├── k8s-manifests/              # K8s YAML
│   ├── base/                   # 基础配置
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── monitoring/
│   ├── prometheus-rules/
│   ├── grafana-dashboards/
│   └── alert-templates/
├── scripts/
│   ├── db-migrations/          # Flyway/Liquibase
│   └── deploy/
└── docs/
    └── api/                    # OpenAPI 3.0 规范文件
```

---

*文档版本：v1.0 | 架构师：ILbuy 技术团队 | 最后更新：2026-03-05*
