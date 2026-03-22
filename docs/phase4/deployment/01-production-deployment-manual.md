# 我来购ILbuy 生产部署手册

## 文档说明

| 属性 | 内容 |
|------|------|
| 文档版本 | v1.0 |
| 适用环境 | Linux + Kubernetes 生产环境 |
| 最后更新 | 2024-03-22 |
| 维护团队 | ILbuy运维团队 |

> **重要：** 所有命令在 root 或具备 sudo 权限的账号下执行。生产操作前务必做好数据备份。

---

## 一、生产环境规格

### 1.1 服务器规格（初期规划）

| 服务器角色 | 数量 | CPU | 内存 | 磁盘 | 网络 | 备注 |
|-----------|------|-----|------|------|------|------|
| K8s Master节点 | 3 | 4核 | 8GB | 200GB SSD | 千兆 | 高可用Master集群 |
| K8s Worker节点 | 6 | 8核 | 16GB | 500GB SSD | 万兆 | 业务服务Pod |
| MySQL主节点 | 1 | 8核 | 32GB | 2TB SSD | 万兆 | 主库，写操作 |
| MySQL从节点 | 2 | 8核 | 32GB | 2TB SSD | 万兆 | 从库，读操作 |
| Redis集群节点 | 6 | 4核 | 16GB | 200GB SSD | 万兆 | 3主3从集群 |
| Kafka节点 | 3 | 4核 | 8GB | 1TB HDD | 万兆 | 消息队列集群 |
| Nacos节点 | 3 | 2核 | 4GB | 100GB SSD | 千兆 | 配置/注册中心 |
| ELK节点 | 3 | 8核 | 32GB | 4TB HDD | 万兆 | 日志系统 |
| 监控节点 | 2 | 4核 | 8GB | 500GB SSD | 千兆 | Prometheus+Grafana |
| 负载均衡 | 2 | 4核 | 8GB | 100GB | 万兆 | Nginx/HAProxy，主备 |

### 1.2 操作系统与软件版本

```
操作系统：    CentOS 7.9 / RHEL 8.x / Ubuntu 22.04 LTS
内核版本：    ≥ 4.19（推荐 5.4+）
Docker：     24.0.x
Kubernetes： 1.28.x
Helm：       3.13.x
MySQL：      8.0.x
Redis：      7.0.x
Kafka：      3.5.x
Nacos：      2.3.x
Elasticsearch：8.x
JDK：        OpenJDK 17
```

---

## 二、服务器初始化

### Step 1：系统基础配置（所有节点执行）

```bash
# 设置主机名（各节点修改为对应名称）
hostnamectl set-hostname k8s-master-01

# 关闭防火墙（或配置规则放行）
systemctl stop firewalld
systemctl disable firewalld

# 关闭SELinux
setenforce 0
sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config

# 关闭Swap（K8s要求）
swapoff -a
sed -ri 's/.*swap.*/#&/' /etc/fstab

# 配置内核参数
cat > /etc/sysctl.d/k8s.conf << 'EOF'
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
vm.swappiness                       = 0
net.ipv4.tcp_max_syn_backlog        = 65535
net.core.somaxconn                  = 65535
net.ipv4.tcp_fin_timeout            = 30
net.ipv4.tcp_keepalive_time         = 600
fs.file-max                         = 1000000
fs.inotify.max_user_instances       = 512
fs.inotify.max_user_watches         = 16384
EOF
sysctl -p /etc/sysctl.d/k8s.conf

# 加载内核模块
modprobe overlay
modprobe br_netfilter
cat > /etc/modules-load.d/k8s.conf << 'EOF'
overlay
br_netfilter
EOF

# 配置时间同步
timedatectl set-timezone Asia/Shanghai
yum install -y chrony
systemctl enable chronyd
systemctl start chronyd

# 配置hosts解析（所有节点）
cat >> /etc/hosts << 'EOF'
192.168.1.10  k8s-master-01
192.168.1.11  k8s-master-02
192.168.1.12  k8s-master-03
192.168.1.21  k8s-worker-01
192.168.1.22  k8s-worker-02
192.168.1.23  k8s-worker-03
192.168.1.24  k8s-worker-04
192.168.1.25  k8s-worker-05
192.168.1.26  k8s-worker-06
192.168.1.31  mysql-master-01
192.168.1.32  mysql-slave-01
192.168.1.33  mysql-slave-02
192.168.1.41  redis-01
192.168.1.42  redis-02
192.168.1.43  redis-03
192.168.1.44  redis-04
192.168.1.45  redis-05
192.168.1.46  redis-06
EOF
```

