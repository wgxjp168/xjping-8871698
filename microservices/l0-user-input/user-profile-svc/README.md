# user-profile-svc — 用户画像服务

## 概述

L0 用户输入层画像管理服务，存储并提供用户历史购物偏好、预算区间、购物场景等画像信息，
采用 MySQL 持久化 + Redis 缓存（Cache-Aside 模式，TTL 30min）。

| 属性 | 值 |
|------|-----|
| 服务名 | `user-profile-svc` |
| 端口 | **8001** |
| 层级 | L0 用户输入层 |
| Spring Boot | 3.2.3 |

## 业务能力

| 能力 | 说明 |
|------|------|
| 画像查询 | MySQL → Redis（Cache-Aside），缓存 TTL 30min，滑动续期 |
| 画像更新 | PATCH 语义，仅更新非null字段，延迟双删缓存 |
| 偏好权重 | 行为驱动增量更新，按维度（品类/品牌/平台/场景）管理，上限100 |
| 画像初始化 | 用户注册后由 auth-svc 调用，幂等保证 |
| 完整度评分 | 0-100分，字段填充越完整得分越高 |

## 核心接口

```
GET  /api/v0/profiles/me              - 获取当前用户完整画像
GET  /api/v0/profiles/{userId}        - 获取指定用户画像（管理员）
GET  /api/v0/profiles/{userId}/summary - 获取画像摘要（供multimodal-input-svc Feign调用）
PUT  /api/v0/profiles/me              - 更新画像（PATCH语义）
POST /api/v0/profiles/{userId}/preference - 行为驱动偏好权重更新（L5业务层调用）
POST /api/v0/profiles/{userId}/init   - 初始化新用户画像（auth-svc调用）
GET  /actuator/health                 - K8s探针
GET  /swagger-ui.html                 - Swagger文档
```

## 数据库建表 SQL

```sql
CREATE TABLE `user_profile` (
  `user_id`               BIGINT       NOT NULL,
  `nickname`              VARCHAR(64),
  `gender`                TINYINT      DEFAULT 0,
  `age_group`             VARCHAR(20),
  `city`                  VARCHAR(50),
  `budget_min`            DECIMAL(10,2),
  `budget_max`            DECIMAL(10,2),
  `avg_spend_min`         DECIMAL(10,2),
  `avg_spend_max`         DECIMAL(10,2),
  `preferred_categories`  VARCHAR(500),
  `scene_tags`            VARCHAR(200),
  `preferred_brands`      VARCHAR(500),
  `preferred_platforms`   VARCHAR(200),
  `purchase_frequency`    VARCHAR(20),
  `eco_friendly`          TINYINT(1)   DEFAULT 0,
  `profile_score`         INT          DEFAULT 0,
  `version`               INT          DEFAULT 0,
  `created_at`            DATETIME     NOT NULL,
  `updated_at`            DATETIME     NOT NULL,
  `deleted`               TINYINT      DEFAULT 0,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `user_preference` (
  `id`              BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`         BIGINT       NOT NULL,
  `dimension`       VARCHAR(30)  NOT NULL,
  `dimension_value` VARCHAR(100) NOT NULL,
  `weight`          INT          DEFAULT 50,
  `source`          VARCHAR(20)  DEFAULT 'inferred',
  `trigger_count`   INT          DEFAULT 0,
  `last_triggered_at` DATETIME,
  `created_at`      DATETIME     NOT NULL,
  `updated_at`      DATETIME     NOT NULL,
  `deleted`         TINYINT      DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_user_dimension` (`user_id`, `dimension`, `deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## 本地启动

```bash
# 前置：MySQL + Redis + Nacos 已启动，数据库已建表
cd microservices/l0-user-input/user-profile-svc
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 验证
curl http://localhost:8001/actuator/health

# 初始化用户画像（需先获取 INTERNAL 角色 JWT）
curl -X POST "http://localhost:8001/api/v0/profiles/1001/init?nickname=张三" \
  -H "Authorization: Bearer $TOKEN"

# 获取画像摘要
curl "http://localhost:8001/api/v0/profiles/1001/summary" \
  -H "Authorization: Bearer $TOKEN"
```

## 容器部署

```bash
docker build -t user-profile-svc:1.0.0 .
docker run -d \
  -p 8001:8001 \
  -e SPRING_PROFILES_ACTIVE=dev \
  -e DB_HOST=host.docker.internal \
  -e DB_USERNAME=root \
  -e DB_PASSWORD=root123 \
  -e REDIS_HOST=host.docker.internal \
  --name user-profile-svc \
  user-profile-svc:1.0.0
```

## K8s 部署

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl -n ilbuy-prod get pods -l app=user-profile-svc
```

## 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `JWT_SECRET` | ✅ Prod | `ilbuy-jwt-secret...` | JWT签名密钥 |
| `DB_HOST` | ✅ Prod | `mysql-cluster` | MySQL主机 |
| `DB_USERNAME` | ✅ Prod | - | MySQL用户名 |
| `DB_PASSWORD` | ✅ Prod | - | MySQL密码 |
| `REDIS_HOST` | ✅ Prod | `redis-cluster` | Redis主机 |
| `REDIS_PASSWORD` | ✅ Prod | - | Redis密码 |
| `NACOS_ADDR` | ✅ Prod | `nacos:8848` | Nacos地址 |

## 运行单元测试

```bash
mvn test
```
