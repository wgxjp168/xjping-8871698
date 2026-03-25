# 02 · 生产环境部署架构

## 2.1 总体架构图

```
                        ┌──────────────────────────────────────┐
                        │         互联网 / 卫健局专网              │
                        └────────────────┬─────────────────────┘
                                         │ HTTPS 443
                        ┌────────────────▼─────────────────────┐
                        │          Nginx 反向代理 (DMZ)          │
                        │    SSL卸载 / 静态资源 / 负载均衡         │
                        │         192.168.10.10                 │
                        └──────┬────────────────────┬──────────┘
                               │ /api → :9090       │ / → :3000
              ┌────────────────▼────┐   ┌───────────▼──────────┐
              │  Spring Cloud       │   │    Vue3 前端静态资源   │
              │  Gateway :9090      │   │  (Nginx 直接服务)     │
              │  JWT鉴权/路由/CORS   │   └──────────────────────┘
              └──┬──┬──┬──┬──┬─────┘
     ┌───────────┘  │  │  │  └──────────────┐
     │        ┌─────┘  │  └────┐            │
  :8001    :8002    :8003    :8004         :8005
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   ┌──────┐
│hd-   │ │hd-   │ │hd-   │ │hd-   │   │hd-dr │
│auth  │ │resid.│ │device│ │check │   │      │
└──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘   └──┬───┘
   │        │        │  TCP   │           │
   └────────┴────────┤ :7100  ├───────────┘
                     │        │
              ┌──────▼──┐  ┌──▼──────────────────┐
              │ Redis   │  │      MySQL 8.0        │
              │ :6379   │  │  hd_public_health     │
              │ JWT黑名单│  │  192.168.10.20:3306   │
              └─────────┘  └──────────────────────┘
                                      │
                           ┌──────────▼──────────┐
                           │   NAS/OSS 文件存储    │
                           │  DR影像 / 报告PDF     │
                           └─────────────────────┘

──── 医疗设备局域网 ────────────────────────────────────────────
  设备IP段: 192.168.20.0/24
  [生化仪×2] [血常规仪×3] [尿分析仪×3] [糖化Hb仪×3]
    │  ASTM E1394 over TCP → 192.168.10.30:7100(hd-device)
```

---

## 2.2 服务器规划

### 生产服务器配置（最低）

| 角色 | 规格 | 数量 | IP | 说明 |
|------|------|------|----|------|
| 应用服务器 | 8核 16GB RAM 200GB SSD | 1 | 192.168.10.30 | 运行所有微服务 |
| 数据库服务器 | 8核 32GB RAM 1TB HDD + 500GB SSD | 1 | 192.168.10.20 | MySQL主库 |
| 缓存/代理服务器 | 4核 8GB RAM 100GB SSD | 1 | 192.168.10.10 | Nginx + Redis |
| 备份服务器 | 4核 8GB RAM 4TB HDD | 1 | 192.168.10.40 | 定时备份 |

### 推荐高可用配置（二期）

```
负载均衡层:  HAProxy × 2 (主备 VIP: 192.168.10.100)
应用层:      应用服务器 × 2 (微服务容器化)
数据库层:    MySQL 主从复制 (1主1从) + MHA自动切换
缓存层:      Redis Sentinel (1主2从)
存储层:      MinIO 分布式对象存储 (DR影像)
```

---

## 2.3 容器化部署方案（Docker Compose）

### 目录结构

