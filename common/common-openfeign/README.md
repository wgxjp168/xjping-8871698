# common-openfeign - 微服务调用组件

## 功能概述

| 模块 | 说明 |
|------|------|
| `FeignAutoConfiguration` | 全局超时/重试/日志/拦截器配置 |
| `FeignRequestInterceptor` | 自动传递 UserId/UserType/TraceId/InnerCall Header |
| `FeignErrorDecoder` | 将下游4xx/5xx响应解码为BizException |
| `BaseFallbackFactory` | 熔断降级基类，提供统一降级日志和响应 |

## 超时配置

| 参数 | 值 | 说明 |
|------|----|------|
| 连接超时 | 5s | 建立TCP连接超时 |
| 读取超时 | 30s | 等待响应超时（AI决策接口最多30s）|
| 重试次数 | 3次 | 仅对网络异常（IOException）重试 |

## 熔断配置（application.yml）

```yaml
resilience4j:
  circuitbreaker:
    instances:
      # 用户服务熔断配置
      user-svc:
        failure-rate-threshold: 50        # 失败率>50%触发熔断
        wait-duration-in-open-state: 30s  # 熔断开启后30s尝试半开
        sliding-window-size: 10           # 滑动窗口10次请求
        minimum-number-of-calls: 5        # 最少5次请求才统计
  timelimiter:
    instances:
      user-svc:
        timeout-duration: 10s
```

## 使用示例

**1. 定义 Feign 客户端**
```java
@FeignClient(
    name = "ilbuy-user-svc",
    fallbackFactory = UserFeignFallbackFactory.class
)
public interface UserFeignClient {
    @GetMapping("/api/v1/users/{userId}")
    Result<UserVO> getUserInfo(@PathVariable Long userId);
}
```

**2. 实现降级工厂**
```java
@Component
public class UserFeignFallbackFactory
        extends BaseFallbackFactory<UserFeignClient>
        implements FallbackFactory<UserFeignClient> {

    @Override
    public UserFeignClient create(Throwable cause) {
        return new UserFeignClient() {
            @Override
            public Result<UserVO> getUserInfo(Long userId) {
                return fallbackResult(cause, "getUserInfo");
            }
        };
    }
}
```

**3. 启用 Feign 客户端**
```java
@SpringBootApplication
@EnableFeignClients(basePackages = "com.ilbuy")
public class ServiceApplication { ... }
```

## 注意事项

- POST接口不建议使用自动重试（可能导致重复提交）
- 内部服务调用自动携带 `X-Inner-Call` Header，下游跳过JWT校验
- 熔断状态下立即返回降级响应，不等待超时（快速失败）