### Step 2：安装 Docker

```bash
# 安装依赖
yum install -y yum-utils device-mapper-persistent-data lvm2

# 添加Docker仓库
yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo

# 安装Docker
yum install -y docker-ce-24.0.7 docker-ce-cli-24.0.7 containerd.io docker-buildx-plugin

# 配置Docker daemon
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://registry.cn-hangzhou.aliyuncs.com"
  ],
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "data-root": "/data/docker"
}
EOF

systemctl daemon-reload
systemctl enable docker
systemctl start docker

# 验证
docker version
docker info
```

### Step 3：安装 Kubernetes 组件

```bash
# 添加K8s仓库
cat > /etc/yum.repos.d/kubernetes.repo << 'EOF'
[kubernetes]
name=Kubernetes
baseurl=https://mirrors.aliyun.com/kubernetes/yum/repos/kubernetes-el7-x86_64/
enabled=1
gpgcheck=0
EOF

# 安装kubeadm、kubelet、kubectl
yum install -y kubelet-1.28.4 kubeadm-1.28.4 kubectl-1.28.4

systemctl enable kubelet
# 注意：kubelet此时不需要启动，kubeadm初始化后会自动管理

# 配置crictl（容器运行时工具）
cat > /etc/crictl.yaml << 'EOF'
runtime-endpoint: unix:///run/containerd/containerd.sock
image-endpoint: unix:///run/containerd/containerd.sock
timeout: 10
debug: false
EOF
```

---

## 三、K8s集群初始化

### Step 4：初始化Master节点（第一个Master执行）

```bash
# 生成初始化配置文件
cat > kubeadm-config.yaml << 'EOF'
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
kubernetesVersion: v1.28.4
controlPlaneEndpoint: "192.168.1.100:6443"  # VIP地址（HAProxy/Keepalived）
imageRepository: registry.aliyuncs.com/google_containers
networking:
  podSubnet: "10.244.0.0/16"
  serviceSubnet: "10.96.0.0/12"
  dnsDomain: "cluster.local"
etcd:
  local:
    dataDir: /var/lib/etcd
apiServer:
  certSANs:
  - "192.168.1.10"
  - "192.168.1.11"
  - "192.168.1.12"
  - "192.168.1.100"
  - "k8s-api.ilbuy.internal"
  extraArgs:
    audit-log-path: /var/log/audit/audit.log
    audit-log-maxage: "30"
    audit-log-maxbackup: "10"
    audit-log-maxsize: "100"
---
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
cgroupDriver: systemd
EOF

# 预拉取镜像（可选，提前准备）
kubeadm config images pull --config kubeadm-config.yaml

# 初始化第一个Master
kubeadm init --config kubeadm-config.yaml --upload-certs | tee /root/kubeadm-init.log

# 配置kubectl
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

# 安装Calico网络插件
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.4/manifests/calico.yaml

# 验证Master节点就绪
kubectl get nodes
kubectl get pods -n kube-system
```

### Step 5：加入其他Master节点

```bash
# 从第一个Master的初始化输出中获取join命令
# 格式示例：
kubeadm join 192.168.1.100:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane \
  --certificate-key <cert-key>

# 每个Master节点执行后：
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
```

### Step 6：加入Worker节点

```bash
# 每个Worker节点执行（join命令从初始化输出获取）
kubeadm join 192.168.1.100:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>

# 在Master上验证节点加入
kubectl get nodes -o wide
# 预期所有节点状态为 Ready
```

### Step 7：安装 Helm

