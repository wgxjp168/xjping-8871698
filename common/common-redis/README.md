# common-redis - Redis封装组件

## 功能概述

| 模块 | 说明 |
|------|------|
| `RedisAutoConfiguration` | 自定义序列化（Key=String，Value=JSON）|
| `RedisUtils` | String/Hash/Set/ZSet/List操作 + Lua限流 |
| `DistributedLock` | 基于Redisson的分布式锁（含回调方式）|

## 配置说明

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
      password: ilbuy@2024
      database: 0
      lettuce:
        pool:
          max-active: 20
          max-wait: -1ms
          max-idle: 10
          min-idle: 5

# Redisson配置（分布式锁）
spring:
  redisson:
    file: classpath:redisson.yaml
```

`redisson.yaml`（单机模式）:
```yaml
singleServerConfig:
  address: "redis://localhost:6379"
  password: "ilbuy@2024"
  database: 0
  connectionMinimumIdleSize: 5
  connectionPoolSize: 20
```

## 使用示例

**1. 缓存操作**
```java
@Autowired
private RedisUtils redisUtils;

// 设置缓存（30分钟）
redisUtils.set("user:100001", userVO, 30, TimeUnit.MINUTES);

// 获取缓存
UserVO user = redisUtils.get("user:100001");

// 原子递增（用于决策次数统计）
long count = redisUtils.increment("decision:count:" + userId, 1);
```

**2. 限流（B端1000/min，C端100/min）**
```java
// B2B接口限流：1000次/分钟
String key = CommonConstants.RATE_LIMIT_B_PREFIX + clientIp;
boolean allowed = redisUtils.isAllowed(key, 1000, 60_000);
if (!allowed) {
    throw new BizException(ResultCode.TOO_MANY_REQUESTS);
}

// B2C接口限流：100次/分钟/用户
String key = CommonConstants.RATE_LIMIT_C_PREFIX + userId;
boolean allowed = redisUtils.isAllowed(key, 100, 60_000);
```

**3. 分布式锁（防重复提交）**
```java
@Autowired
private DistributedLock distributedLock;

// 采购决策防重（30秒内同一用户只能有一个决策在进行）
DecisionResult result = distributedLock.lockWithResult(
    "decision:lock:" + userId,
    30,  // 锁持有30秒
    () -> aiDecisionService.process(request)
);
if (result == null) {
    throw new BizException(ResultCode.DECISION_PROCESSING);
}
```
