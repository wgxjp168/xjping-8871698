# common-mybatis - 数据库适配组件

## 功能概述

| 模块 | 说明 |
|------|------|
| `BaseEntity` | 公共字段（id/createTime/updateTime/deleted）|
| `MybatisPlusConfig` | 分页插件/乐观锁/防全表更新配置 |
| `MetaObjectHandlerImpl` | createTime/updateTime 自动填充 |
| `PageQuery` | 分页请求参数基类，提供 `toPage()` 转换 |

## 配置说明

```yaml
spring:
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://localhost:3306/ilbuy_main?useUnicode=true&characterEncoding=utf8
    username: root
    password: ilbuy@2024
    type: com.alibaba.druid.pool.DruidDataSource
    druid:
      initial-size: 5
      min-idle: 5
      max-active: 20
      max-wait: 60000

mybatis-plus:
  mapper-locations: classpath*:mapper/**/*.xml
  configuration:
    map-underscore-to-camel-case: true
    log-impl: org.apache.ibatis.logging.slf4j.Slf4jImpl
  global-config:
    db-config:
      logic-delete-field: deleted
      logic-delete-value: 1
      logic-not-delete-value: 0
```

## 使用示例

**1. 实体类继承 BaseEntity**
```java
@Data
@TableName("ilbuy_user")
public class User extends BaseEntity {
    private String username;
    private String phone;
    // id/createTime/updateTime/deleted 继承自BaseEntity
}
```

**2. 分页查询**
```java
// Controller接收分页参数
public Result<PageResult<UserVO>> list(PageQuery query) {
    IPage<User> page = userService.page(query.toPage(),
            Wrappers.lambdaQuery(User.class).eq(User::getStatus, 1));
    return Result.ok(PageQuery.toPageResult(page, UserVO::from));
}
```

**3. 防全表更新（生产安全）**
- 如果执行 `update table set ...` 没有 where 条件，会抛出 `MybatisException`
- 这是生产安全保障，防止误操作清空表

**4. 乐观锁使用**
```java
@Version  // 在实体类字段上加注解
private Integer version;
// MyBatis-Plus会自动在UPDATE时加上 version = version + 1 的条件
```
