#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"

echo "正在停止所有服务..."
for svc in hd-gateway hd-auth hd-resident hd-device hd-check hd-dr; do
  PID_FILE="$LOG_DIR/$svc.pid"
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID"
      echo "已停止 $svc (PID: $PID)"
    fi
    rm -f "$PID_FILE"
  fi
done
echo "所有服务已停止"