```
/opt/hd-ph/
├── docker-compose.yml          # 主编排文件
├── docker-compose.prod.yml     # 生产环境覆盖
├── nginx/
│   ├── nginx.conf
│   └── ssl/                    # SSL证书
├── mysql/
│   ├── init/                   # 初始化SQL
│   └── conf/my.cnf
├── redis/
│   └── redis.conf
├── logs/                       # 统一日志目录
├── data/
│   ├── mysql/                  # MySQL数据持久化
│   ├── redis/
│   └── images/                 # DR影像存储
└── jars/                       # 各服务JAR包
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: hd-mysql
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: "${MYSQL_ROOT_PASSWORD}"
      MYSQL_DATABASE: hd_public_health
      TZ: Asia/Shanghai
    ports:
      - "3306:3306"
    volumes:
      - /opt/hd-ph/data/mysql:/var/lib/mysql
      - /opt/hd-ph/mysql/init:/docker-entrypoint-initdb.d
      - /opt/hd-ph/mysql/conf/my.cnf:/etc/mysql/conf.d/my.cnf
    networks:
      - hd-net
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7.2-alpine
    container_name: hd-redis
    restart: always
    command: redis-server /etc/redis/redis.conf
    ports:
      - "6379:6379"
    volumes:
      - /opt/hd-ph/redis/redis.conf:/etc/redis/redis.conf
      - /opt/hd-ph/data/redis:/data
    networks:
      - hd-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  hd-gateway:
    image: hd-gateway:1.0.0
    container_name: hd-gateway
    restart: always
    ports:
      - "9090:9090"
    environment:
      - SPRING_REDIS_HOST=redis
      - TZ=Asia/Shanghai
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - hd-net
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  hd-auth:
    image: hd-auth:1.0.0
    container_name: hd-auth
    restart: always
    ports:
      - "8001:8001"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/hd_public_health?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
      - SPRING_DATASOURCE_USERNAME=root
      - SPRING_DATASOURCE_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - SPRING_REDIS_HOST=redis
      - TZ=Asia/Shanghai
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - /opt/hd-ph/logs/auth:/logs
    networks:
      - hd-net

  hd-resident:
    image: hd-resident:1.0.0
    container_name: hd-resident
    restart: always
    ports:
      - "8002:8002"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/hd_public_health?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
      - SPRING_DATASOURCE_USERNAME=root
      - SPRING_DATASOURCE_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - TZ=Asia/Shanghai
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - /opt/hd-ph/logs/resident:/logs
    networks:
      - hd-net

  hd-device:
    image: hd-device:1.0.0
    container_name: hd-device
    restart: always
    ports:
      - "8003:8003"
      - "7100:7100"          # ASTM TCP Server
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/hd_public_health?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
      - SPRING_DATASOURCE_USERNAME=root
      - SPRING_DATASOURCE_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - SPRING_REDIS_HOST=redis
      - DEVICE_TCP_PORT=7100
      - DEVICE_TCP_ENABLED=true
      - TZ=Asia/Shanghai
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - /opt/hd-ph/logs/device:/logs
    networks:
      - hd-net
      - device-net           # 设备局域网

  hd-check:
    image: hd-check:1.0.0
    container_name: hd-check
    restart: always
    ports:
      - "8004:8004"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/hd_public_health?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
      - SPRING_DATASOURCE_USERNAME=root
      - SPRING_DATASOURCE_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - TZ=Asia/Shanghai
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - /opt/hd-ph/logs/check:/logs
    networks:
      - hd-net

  hd-dr:
    image: hd-dr:1.0.0
    container_name: hd-dr
    restart: always
    ports:
      - "8005:8005"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/hd_public_health?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
      - SPRING_DATASOURCE_USERNAME=root
      - SPRING_DATASOURCE_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - TZ=Asia/Shanghai
    depends_on:
      mysql:
        condition: service_healthy
    volumes:
      - /opt/hd-ph/logs/dr:/logs
      - /opt/hd-ph/data/images:/images  # DR影像存储
    networks:
      - hd-net

  nginx:
    image: nginx:1.25-alpine
    container_name: hd-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /opt/hd-ph/nginx/nginx.conf:/etc/nginx/nginx.conf
      - /opt/hd-ph/nginx/ssl:/etc/nginx/ssl
      - /opt/hd-ph/hd-frontend/dist:/usr/share/nginx/html
    depends_on:
      - hd-gateway
    networks:
      - hd-net

networks:
  hd-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
  device-net:
    driver: bridge
    ipam:
      config:
        - subnet: 192.168.20.0/24
```

### Nginx 配置

```nginx
# /opt/hd-ph/nginx/nginx.conf
server {
    listen 80;
    server_name phcheck.huidong.gov.cn;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name phcheck.huidong.gov.cn;

    ssl_certificate     /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-RSA-AES128-GCM-SHA256:HIGH:!aNULL:!MD5;

    # 前端静态资源
    location / {
        root   /usr/share/nginx/html;
        index  index.html;
        try_files $uri $uri/ /index.html;  # Vue Router history mode
        gzip on;
        gzip_types text/plain application/javascript text/css application/json;
    }

    # API代理到网关
    location /api/ {
        proxy_pass         http://hd-gateway:9090/api/;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        client_max_body_size 100m;  # DR影像上传
    }

    # 健康检查
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    # 安全头
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
}
```

---

## 2.4 MySQL 生产配置

```ini
# /opt/hd-ph/mysql/conf/my.cnf
[mysqld]
character-set-server    = utf8mb4
collation-server        = utf8mb4_unicode_ci
default-time-zone       = +08:00
max_connections         = 500
innodb_buffer_pool_size = 8G       # 数据库服务器内存的50%~70%
innodb_log_file_size    = 512M
innodb_flush_log_at_trx_commit = 1 # 生产环境不可改
sync_binlog             = 1        # 生产环境不可改
slow_query_log          = ON
slow_query_log_file     = /var/log/mysql/slow.log
long_query_time         = 2
log_bin                 = /var/log/mysql/mysql-bin
expire_logs_days        = 7
binlog_format           = ROW
```

---

## 2.5 网络安全策略

```
【防火墙规则（iptables）】

对外开放:
  443/tcp   HTTPS (Nginx)
  80/tcp    HTTP (跳转HTTPS)

内部开放 (仅内网IP段 192.168.10.0/24):
  9090/tcp  API Gateway
  8001-8005/tcp  微服务端口（仅运维访问）
  3306/tcp  MySQL（仅应用服务器IP）
  6379/tcp  Redis（仅应用服务器IP）

设备网络 (仅 192.168.20.0/24):
  7100/tcp  ASTM TCP Server (hd-device)

全部关闭:
  其余所有端口 DROP

【VPN策略】
  运维SSH登录需通过 VPN (OpenVPN/WireGuard)
  SSH端口修改为非默认端口(如 22022)
  禁止root直接SSH登录
  仅允许SSH密钥认证

【数据库安全】
  MySQL不对外网开放
  应用账号仅有 SELECT/INSERT/UPDATE/DELETE 权限
  禁止应用账号执行 DROP/TRUNCATE/ALTER
  定期轮换数据库密码(每季度)
```

---

## 2.6 环境变量管理

生产环境所有敏感信息通过环境变量注入，禁止明文写入配置文件：

```bash
# /opt/hd-ph/.env（设置600权限，只读）
MYSQL_ROOT_PASSWORD=生产密码(不少于16位)
REDIS_PASSWORD=生产Redis密码
JWT_SECRET=生产JWT密钥(不少于32位随机字符串)
```

```bash
# 设置安全权限
chmod 600 /opt/hd-ph/.env
chown root:root /opt/hd-ph/.env
```
