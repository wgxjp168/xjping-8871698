# 我来购ILbuy 故障排查手册

## 一、服务启动失败

### 问题1：Pod 反复 CrashLoopBackOff

**排查步骤：**

```bash
# Step 1: 查看Pod状态和事件
kubectl describe pod <pod-name> -n ilbuy-prod

# Step 2: 查看容器日志（当前实例）
kubectl logs <pod-name> -n ilbuy-prod --tail=200

# Step 3: 查看前一个崩溃实例的日志
kubectl logs <pod-name> -n ilbuy-prod --previous --tail=200

# Step 4: 进入容器调试（如容器能临时启动）
kubectl exec -it <pod-name> -n ilbuy-prod -- /bin/sh

# Step 5: 查看K8s事件
kubectl get events -n ilbuy-prod --sort-by=.metadata.creationTimestamp | tail -20
```

**常见原因及解决方案：**

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Connection refused: nacos-headless:8848` | Nacos服务未就绪 | 检查Nacos Pod状态，等待就绪后重启服务Pod |
| `Communications link failure` (MySQL) | 数据库连接失败 | 检查MySQL地址/密码/防火墙规则 |
| `Failed to connect to Redis` | Redis连接失败 | 验证Redis密码和集群状态 |
| `OOMKilled` | 内存不足 | 调大requests/limits，优化JVM堆内存 |
| `Error: Unable to access jarfile` | 镜像构建问题 | 检查Dockerfile，重新构建镜像 |
| `ConfigDataLocationNotFoundException` | 配置中心数据Id不存在 | 检查Nacos中配置是否已导入 |

```bash
# 修复内存不足（OOMKilled）
kubectl patch deployment procurement-service -n ilbuy-prod \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"procurement-service","resources":{"requests":{"memory":"1Gi"},"limits":{"memory":"2Gi"}}}]}}}}'
```

---

### 问题2：服务启动慢或ReadinessProbe失败

```bash
# 查看Probe配置
kubectl describe pod <pod-name> -n ilbuy-prod | grep -A 10 "Readiness"

# 临时禁用Readiness Probe排查（仅测试环境）
kubectl patch deployment user-service -n ilbuy-prod \
  --type json \
  -p '[{"op": "remove", "path": "/spec/template/spec/containers/0/readinessProbe"}]'

# 手动测试健康接口
kubectl port-forward <pod-name> 18080:8080 -n ilbuy-prod &
curl http://localhost:18080/actuator/health
```

---

## 二、接口报错排查

### 问题3：接口返回 5xx 错误

```bash
# Step 1: 查看Gateway日志（快速定位到哪个服务报错）
kubectl logs -l app=api-gateway -n ilbuy-prod --tail=100 | grep "ERROR\|5[0-9][0-9]"

# Step 2: 通过TraceId查全链路日志（ELK）
# 在Kibana中搜索：traceId:"your-trace-id-here"

# Step 3: 查看对应服务日志
kubectl logs -l app=procurement-service -n ilbuy-prod --tail=200 | grep ERROR

# Step 4: 查看异常堆栈
kubectl logs -l app=order-service -n ilbuy-prod --since=10m | \
  awk '/Exception/{found=1} found{print; if(/^\s*$/) found=0}'
```

---

### 问题4：接口返回 500 - 数据库操作失败

```bash
# 检查MySQL主从同步状态
mysql -h 192.168.1.32 -u root -pILbuy@MySQL2024 -e "SHOW REPLICA STATUS\G" | \
  grep -E "Replica_IO_Running|Replica_SQL_Running|Last_Error|Seconds_Behind_Source"

# 如果IO线程停了，重启
mysql -h 192.168.1.32 -u root -pILbuy@MySQL2024 << 'EOF'
STOP REPLICA IO_THREAD;
START REPLICA IO_THREAD;
EOF

# 如果SQL线程有错误（GTID冲突）
mysql -h 192.168.1.32 -u root -pILbuy@MySQL2024 << 'EOF'
STOP REPLICA;
SET GLOBAL gtid_next='MASTER_UUID:1';  -- 替换为冲突的GTID
BEGIN; COMMIT;
SET GLOBAL gtid_next='AUTOMATIC';
START REPLICA;
EOF

# 检查慢查询日志
tail -100 /var/log/mysql/slow.log

# 查询当前慢查询
mysql -h 192.168.1.31 -u ilbuy -pILbuy@DB2024 << 'EOF'
SELECT * FROM information_schema.PROCESSLIST
WHERE TIME > 5 ORDER BY TIME DESC;
EOF
```

---

### 问题5：接口超时（Gateway 504）

```bash
# 查看当前活跃连接
kubectl exec -it deploy/api-gateway -n ilbuy-prod -- \
  netstat -tn | awk '{print $6}' | sort | uniq -c | sort -rn

