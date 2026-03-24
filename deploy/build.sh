#!/bin/bash
# 惠东县区域公卫体检集中系统 - 一键构建并部署
# 使用方法: chmod +x build.sh && ./build.sh

set -e
cd "$(dirname "$0")/.."

echo "======================================================"
echo " 惠东县区域公卫体检集中系统 - 构建部署脚本"
echo "======================================================"

# 1. Maven 构建所有服务
echo "[1/3] Maven 构建所有微服务..."
mvn clean package -DskipTests -pl physical-common,physical-auth,physical-dr,physical-core,physical-sync,physical-urine,physical-gateway -am

# 2. 构建Docker镜像
echo "[2/3] 构建Docker镜像..."
SERVICES=("physical-gateway" "physical-auth" "physical-dr" "physical-core" "physical-sync" "physical-urine")
for svc in "${SERVICES[@]}"; do
    echo "  => 构建 $svc ..."
    docker build --build-arg SERVICE_NAME=$svc -t physical/${svc#physical-}:1.0.0 -f deploy/Dockerfile.service .
done
echo "  => 构建前端 physical-web ..."
docker build -t physical/web:1.0.0 -f deploy/Dockerfile.web .

# 3. 启动服务
echo "[3/3] 启动所有服务..."
cd deploy
docker-compose down --remove-orphans
docker-compose up -d

echo ""
echo "======================================================"
echo " 部署完成！"
echo " 网页端访问地址: http://服务器IP:8888/web"
echo " API文档(auth): http://服务器IP:9005/doc.html"
echo " API文档(dr):   http://服务器IP:9011/doc.html"
echo " API文档(core): http://服务器IP:9001/doc.html"
echo " 默认管理员账号: admin / Admin@2024"
echo "======================================================"
