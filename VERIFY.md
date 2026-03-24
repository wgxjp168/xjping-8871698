# 验收检查指南

## 端口分配（无冲突）

| 服务 | 端口 | 说明 |
|------|------|------|
| physical-gateway | **8888** | 对外唯一入口 |
| physical-core | **9001** | 核心业务 |
| physical-sync | **9004** | 同步服务 |
| physical-auth | **9005** | 权限服务 [NEW] |
| physical-urine | **9010** | 尿机服务 |
| physical-dr | **9011** | DR服务 [NEW] |
| physical-web（nginx） | **80** | 网页端 |
| MySQL | **3306** | 数据库 |
| Redis | **6379** | 缓存 |

## 本地启动步骤

```bash
# 1. 启动基础设施
docker-compose -f deploy/docker-compose.yml up -d mysql redis

# 2. 等待MySQL就绪，初始化数据库
sleep 30
mysql -h 127.0.0.1 -uroot -pphysical@2024 < sql/init.sql

# 3. Maven构建（跳过测试快速构建）
mvn clean package -DskipTests

# 4. 分别启动各服务（或用IDE启动）
java -jar physical-auth/target/physical-auth-1.0.0.jar   --spring.profiles.active=dev &
java -jar physical-dr/target/physical-dr-1.0.0.jar       --spring.profiles.active=dev &
java -jar physical-core/target/physical-core-1.0.0.jar   --spring.profiles.active=dev &
java -jar physical-sync/target/physical-sync-1.0.0.jar   --spring.profiles.active=dev &
java -jar physical-urine/target/physical-urine-1.0.0.jar --spring.profiles.active=dev &
java -jar physical-gateway/target/physical-gateway-1.0.0.jar --spring.profiles.active=dev &

# 5. 前端开发模式
cd physical-web && npm install && npm run dev
```

## 健康检查验证

```bash
# 各服务 Actuator 健康端点
curl http://localhost:9005/actuator/health   # auth
curl http://localhost:9011/actuator/health   # dr
curl http://localhost:9001/actuator/health   # core
curl http://localhost:9004/actuator/health   # sync
curl http://localhost:9010/actuator/health   # urine
curl http://localhost:8888/actuator/health   # gateway

# Liveness/Readiness（K8s探针路径）
curl http://localhost:9005/actuator/health/liveness
curl http://localhost:9005/actuator/health/readiness
```

## 运行单元测试

```bash
# 运行全部测试
mvn test

# 运行指定模块测试
mvn test -pl physical-common
mvn test -pl physical-auth
mvn test -pl physical-dr
mvn test -pl physical-core

# 测试报告位置
# target/surefire-reports/*.txt
# target/site/surefire-report.html
```

## Docker 镜像构建验证

```bash
# 构建 Auth 服务镜像（从项目根目录执行）
docker build \
  --build-arg SERVICE_NAME=physical-auth \
  --build-arg SERVICE_PORT=9005 \
  -t physical/auth:1.0.0 \
  -f deploy/Dockerfile.service .

# 构建 DR 服务镜像
docker build \
  --build-arg SERVICE_NAME=physical-dr \
  --build-arg SERVICE_PORT=9011 \
  -t physical/dr:1.0.0 \
  -f deploy/Dockerfile.service .

# 构建前端镜像
docker build -t physical/web:1.0.0 -f deploy/Dockerfile.web .

# 验证镜像
docker images | grep physical
docker run --rm physical/auth:1.0.0 java -version
```

## K8s 部署验证

```bash
# 验证YAML语法
kubectl apply --dry-run=client -f k8s/namespace/namespace.yaml
kubectl apply --dry-run=client -f k8s/configmap/configmap.yaml
kubectl apply --dry-run=client -f k8s/auth/deployment.yaml
kubectl apply --dry-run=client -f k8s/dr/deployment.yaml

# 一键部署
chmod +x k8s/deploy-all.sh
./k8s/deploy-all.sh prod

# 检查Pod资源限制
kubectl describe pod -n physical-health -l app=physical-auth | grep -A5 "Limits\|Requests"

# 检查HPA状态
kubectl get hpa -n physical-health

# 检查探针配置
kubectl describe pod -n physical-health -l app=physical-dr | grep -A10 "Liveness\|Readiness"
```

## 核心业务接口冒烟测试

```bash
# 1. 登录获取Token
TOKEN=$(curl -s -X POST http://localhost:8888/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@2024","loginSource":"WEB"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

echo "TOKEN: $TOKEN"

# 2. 检查权限
curl -X POST http://localhost:8888/api/auth/check \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"docId":"ADMIN001","projectCode":"DR","operateType":"INPUT"}'

# 3. 注册DR开单（模拟县域回调）
curl -X POST http://localhost:8888/api/dr/register \
  -H 'Content-Type: application/json' \
  -d '{"drCode":"DR20240324TEST01","residentId":1,"residentName":"测试居民","examPart":"胸部正位"}'

# 4. DR扫码
curl -X POST http://localhost:8888/api/dr/scan \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"drCode":"DR20240324TEST01"}'
```

## K8s 资源限制汇总

| 服务 | CPU Request | CPU Limit | Mem Request | Mem Limit |
|------|------------|-----------|-------------|-----------|
| gateway | 100m | 500m | 256Mi | 512Mi |
| auth | 200m | 800m | 384Mi | 768Mi |
| dr | 100m | 500m | 256Mi | 512Mi |
| core | 200m | 1000m | 384Mi | 1Gi |
| sync | 50m | 300m | 128Mi | 384Mi |
| urine | 50m | 300m | 128Mi | 384Mi |
| web | 50m | 200m | 64Mi | 128Mi |
| mysql | 500m | 2000m | 1Gi | 2Gi |
| redis | 100m | 500m | 128Mi | 512Mi |

## 探针配置汇总

| 服务 | Liveness路径 | 初始延迟 | Readiness路径 | 初始延迟 |
|------|-------------|---------|--------------|---------|
| gateway | /actuator/health/liveness | 60s | /actuator/health/readiness | 30s |
| auth | /actuator/health/liveness | 90s | /actuator/health/readiness | 60s |
| dr | /actuator/health/liveness | 60s | /actuator/health/readiness | 40s |
| core | /actuator/health/liveness | 60s | /actuator/health/readiness | 40s |
| sync | /actuator/health/liveness | 60s | /actuator/health/readiness | 40s |
| urine | /actuator/health/liveness | 60s | /actuator/health/readiness | 40s |
| web | /health | 15s | /health | 10s |