# 查看Sentinel流控日志
kubectl logs -l app=api-gateway -n ilbuy-prod | grep "BLOCKED\|FlowException"

# 查看线程堆栈（检查线程池耗尽）
POD=$(kubectl get pod -l app=procurement-service -n ilbuy-prod -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -n ilbuy-prod -- sh -c 'kill -3 1'  # 触发Thread Dump
kubectl logs $POD -n ilbuy-prod --tail=500 | grep "BLOCKED\|WAITING" | head -20

# 查看连接池状态
kubectl exec -it $POD -n ilbuy-prod -- \
  curl -s http://localhost:8080/actuator/metrics/hikaricp.connections.active
```

---

## 三、数据采集异常

### 问题6：爬虫数据采集失败

```bash
# 查看数据采集服务日志
kubectl logs -l app=data-collector-service -n ilbuy-prod --tail=200

# 常见错误处理
# 错误1：代理IP失效
kubectl exec -it deploy/data-collector-service -n ilbuy-prod -- \
  curl http://localhost:8087/admin/proxy/refresh  # 刷新代理池

# 错误2：目标网站结构变化（解析失败）
# 检查解析结果
kubectl exec -it deploy/data-collector-service -n ilbuy-prod -- \
  curl "http://localhost:8087/admin/parse/test?url=xxx&parser=jd"

# 错误3：采集任务卡死
# 查看任务状态
kubectl exec -it deploy/data-collector-service -n ilbuy-prod -- \
  curl http://localhost:8087/admin/tasks

# 重置卡死任务
kubectl exec -it deploy/data-collector-service -n ilbuy-prod -- \
  curl -X POST http://localhost:8087/admin/tasks/reset-stuck

# 重启采集服务（最后手段）
kubectl rollout restart deployment/data-collector-service -n ilbuy-prod
```

---

## 四、AI模型调用失败

### 问题7：LLM接口超时/报错

```bash
# 查看AI匹配服务日志
kubectl logs -l app=ai-matching-service -n ilbuy-prod --tail=200 | grep -E "ERROR|WARN|timeout"

# 检查LLM接口连通性
kubectl exec -it deploy/ai-matching-service -n ilbuy-prod -- \
  curl -w "\n状态码: %{http_code}\n连接时间: %{time_connect}s\n总时间: %{time_total}s\n" \
  -o /dev/null -s "https://api.openai.com/v1/models" \
  -H "Authorization: Bearer ${LLM_API_KEY}"

# 检查降级是否生效
kubectl exec -it deploy/ai-matching-service -n ilbuy-prod -- \
  curl http://localhost:8083/actuator/circuitbreakers

# 手动触发熔断恢复
kubectl exec -it deploy/ai-matching-service -n ilbuy-prod -- \
  curl -X POST http://localhost:8083/actuator/circuitbreaker/reset/llmClient

# 如果LLM服务长期不可用，切换为纯规则引擎模式
kubectl set env deployment/ai-matching-service -n ilbuy-prod \
  MATCHING_MODE=RULE_ENGINE_ONLY
```

---

## 五、容器崩溃排查

### 问题8：Pod OOMKilled（内存溢出）

```bash
# 查看内存使用情况
kubectl top pods -n ilbuy-prod --sort-by=memory

# 查看容器历史退出记录
kubectl describe pod <pod-name> -n ilbuy-prod | grep -A 5 "Last State"

# 查看JVM堆内存使用（通过Actuator）
POD=$(kubectl get pod -l app=order-service -n ilbuy-prod -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $POD -n ilbuy-prod -- \
  curl -s http://localhost:8080/actuator/metrics/jvm.memory.used | python3 -m json.tool

# 触发GC
kubectl exec -it $POD -n ilbuy-prod -- \
  curl -X POST http://localhost:8080/actuator/gc

# 下载Heap Dump分析（如启用了OOM时自动Dump）
kubectl cp ilbuy-prod/$POD:/app/logs/heap-dump.hprof ./heap-dump.hprof

# 调大内存限制（临时解决）
kubectl patch deployment order-service -n ilbuy-prod \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"order-service","env":[{"name":"JAVA_OPTS","value":"-Xms1g -Xmx2g -XX:+UseG1GC"}],"resources":{"limits":{"memory":"2.5Gi"}}}]}}}}'
```

---

### 问题9：磁盘空间不足

```bash
# 检查节点磁盘使用
kubectl get nodes -o custom-columns='NAME:.metadata.name,CAPACITY:.status.capacity.ephemeral-storage,ALLOCATABLE:.status.allocatable.ephemeral-storage'

