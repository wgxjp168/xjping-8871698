# format-output-svc — L6 多格式输出服务

**技术栈**: Java 17 / Spring Boot 3.2 / Thymeleaf / Flying Saucer / Apache POI / MinIO
**端口**: 8062
**职责**: 接收来自report-generator-svc的结构化报告，渲染为HTML/PDF/Excel/JSON四种格式，存储至MinIO对象存储，并触发channel-delivery-svc进行多渠道交付。

---

## 格式输出能力

| 格式 | 技术 | 特点 |
|-----|------|------|
| HTML | Thymeleaf + Chart.js | 交互式报告，含可视化图表，支持在线浏览 |
| PDF | Flying Saucer + OpenPDF | 可打印版本，支持CJK中文字体，A4格式 |
| Excel | Apache POI | 多Sheet数据报告，支持图表数据导出，适合数据分析 |
| JSON | Spring MVC | RESTful API直接访问，适合系统集成 |

---

## 目录结构

```
format-output-svc/
├── src/main/java/com/ilbuy/format/
│   ├── FormatOutputApplication.java
│   ├── api/
│   │   └── FormatJobController.java    # REST API
│   ├── client/
│   │   └── ChannelDeliveryClient.java  # 调用channel-delivery-svc
│   ├── config/
│   │   ├── AsyncConfig.java
│   │   ├── MinioConfig.java
│   │   └── SecurityConfig.java
│   ├── exception/
│   ├── model/
│   │   ├── dto/
│   │   ├── entity/FormatJob.java
│   │   └── enums/
│   ├── repository/FormatJobRepository.java
│   ├── service/
│   │   ├── FormatOutputService.java     # 主编排服务
│   │   └── formatter/
│   │       ├── HtmlFormatter.java       # Thymeleaf HTML渲染
│   │       ├── PdfFormatter.java        # Flying Saucer PDF生成
│   │       └── ExcelFormatter.java      # Apache POI Excel生成
│   └── storage/
│       └── MinioStorageService.java     # MinIO对象存储
├── src/main/resources/
│   ├── application.yml
│   ├── application-prod.yml
│   ├── templates/report.html           # 交互式HTML模板
│   └── db/migration/V1__init_format_output.sql
├── src/test/
├── k8s/
├── Dockerfile
└── README.md
```

---

## 数据流

```
report-generator-svc
    │ POST /internal/v1/format-jobs
    ▼
FormatJobController → FormatOutputService
    │
    ├──→ PdfFormatter   → PDF bytes → MinIO (ilbuy-reports-pdf)
    ├──→ ExcelFormatter → XLSX bytes → MinIO (ilbuy-reports-excel)
    ├──→ HtmlFormatter  → HTML bytes → MinIO (ilbuy-reports-html)
    │
    ▼ POST /internal/v1/deliveries
channel-delivery-svc (port 8063)
```

---

## 本地开发启动

### 前置依赖

```bash
# PostgreSQL + MinIO
docker run -d --name minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  quay.io/minio/minio server /data --console-address ":9001"

docker run -d --name postgres-l6 -p 5432:5432 \
  -e POSTGRES_DB=ilbuy_l6 -e POSTGRES_USER=ilbuy -e POSTGRES_PASSWORD=ilbuy123 \
  postgres:15-alpine
```

### 编译运行

```bash
mvn clean package -DskipTests
java -jar target/format-output-svc-1.0.0.jar --spring.profiles.active=dev
```

### 测试

```bash
mvn test
```

---

## Docker

```bash
docker build -t ilbuy/format-output-svc:latest .
docker run -p 8062:8062 \
  -e DB_URL=jdbc:postgresql://host.docker.internal:5432/ilbuy_l6 \
  -e MINIO_ENDPOINT=http://host.docker.internal:9000 \
  ilbuy/format-output-svc:latest
```

---

## K8s部署

```bash
kubectl apply -f k8s/deployment.yaml
kubectl rollout status deployment/format-output-svc -n ilbuy-l6
```

---

## API接口

| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | /internal/v1/format-jobs | 提交格式化任务 |
| GET | /internal/v1/format-jobs/{formatJobNo} | 查询任务状态和文件URL |
| GET | /internal/v1/format-jobs/by-report/{l5ReportNo}/json | 获取JSON格式输出 |
| POST | /internal/v1/format-jobs/{formatJobNo}/monetize-hook | L7商业变现层接口预留 |
| POST | /internal/v1/format-jobs/{formatJobNo}/feedback-hook | L8反馈优化层接口预留 |
