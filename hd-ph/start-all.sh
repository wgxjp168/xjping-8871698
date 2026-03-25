#!/bin/bash
# 惠东县区域公卫体检集中系统 - 一键启动脚本
# 依赖: JDK 11+, Maven 3.6+, MySQL 8, Redis

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "======================================"
echo " 惠东县区域公卫体检集中系统 启动中..."
echo "======================================"

# 检查 MySQL
echo "[1/7] 检查 MySQL 连接..."
if ! mysql -u root -proot123 -e "SELECT 1" &>/dev/null; then
  echo "错误: 无法连接到 MySQL (localhost:3306, root/root123)"
  echo "请确认 MySQL 已启动并且账号密码正确"
  exit 1
fi

# 初始化数据库
echo "[2/7] 初始化数据库..."
mysql -u root -proot123 < "$PROJECT_DIR/sql/hd_public_health.sql"
echo "数据库初始化完成"

# Maven 编译
echo "[3/7] 编译项目 (Maven)..."
cd "$PROJECT_DIR"
mvn clean package -DskipTests -q
echo "编译完成"

# 启动各服务
start_service() {
  local name=$1
  local jar=$2
  local port=$3
  echo "启动 $name (端口 $port)..."
  nohup java -jar "$jar" > "$LOG_DIR/$name.log" 2>&1 &
  echo $! > "$LOG_DIR/$name.pid"
  echo "$name 已启动 (PID: $!)"
  sleep 2
}

echo "[4/7] 启动 hd-gateway (端口 9090)..."
start_service "hd-gateway" "$PROJECT_DIR/hd-gateway/target/hd-gateway-1.0.0.jar" 9090

echo "[5/7] 启动 hd-auth (端口 8001)..."
start_service "hd-auth" "$PROJECT_DIR/hd-auth/target/hd-auth-1.0.0.jar" 8001

echo "[6/7] 启动 hd-resident (端口 8002)..."
start_service "hd-resident" "$PROJECT_DIR/hd-resident/target/hd-resident-1.0.0.jar" 8002

echo "启动 hd-device (端口 8003, ASTM TCP 7100)..."
start_service "hd-device" "$PROJECT_DIR/hd-device/target/hd-device-1.0.0.jar" 8003

echo "启动 hd-check (端口 8004)..."
start_service "hd-check" "$PROJECT_DIR/hd-check/target/hd-check-1.0.0.jar" 8004

echo "[7/7] 启动 hd-dr (端口 8005)..."
start_service "hd-dr" "$PROJECT_DIR/hd-dr/target/hd-dr-1.0.0.jar" 8005

echo ""
echo "======================================"
echo " 所有后端服务启动完成！"
echo "======================================"
echo ""
echo " 前端启动方法:"
echo "   cd $PROJECT_DIR/hd-frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo " 访问地址:"
echo "   前端:    http://localhost:3000"
echo "   网关:    http://localhost:9090"
echo ""
echo " 测试账号:  admin / hd2024"
echo "           doctor01 / hd2024"
echo "           nurse01 / hd2024"
echo ""
echo " API文档:"
echo "   认证:   http://localhost:8001/doc.html"
echo "   居民:   http://localhost:8002/doc.html"
echo "   设备:   http://localhost:8003/doc.html"
echo "   体检:   http://localhost:8004/doc.html"
echo "   DR:     http://localhost:8005/doc.html"
echo ""
echo " 日志目录: $LOG_DIR"
echo "======================================"