```bash
# 在Master节点安装Helm
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 或离线安装
wget https://get.helm.sh/helm-v3.13.3-linux-amd64.tar.gz
tar xzf helm-v3.13.3-linux-amd64.tar.gz
mv linux-amd64/helm /usr/local/bin/helm

# 验证
helm version

# 添加常用Helm仓库
helm repo add stable https://charts.helm.sh/stable
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

---

## 四、中间件集群部署

### Step 8：部署 MySQL 主从集群

#### 主节点配置（mysql-master-01）

```bash
# 安装MySQL 8.0
yum install -y mysql-server-8.0
# 或使用Docker方式
docker run -d \
  --name mysql-master \
  --restart=unless-stopped \
  -v /data/mysql/data:/var/lib/mysql \
  -v /data/mysql/conf:/etc/mysql/conf.d \
  -v /data/mysql/logs:/var/log/mysql \
  -e MYSQL_ROOT_PASSWORD=ILbuy@MySQL2024 \
  -p 3306:3306 \
  mysql:8.0 \
  --server-id=1 \
  --log-bin=mysql-bin \
  --binlog-format=ROW \
  --gtid-mode=ON \
  --enforce-gtid-consistency=ON \
  --binlog-expire-logs-seconds=604800
```

**主节点配置文件（/data/mysql/conf/master.cnf）：**
```ini
[mysqld]
server-id=1
log-bin=mysql-bin
binlog-format=ROW
gtid-mode=ON
enforce-gtid-consistency=ON
binlog-expire-logs-seconds=604800
max_connections=2000
max_connect_errors=100
innodb_buffer_pool_size=16G
innodb_buffer_pool_instances=8
innodb_log_file_size=2G
innodb_log_buffer_size=256M
innodb_flush_log_at_trx_commit=1
sync_binlog=1
innodb_flush_method=O_DIRECT
read_rnd_buffer_size=4M
sort_buffer_size=4M
join_buffer_size=4M
tmp_table_size=128M
max_heap_table_size=128M
slow_query_log=1
slow_query_log_file=/var/log/mysql/slow.log
long_query_time=2
log_queries_not_using_indexes=1
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
```

```bash
# 创建复制账号（在主库执行）
docker exec -it mysql-master mysql -u root -pILbuy@MySQL2024 << 'EOF'
CREATE USER 'repl'@'%' IDENTIFIED BY 'Repl@MySQL2024';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
EOF

# 创建业务数据库
docker exec -it mysql-master mysql -u root -pILbuy@MySQL2024 << 'EOF'
CREATE DATABASE ilbuy_user CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE ilbuy_procurement CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE ilbuy_order CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE ilbuy_supplier CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE ilbuy_inquiry CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE ilbuy_matching CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE ilbuy_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE ilbuy_notification CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE seata CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE nacos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'ilbuy'@'%' IDENTIFIED BY 'ILbuy@DB2024';
GRANT ALL PRIVILEGES ON ilbuy_*.* TO 'ilbuy'@'%';
GRANT ALL PRIVILEGES ON seata.* TO 'ilbuy'@'%';
GRANT ALL PRIVILEGES ON nacos.* TO 'ilbuy'@'%';
FLUSH PRIVILEGES;
EOF
```

#### 从节点配置（mysql-slave-01/02）

```bash
# 从节点启动
docker run -d \
  --name mysql-slave-01 \
  --restart=unless-stopped \
  -v /data/mysql/data:/var/lib/mysql \
  -v /data/mysql/conf:/etc/mysql/conf.d \
  -e MYSQL_ROOT_PASSWORD=ILbuy@MySQL2024 \
  -p 3306:3306 \
  mysql:8.0 \
  --server-id=2 \
  --read-only=ON \
  --gtid-mode=ON \
  --enforce-gtid-consistency=ON

# 配置主从复制（在从库执行）
docker exec -it mysql-slave-01 mysql -u root -pILbuy@MySQL2024 << 'EOF'
CHANGE REPLICATION SOURCE TO
  SOURCE_HOST='192.168.1.31',
  SOURCE_PORT=3306,
  SOURCE_USER='repl',
  SOURCE_PASSWORD='Repl@MySQL2024',
  SOURCE_AUTO_POSITION=1;
