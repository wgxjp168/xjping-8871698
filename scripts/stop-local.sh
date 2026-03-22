#!/usr/bin/env bash
# 停止所有本地进程
PID_FILE="/tmp/ilbuy.pids"
if [ -f "$PID_FILE" ]; then
    while read -r pid name; do
        kill "$pid" 2>/dev/null && echo "停止 $name (PID $pid)" || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
    echo "所有服务已停止"
else
    # 兜底：按端口kill
    for port in 8080 8001 8002 8003 8004 8005; do
        pid=$(lsof -ti:$port 2>/dev/null) && kill $pid 2>/dev/null && echo "停止端口 $port (PID $pid)" || true
    done
fi
