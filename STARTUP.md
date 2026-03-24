# 健康检查系统 - 启动指南

## 项目架构

```
xjping-8871698/
├── sql/                    # 数据库脚本
│   └── health_check.sql
├── health-backend/         # Spring Boot 后端
│   ├── pom.xml
│   └── src/
└── health-frontend/        # Vue 3 前端
    ├── package.json
    └── src/
```

## 技术栈

| 层级     | 技术                                        |
|--------|-------------------------------------------|
| 后端框架   | Spring Boot 2.7 + Spring Security + JWT   |
| ORM    | MyBatis Plus 3.5                          |
| 数据库    | MySQL 8.0                                 |
| API文档  | Knife4j (Swagger UI)                      |
| 前端框架   | Vue 3 + Vite                              |
| UI组件库  | Element Plus                              |
| 图表     | ECharts 5                                 |
| 状态管理   | Pinia                                     |

## 环境要求

- JDK 11+
- Maven 3.8+
- MySQL 8.0+
- Node.js 18+

## 快速启动

### 1. 初始化数据库

```bash
mysql -u root -p < sql/health_check.sql
```

### 2. 启动后端

修改 `health-backend/src/main/resources/application.yml` 中的数据库配置：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/health_check?...
    username: root
    password: your_password
```

```bash
cd health-backend
mvn spring-boot:run
```

后端启动后访问：
- API接口：http://localhost:8080/api
- 接口文档：http://localhost:8080/api/doc.html

### 3. 启动前端

```bash
cd health-frontend
npm install
npm run dev
```

前端启动后访问：http://localhost:3000

## 默认账号

| 用户名      | 密码         | 角色   |
|----------|------------|------|
| admin    | health123  | 管理员  |
| doctor01 | health123  | 医生   |
| doctor02 | health123  | 医生   |
| user01   | health123  | 普通用户 |

## 主要功能模块

### 1. 体检管理
- 体检单列表、创建、详情查看
- 检查结果录入（手动/设备采集）
- 检查项目管理
- 套餐管理

### 2. 诊断管理
- 诊断报告创建、编辑
- 报告确认、发布流程
- 健康评分、风险等级评估

### 3. 设备集成
- 设备信息管理（增删改查）
- 设备在线状态监控（心跳检测）
- 设备数据上报接口
- 实时设备监控面板

### 4. 系统管理
- 用户管理（增删改查、角色分配）
- 科室管理（树形结构）
- 操作日志查询

## 设备集成接口

### 心跳上报
```
POST /api/device/heartbeat/{deviceCode}
```

### 数据上报
```
POST /api/device/upload/{deviceCode}
Body: {
  "itemCode": "CI004",
  "value": "128",
  "unit": "mmHg",
  "orderId": 1,
  "patientId": 4
}
```

## 生产部署

```bash
# 后端打包
cd health-backend
mvn clean package -DskipTests
java -jar target/health-backend-1.0.0.jar

# 前端打包
cd health-frontend
npm run build
# 将 dist/ 目录部署到 Nginx
```

### Nginx 配置参考

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /var/www/health-frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
