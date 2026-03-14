# common-security - 安全组件

## 功能概述

| 模块 | 说明 |
|------|------|
| `JwtProperties` | JWT配置属性（密钥/有效期/黑名单开关）|
| `JwtTokenProvider` | JWT生成/解析/校验/黑名单/Refresh机制 |
| `JwtAuthenticationFilter` | 每次请求验证JWT，注入SecurityContext |
| `SecurityAutoConfiguration` | Spring Security无状态配置 |
| `LoginUser` | 登录用户信息（实现UserDetails）|
| `SecurityUtils` | 获取当前用户信息的工具类 |
| `AccessDeniedHandlerImpl` | 403 JSON响应处理 |
| `AuthenticationEntryPointImpl` | 401 JSON响应处理 |

## 配置说明

```yaml
ilbuy:
  security:
    jwt:
      secret: your-256-bit-secret-key-here  # 至少32位，生产用Vault注入
      expiration: 7200000          # Access Token有效期：2小时
      refresh-expiration: 604800000 # Refresh Token有效期：7天
      token-header: Authorization
      token-prefix: "Bearer "
      enable-blacklist: true       # 开启Token黑名单（登出立即失效）
```

## 使用示例

**1. Service层生成Token**
```java
@Autowired
private JwtTokenProvider jwtTokenProvider;

// 登录成功后生成Token对
JwtTokenProvider.TokenPair tokens = jwtTokenProvider.generateTokenPair(
    userId.toString(), "B2C", "FREE"
);
```

**2. Controller层获取当前用户**
```java
// 获取当前用户ID（未登录自动抛出UNAUTHORIZED）
Long userId = SecurityUtils.currentUserId();

// 获取完整用户信息
LoginUser user = SecurityUtils.currentUser();
boolean isB2B = user.isB2B();
```

**3. 方法级权限控制**
```java
@PreAuthorize("hasRole('B2B')")
public Result<?> b2bOnlyApi() { ... }

@PreAuthorize("hasRole('B2B') or hasRole('B2C')")
public Result<?> allUserApi() { ... }
```

**4. 白名单配置（无需认证）**

在 `JwtAuthenticationFilter.WHITE_LIST` 中添加路径，或在 `SecurityAutoConfiguration` 的 `permitAll()` 中配置。

## 安全设计

- JWT黑名单存储于Redis，TTL与Token剩余有效期一致
- 内部服务调用通过 `X-Inner-Call` Header跳过JWT校验
- BCrypt密码加密（12轮），不可逆
- Token即将过期时（<30min），响应头携带 `X-Token-About-Expire: true` 提示客户端刷新
