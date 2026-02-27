# ILbuy Config Repo

Spring Cloud Config 集中配置仓库，存放所有微服务的配置文件。

## 配置文件命名规范

```
{application}-{profile}.yml
```

- `application.yml` — 公共配置（所有服务共享）
- `ilbuy-access-layer-{profile}.yml` — API网关配置
- `ilbuy-ai-decision-hub-{profile}.yml` — AI决策中心配置
- `ilbuy-business-logic-{profile}.yml` — 业务逻辑层配置

## Profile

- `dev` — 开发环境
- `prod` — 生产环境

## 使用方式

Spring Cloud Config Server 指向此目录即可加载配置：

```yaml
spring:
  cloud:
    config:
      server:
        native:
          search-locations: file:///workspace/ilbuy-microservices/config-repo
```