START REPLICA;
EOF

# 验证复制状态
docker exec -it mysql-slave-01 mysql -u root -pILbuy@MySQL2024 -e "SHOW REPLICA STATUS\G" | \
  grep -E "Replica_IO_Running|Replica_SQL_Running|Seconds_Behind_Source"
# 期望：Replica_IO_Running: Yes, Replica_SQL_Running: Yes
```

---

### Step 9：部署 Redis 集群

```bash
# 在6个Redis节点分别创建配置目录
for i in 1 2 3 4 5 6; do
  mkdir -p /data/redis-cluster/node-${i}/{data,conf,logs}
done

# Redis集群节点配置（端口7001-7006）
for port in 7001 7002 7003 7004 7005 7006; do
cat > /data/redis-cluster/node-${port}/conf/redis.conf << EOF
port ${port}
cluster-enabled yes
cluster-config-file /data/nodes.conf
cluster-node-timeout 15000
appendonly yes
appendfilename appendonly.aof
dir /data
logfile /logs/redis.log
loglevel notice
maxmemory 12gb
maxmemory-policy allkeys-lru
protected-mode no
bind 0.0.0.0
requirepass ILbuy@Redis2024
masterauth ILbuy@Redis2024
save 900 1
save 300 10
save 60 10000
EOF
done

# 启动Redis集群节点（分布到3台物理机，每台2个节点）
# 物理机192.168.1.41运行 7001/7002
# 物理机192.168.1.42运行 7003/7004
# 物理机192.168.1.43运行 7005/7006

# 创建Redis集群
redis-cli --cluster create \
  192.168.1.41:7001 192.168.1.41:7002 \
  192.168.1.42:7003 192.168.1.42:7004 \
  192.168.1.43:7005 192.168.1.43:7006 \
  --cluster-replicas 1 \
  -a ILbuy@Redis2024

# 验证集群状态
redis-cli -h 192.168.1.41 -p 7001 -a ILbuy@Redis2024 cluster info
redis-cli -h 192.168.1.41 -p 7001 -a ILbuy@Redis2024 cluster nodes
```

---

### Step 10：部署 Kafka 集群

```bash
# 使用Helm部署Kafka（在K8s中部署）
helm install kafka bitnami/kafka \
  --namespace middleware \
  --create-namespace \
  --set replicaCount=3 \
  --set zookeeper.replicaCount=3 \
  --set persistence.size=100Gi \
  --set resources.requests.memory=4Gi \
  --set resources.requests.cpu=2 \
  --set auth.enabled=true \
  --set auth.sasl.mechanisms=plain \
  --set auth.sasl.interBrokerMechanism=plain \
  --set-string auth.sasl.jaas.clientUsers[0]=ilbuy \
  --set-string auth.sasl.jaas.clientPasswords[0]=ILbuy@Kafka2024 \
  --set-string auth.sasl.jaas.interBrokerUser=ilbuy \
  --set-string auth.sasl.jaas.interBrokerPassword=ILbuy@Kafka2024 \
  -f kafka-values.yaml

# 创建业务Topic
kubectl run kafka-client --restart='Never' --image docker.io/bitnami/kafka:3.5.1 \
  --namespace middleware --command -- sleep infinity

kubectl exec -it kafka-client -n middleware -- bash << 'EOF'
kafka-topics.sh --create --topic procurement.matching --partitions 6 --replication-factor 3 \
  --bootstrap-server kafka:9092
kafka-topics.sh --create --topic procurement.notification --partitions 3 --replication-factor 3 \
  --bootstrap-server kafka:9092
kafka-topics.sh --create --topic order.events --partitions 6 --replication-factor 3 \
  --bootstrap-server kafka:9092
kafka-topics.sh --create --topic data.collection --partitions 3 --replication-factor 3 \
  --bootstrap-server kafka:9092
