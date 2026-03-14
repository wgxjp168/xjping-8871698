#!/bin/bash
# =============================================
# ILbuy AI采购决策平台 - 本地开发环境一键启动
# =============================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "================================================"
echo "  我来购(ILbuy) AI采购决策平台 - 本地开发启动"
echo "================================================"

# 检查 Docker
if ! command -v docker &>/dev/null; then
    echo "[ERROR] Docker 未安装，请先安装 Docker 25+"
    exit 1
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
    echo "[ERROR] Docker Compose 未安装"
    exit 1
fi

# 创建 .env 文件（如果不存在）
if [ ! -f ".env" ]; then
    echo "[INFO] 创建 .env 配置文件..."
    cat > .env << 'EOF'
# LLM API Keys（根据实际情况填写）
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# 数据库密码
MYSQL_PASSWORD=ilbuy@2024
REDIS_PASSWORD=ilbuy@2024

# JWT密钥（生产环境请修改）
JWT_SECRET=ilbuy-secret-key-must-be-at-least-32-chars-long

# 环境
APP_ENV=dev
EOF
    echo "[INFO] .env 文件已创建，请根据需要修改 API Key"
fi

# 启动基础中间件
echo ""
echo "[STEP 1] 启动基础中间件（MySQL/Redis/ES/RabbitMQ/MinIO/Nacos）..."
docker compose up -d mysql redis elasticsearch rabbitmq minio nacos

echo "[INFO] 等待中间件初始化（30秒）..."
sleep 30

# 检查 MySQL
echo "[STEP 2] 检查数据库连接..."
docker compose exec -T mysql mysqladmin ping -h localhost -u root -pilbuy@2024 --silent \
    && echo "[OK] MySQL 就绪" || echo "[WARN] MySQL 未就绪，可能需要更多时间"

# 启动监控组件
echo ""
echo "[STEP 3] 启动监控组件（Prometheus/Grafana/Jaeger）..."
docker compose up -d prometheus grafana jaeger kibana

echo ""
echo "================================================"
echo "  本地环境启动完成！"
echo ""
echo "  服务访问地址:"
echo "  - Nacos:       http://localhost:8848/nacos  (nacos/nacos)"
echo "  - MySQL:       localhost:3306  (root/ilbuy@2024)"
echo "  - Redis:       localhost:6379"
echo "  - Elasticsearch: http://localhost:9200"
echo "  - Kibana:      http://localhost:5601"
echo "  - RabbitMQ:    http://localhost:15672  (ilbuy/ilbuy@2024)"
echo "  - MinIO:       http://localhost:9001  (ilbuy/ilbuy@2024)"
echo "  - Prometheus:  http://localhost:9090"
echo "  - Grafana:     http://localhost:3000  (admin/ilbuy@2024)"
echo "  - Jaeger:      http://localhost:16686"
echo "================================================"
echo ""
echo "  下一步: 启动微服务"
echo "  docker compose up -d l1-gateway l2-intent-svc l2-llm-svc"
echo "================================================"
