# common-core - 公共核心组件

## 功能概述

| 模块 | 包路径 | 说明 |
|------|--------|------|
| 响应结果 | `result/` | `Result<T>` 统一响应、`PageResult<T>` 分页结果 |
| 错误码 | `result/ResultCode` | 全局错误码枚举（通用/用户/决策/支付/报告）|
| 业务异常 | `exception/BizException` | 业务异常基类，携带错误码 |
| 全局异常处理 | `exception/GlobalExceptionHandler` | `@RestControllerAdvice` 统一处理 |
| 枚举 | `enums/` | UserTypeEnum/BrandStatusEnum/StatusEnum/MemberLevelEnum |
| 常量 | `constant/CommonConstants` | HTTP Header/缓存Key/限流配置/正则 |
| AES工具 | `utils/AesUtils` | AES-256-GCM 加解密（随机IV，防重放）|
| JSON工具 | `utils/JsonUtils` | Jackson封装，支持泛型/List/Map |
| 日期工具 | `utils/DateUtils` | LocalDateTime操作，时区统一Asia/Shanghai |
| ID生成器 | `utils/IdGenerator` | 雪花算法，线程安全，支持并发 |
| 校验工具 | `utils/ValidateUtils` | 手机号/邮箱/信用代码/密码校验+脱敏 |

## 快速开始

### 添加依赖
```xml
<dependency>
    <groupId>com.ilbuy</groupId>
    <artifactId>common-core</artifactId>
    <version>1.0.0-SNAPSHOT</version>
</dependency>
```

### 使用示例

**1. Controller 返回统一响应**
```java
// 成功
return Result.ok(userVO);

// 失败（使用枚举）
return Result.fail(ResultCode.USER_NOT_FOUND);

// 分页
return Result.ok(PageResult.of(records, total, current, size));
```

**2. 抛出业务异常（由GlobalExceptionHandler自动捕获）**
```java
// 推荐使用枚举
throw new BizException(ResultCode.USER_NOT_FOUND);

// 静态工厂方法
throw BizException.notFound("用户");
throw BizException.forbidden();
```

**3. AES加密敏感数据**
```java
String key = AesUtils.generateKey(); // 生成密钥（存入Vault）
String encrypted = AesUtils.encrypt(phone, key);
String decrypted = AesUtils.decrypt(encrypted, key);
```

**4. ID生成**
```java
long id = IdGenerator.nextId();     // 雪花算法Long ID
String strId = IdGenerator.nextStrId();  // 字符串ID
```

## 运行测试
```bash
cd common/common-core
mvn test
```