kafka-topics.sh --create --topic matching.dlq --partitions 1 --replication-factor 3 \
  --bootstrap-server kafka:9092
kafka-topics.sh --list --bootstrap-server kafka:9092
EOF
```

---

### Step 11：部署 Nacos 集群

```bash
# 创建Nacos数据库（已在MySQL中创建nacos库）
# 导入Nacos初始化SQL
kubectl run mysql-client --image=mysql:8.0 --restart=Never -n middleware -- sleep infinity
kubectl exec -it mysql-client -n middleware -- bash << 'EOF'
mysql -h 192.168.1.31 -u ilbuy -pILbuy@DB2024 nacos < /scripts/nacos-mysql.sql
EOF

# 使用Helm部署Nacos
helm repo add nacos https://nacos-group.github.io/nacos-k8s-helm-chart
helm install nacos nacos/nacos \
  --namespace middleware \
  --set global.mode=cluster \
  --set replicaCount=3 \
  --set mysql.external=true \
  --set mysql.host=192.168.1.31 \
  --set mysql.port=3306 \
  --set mysql.user=ilbuy \
  --set mysql.password=ILbuy@DB2024 \
  --set mysql.database=nacos \
  --set resources.requests.memory=2Gi \
  --set resources.requests.cpu=1

# 等待Nacos就绪
kubectl wait --for=condition=Ready pod -l app=nacos -n middleware --timeout=300s

# 验证Nacos集群
kubectl exec -it nacos-0 -n middleware -- curl http://nacos-headless:8848/nacos/v1/ns/health/ready
```

---

## 五、Nacos 配置导入

### Step 12：导入应用配置

```bash
# 创建Nacos配置导入脚本
cat > import_nacos_config.sh << 'SCRIPT'
#!/bin/bash
NACOS_URL="http://192.168.1.100:8848/nacos"
NACOS_USER="nacos"
NACOS_PASS="ILbuy@Nacos2024"
NAMESPACE="prod"

# 创建命名空间
curl -X POST "$NACOS_URL/v1/console/namespaces" \
  -d "customNamespaceId=prod&namespaceName=生产环境&namespaceDesc=ILbuy生产配置" \
  -u $NACOS_USER:$NACOS_PASS

# 上传配置函数
upload_config() {
  local dataId=$1
  local content=$2
  curl -X POST "$NACOS_URL/v1/cs/configs" \
    -d "dataId=${dataId}&group=DEFAULT_GROUP&namespace=${NAMESPACE}&type=yaml&content=$(echo $content | python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read()))')" \
    -u $NACOS_USER:$NACOS_PASS
}

# 公共配置
upload_config "ilbuy-common.yaml" "$(cat configs/ilbuy-common.yaml)"

# 各服务配置
for service in gateway user procurement order supplier inquiry matching data-collector notification; do
  upload_config "ilbuy-${service}-prod.yaml" "$(cat configs/ilbuy-${service}-prod.yaml)"
done

echo "Nacos配置导入完成"
SCRIPT

chmod +x import_nacos_config.sh
./import_nacos_config.sh
```

---

## 六、微服务镜像构建与推送

### Step 13：构建并推送镜像

```bash
# 设置镜像仓库地址（私有Harbor仓库）
REGISTRY="registry.ilbuy.com"
VERSION="1.0.0"

# 登录镜像仓库
docker login ${REGISTRY} -u admin -p ILbuy@Harbor2024

# 构建各微服务镜像（CI/CD流水线中自动执行）
services=(
  "api-gateway"
  "user-service"
  "procurement-service"
  "ai-matching-service"
  "inquiry-service"
  "order-service"
  "supplier-service"
  "data-collector-service"
  "notification-service"
)

for service in "${services[@]}"; do
  echo "构建 ${service}:${VERSION} ..."
  docker build \
    -t ${REGISTRY}/ilbuy/${service}:${VERSION} \
    -t ${REGISTRY}/ilbuy/${service}:latest \
    -f ${service}/Dockerfile \
    --build-arg JAR_FILE=${service}/target/${service}-*.jar \
    .
  docker push ${REGISTRY}/ilbuy/${service}:${VERSION}
  docker push ${REGISTRY}/ilbuy/${service}:latest
  echo "✓ ${service} 推送完成"