# 清理无用镜像和容器（在每个节点执行）
docker system prune -f --volumes
crictl rmi --prune

# 清理K8s日志
find /var/log/pods -name "*.log" -mtime +7 -delete
journalctl --vacuum-size=500M

# 清理应用日志（超过7天的）
kubectl exec -it deploy/procurement-service -n ilbuy-prod -- \
  find /app/logs -name "*.log.*" -mtime +7 -delete
```

---

## 六、消息队列问题

### 问题10：Kafka消费积压

```bash
# 查看消费组延迟
kubectl exec -it kafka-client -n middleware -- \
  kafka-consumer-groups.sh \
    --bootstrap-server kafka:9092 \
    --describe \
    --group ilbuy-matching-group

# 查看Topic详情
kubectl exec -it kafka-client -n middleware -- \
  kafka-topics.sh --describe --topic procurement.matching \
    --bootstrap-server kafka:9092

# 如果消费者组停止消费，重置消费位点（慎用！会丢失消息或重复消费）
kubectl exec -it kafka-client -n middleware -- \
  kafka-consumer-groups.sh \
    --bootstrap-server kafka:9092 \
    --group ilbuy-matching-group \
    --topic procurement.matching \
    --reset-offsets \
    --to-latest \
    --execute

# 扩容消费者实例（增加副本数）
kubectl scale deployment ai-matching-service --replicas=5 -n ilbuy-prod

# 查看死信队列
kubectl exec -it kafka-client -n middleware -- \
  kafka-console-consumer.sh \
    --bootstrap-server kafka:9092 \
    --topic matching.dlq \
    --from-beginning \
    --max-messages 10
```

---

## 七、网络问题

### 问题11：服务间无法通信（Feign调用失败）

```bash
# 检查Service是否存在
kubectl get svc -n ilbuy-prod

# 检查Endpoints是否健康
kubectl get endpoints user-service -n ilbuy-prod

# Pod间连通性测试
kubectl exec -it deploy/procurement-service -n ilbuy-prod -- \
  curl http://user-service.ilbuy-prod.svc.cluster.local:8081/actuator/health

# 查看Nacos服务注册状态
curl "http://nacos-headless.middleware:8848/nacos/v1/ns/instance/list?serviceName=user-service&namespaceId=prod"

# DNS解析测试
kubectl exec -it deploy/procurement-service -n ilbuy-prod -- \
  nslookup user-service.ilbuy-prod.svc.cluster.local

# 检查NetworkPolicy（如有配置）
kubectl get networkpolicy -n ilbuy-prod
```

---

## 八、快速诊断脚本

```bash
#!/bin/bash
# quick-diagnosis.sh - 快速诊断脚本

NAMESPACE="ilbuy-prod"

echo "========================================"
echo "  ILbuy 生产环境快速诊断报告"
echo "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

echo ""
echo "【1】Pod状态概览"
kubectl get pods -n $NAMESPACE -o wide | head -30

echo ""
echo "【2】异常Pod（非Running状态）"
kubectl get pods -n $NAMESPACE | grep -v "Running\|Completed\|NAME"

echo ""
echo "【3】最近事件（异常）"
kubectl get events -n $NAMESPACE --sort-by=.metadata.creationTimestamp | \
  grep -E "Warning|Error|Failed|OOMKilled" | tail -10

echo ""
echo "【4】资源使用情况"
kubectl top pods -n $NAMESPACE --sort-by=cpu 2>/dev/null | head -15

echo ""
echo "【5】HPA状态"
kubectl get hpa -n $NAMESPACE

echo ""
echo "【6】Service端点健康"
for svc in api-gateway user-service procurement-service ai-matching-service order-service; do
  endpoints=$(kubectl get endpoints $svc -n $NAMESPACE -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)
  if [ -n "$endpoints" ]; then
    echo "  ✓ $svc: 健康 (${endpoints})"
  else
    echo "  ✗ $svc: 无可用端点！"
  fi
done

echo ""
echo "【7】中间件状态"
echo "  Redis:"
redis-cli -h 192.168.1.41 -p 7001 -a ILbuy@Redis2024 cluster info 2>/dev/null | grep cluster_state
echo "  Kafka:"
kubectl exec -it kafka-client -n middleware -- kafka-topics.sh --list --bootstrap-server kafka:9092 2>/dev/null | wc -l
echo "  Nacos:"
curl -sf "http://nacos-headless.middleware:8848/nacos/v1/ns/health/ready" 2>/dev/null && echo "OK" || echo "FAIL"

echo ""
echo "========================================"
echo "诊断完成"
```