done
```

**通用 Dockerfile 模板：**
```dockerfile
FROM openjdk:17-jre-slim

# 创建非root用户
RUN groupadd -r ilbuy && useradd -r -g ilbuy ilbuy

# 设置工作目录
WORKDIR /app

# 复制jar包
ARG JAR_FILE=target/*.jar
COPY ${JAR_FILE} app.jar

# 创建日志目录
RUN mkdir -p /app/logs && chown -R ilbuy:ilbuy /app

USER ilbuy

# JVM参数（通过环境变量覆盖）
ENV JAVA_OPTS="-Xms512m -Xmx1g -XX:+UseG1GC -XX:MaxGCPauseMillis=200 \
  -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/app/logs/heap-dump.hprof \
  -Djava.security.egd=file:/dev/./urandom"

EXPOSE 8080
EXPOSE 8081

ENTRYPOINT ["sh", "-c", "java ${JAVA_OPTS} -jar /app/app.jar"]
```

---

## 七、K8s集群部署微服务

### Step 14：创建K8s命名空间和基础资源

```bash
# 创建命名空间
kubectl create namespace ilbuy-prod

# 创建镜像拉取Secret
kubectl create secret docker-registry harbor-secret \
  --docker-server=registry.ilbuy.com \
  --docker-username=admin \
  --docker-password=ILbuy@Harbor2024 \
  -n ilbuy-prod

# 创建ConfigMap（公共配置）
kubectl create configmap ilbuy-common-config \
  --from-literal=NACOS_SERVER_ADDR=nacos-headless.middleware:8848 \
  --from-literal=NACOS_NAMESPACE=prod \
  --from-literal=SPRING_PROFILES_ACTIVE=prod \
  -n ilbuy-prod

# 创建Secret（敏感配置）
kubectl create secret generic ilbuy-secrets \
  --from-literal=DB_PASSWORD=ILbuy@DB2024 \
  --from-literal=REDIS_PASSWORD=ILbuy@Redis2024 \
  --from-literal=JWT_SECRET=ILbuy@JWT@SecretKey@2024@Production \
  -n ilbuy-prod
```

### Step 15：部署 API Gateway

```bash
# 部署api-gateway
kubectl apply -f k8s/api-gateway-deployment.yaml -n ilbuy-prod

# 部署Service（LoadBalancer类型，对外暴露）
kubectl apply -f k8s/api-gateway-service.yaml -n ilbuy-prod

# 等待部署就绪
kubectl rollout status deployment/api-gateway -n ilbuy-prod

# 查看Pod状态
kubectl get pods -l app=api-gateway -n ilbuy-prod
```

### Step 16：部署所有微服务

```bash
# 批量部署所有微服务
kubectl apply -f k8s/ -n ilbuy-prod

# 等待所有Deployment就绪
deployments=(
  "api-gateway"
  "user-service"
  "procurement-service"
  "ai-matching-service"
  "inquiry-service"
  "order-service"
  "supplier-service"
  "data-collector-service"
  "notification-service"
)

for deploy in "${deployments[@]}"; do
  echo "等待 ${deploy} 就绪..."
  kubectl rollout status deployment/${deploy} -n ilbuy-prod --timeout=300s
  echo "✓ ${deploy} 就绪"
done

# 查看所有Pod状态
kubectl get pods -n ilbuy-prod -o wide
```

---

## 八、服务校验

### Step 17：健康检查

```bash
# 获取Gateway外部IP
GATEWAY_IP=$(kubectl get svc api-gateway -n ilbuy-prod -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Gateway IP: ${GATEWAY_IP}"

# 检查各服务健康状态
echo "=== 健康检查 ==="
services=(
  "api-gateway:8080"
  "user-service:8081"
  "procurement-service:8082"
  "ai-matching-service:8083"
  "inquiry-service:8084"
  "order-service:8085"
  "supplier-service:8086"
  "data-collector-service:8087"
  "notification-service:8088"
)

for svc in "${services[@]}"; do
  name="${svc%%:*}"
  port="${svc##*:}"
  # 使用kubectl port-forward或通过Service访问
  status=$(kubectl exec -it deploy/api-gateway -n ilbuy-prod -- \
    curl -s -o /dev/null -w "%{http_code}" \
    http://${name}.ilbuy-prod.svc.cluster.local:${port}/actuator/health)
  if [ "$status" = "200" ]; then
    echo "✓ ${name}: UP"
  else
    echo "✗ ${name}: 异常（HTTP ${status}）"
  fi
done

# 验证Nacos服务注册
curl -s "http://nacos-headless.middleware:8848/nacos/v1/ns/instance/list?serviceName=user-service&namespaceId=prod" | python3 -m json.tool
```

### Step 18：冒烟测试

```bash
GATEWAY_URL="https://api.ilbuy.com"

echo "=== 冒烟测试 ==="

# 1. 健康接口
echo -n "1. Gateway健康检查... "
curl -sf ${GATEWAY_URL}/actuator/health > /dev/null && echo "✓" || echo "✗"

# 2. 登录接口
echo -n "2. 用户登录接口... "
TOKEN=$(curl -sf -X POST ${GATEWAY_URL}/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"smoke_test","password":"Test@123456","captchaToken":"bypass"}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin)['data']['accessToken'])")
[ -n "$TOKEN" ] && echo "✓" || echo "✗"

# 3. 采购需求列表接口
echo -n "3. 采购需求列表... "
curl -sf -H "Authorization: Bearer ${TOKEN}" \
  "${GATEWAY_URL}/api/v1/procurement/demands?page=0&size=5" > /dev/null && echo "✓" || echo "✗"

# 4. 市场价格查询
echo -n "4. 市场价格查询... "
curl -sf -H "Authorization: Bearer ${TOKEN}" \
  "${GATEWAY_URL}/api/v1/data/market-price?keyword=测试商品" > /dev/null && echo "✓" || echo "✗"

echo "=== 冒烟测试完成 ==="
```

---

## 九、高可用配置

### 9.1 K8s多可用区部署

```yaml
# 部署时配置PodAntiAffinity，确保Pod分布在不同节点
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app
          operator: In
          values:
          - procurement-service
      topologyKey: kubernetes.io/hostname
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 1
      preference:
        matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - zone-a
          - zone-b
          - zone-c
```

### 9.2 HPA自动扩缩容

```bash
# 为核心服务配置HPA
kubectl autoscale deployment procurement-service \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n ilbuy-prod

kubectl autoscale deployment ai-matching-service \
  --cpu-percent=60 \
  --min=2 \
  --max=8 \
  -n ilbuy-prod

# 查看HPA状态
kubectl get hpa -n ilbuy-prod
```

### 9.3 PodDisruptionBudget（维护时保障可用性）

```bash
cat << 'EOF' | kubectl apply -f -
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: procurement-service-pdb
  namespace: ilbuy-prod
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: procurement-service
EOF
```

---

## 十、版本更新（滚动发布）

```bash
# 滚动更新特定服务（零停机）
VERSION_NEW="1.0.1"
SERVICE="procurement-service"

# 方式1：更新镜像触发滚动更新
kubectl set image deployment/${SERVICE} \
  ${SERVICE}=registry.ilbuy.com/ilbuy/${SERVICE}:${VERSION_NEW} \
  -n ilbuy-prod

# 监控滚动更新进度
kubectl rollout status deployment/${SERVICE} -n ilbuy-prod --timeout=300s

# 验证更新结果
kubectl get pods -l app=${SERVICE} -n ilbuy-prod

# 如需回滚（回到上一个版本）
kubectl rollout undo deployment/${SERVICE} -n ilbuy-prod

# 回滚到指定版本
kubectl rollout undo deployment/${SERVICE} --to-revision=2 -n ilbuy-prod

# 查看历史版本
kubectl rollout history deployment/${SERVICE} -n ilbuy-prod
```
