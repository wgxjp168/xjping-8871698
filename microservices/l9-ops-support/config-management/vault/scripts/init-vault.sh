#!/usr/bin/env bash
# =============================================================================
# ILbuy Vault 初始化脚本
# 完成 Vault 初始化、解封、K8s Auth 配置、Secret 引擎和策略配置
# 用法：bash init-vault.sh [VAULT_ADDR]
# =============================================================================
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://vault.ilbuy-ops.svc.cluster.local:8200}"
INIT_OUTPUT_FILE="/tmp/vault-init-keys.json"  # 妥善保管！生产环境加密存储

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die()  { echo "[ERROR] $*" >&2; exit 1; }
ok()   { echo "[  OK  ] $*"; }

export VAULT_ADDR

# ── 检查 vault CLI ──────────────────────────────────────────────────────────
command -v vault > /dev/null || die "vault CLI 未安装"

log "=== Vault 初始化开始 ==="
log "Vault 地址: ${VAULT_ADDR}"

# ── 等待 Vault 就绪 ─────────────────────────────────────────────────────────
for i in $(seq 1 30); do
  if vault status > /dev/null 2>&1 || [ $? -eq 2 ]; then  # exit 2 = sealed
    break
  fi
  log "等待 Vault 启动... (${i}/30)"
  sleep 5
done

VAULT_STATUS=$(vault status -format=json 2>/dev/null || true)
INITIALIZED=$(echo "${VAULT_STATUS}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('initialized', False))" 2>/dev/null || echo "false")

# ── Step 1: 初始化（只在第一次运行）────────────────────────────────────────
if [ "${INITIALIZED}" = "False" ] || [ "${INITIALIZED}" = "false" ]; then
  log "初始化 Vault（5个解封 Key，3个 Key 阈值）..."
  vault operator init \
    -key-shares=5 \
    -key-threshold=3 \
    -format=json > "${INIT_OUTPUT_FILE}" || die "Vault 初始化失败"

  ok "初始化完成，Key 已保存至: ${INIT_OUTPUT_FILE}"
  log "⚠️  请立即将 unseal keys 和 root token 存储到安全位置！"

  # 提取 Root Token
  ROOT_TOKEN=$(python3 -c "import json; d=json.load(open('${INIT_OUTPUT_FILE}')); print(d['root_token'])")
  UNSEAL_KEY_1=$(python3 -c "import json; d=json.load(open('${INIT_OUTPUT_FILE}')); print(d['unseal_keys_b64'][0])")
  UNSEAL_KEY_2=$(python3 -c "import json; d=json.load(open('${INIT_OUTPUT_FILE}')); print(d['unseal_keys_b64'][1])")
  UNSEAL_KEY_3=$(python3 -c "import json; d=json.load(open('${INIT_OUTPUT_FILE}')); print(d['unseal_keys_b64'][2])")

  # 自动解封（仅用于初始化，生产环境建议手动解封或使用 Auto-Unseal）
  log "解封 Vault..."
  vault operator unseal "${UNSEAL_KEY_1}" > /dev/null
  vault operator unseal "${UNSEAL_KEY_2}" > /dev/null
  vault operator unseal "${UNSEAL_KEY_3}" > /dev/null
  ok "Vault 解封完成"
else
  log "Vault 已初始化"
  SEALED=$(echo "${VAULT_STATUS}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sealed', True))" 2>/dev/null || echo "true")
  if [ "${SEALED}" = "True" ] || [ "${SEALED}" = "true" ]; then
    die "Vault 处于封印状态，请手动解封后重新运行此脚本"
  fi
  # 从环境变量或文件读取 Token
  ROOT_TOKEN="${VAULT_TOKEN:-$(cat "${INIT_OUTPUT_FILE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['root_token'])" 2>/dev/null || die "请设置 VAULT_TOKEN 环境变量")}"
fi

export VAULT_TOKEN="${ROOT_TOKEN}"

# ── Step 2: 启用 Secret 引擎 ─────────────────────────────────────────────────
log "--- 启用 Secret 引擎 ---"

# KV v2（静态 Secret 存储）
vault secrets enable -path=secret -version=2 kv 2>/dev/null || log "secret 引擎已存在"
ok "KV v2 secret 引擎启用"

# Database（动态数据库凭据）
vault secrets enable database 2>/dev/null || log "database 引擎已存在"

# 配置 PostgreSQL 动态凭据
vault write database/config/ilbuy-postgres \
  plugin_name=postgresql-database-plugin \
  allowed_roles="ilbuy-readonly,ilbuy-readwrite" \
  connection_url="postgresql://{{username}}:{{password}}@postgres.ilbuy-infra.svc.cluster.local:5432/ilbuy?sslmode=disable" \
  username="vault_admin" \
  password="${POSTGRES_VAULT_PASSWORD:-changeme}"

vault write database/roles/ilbuy-readonly \
  db_name=ilbuy-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

vault write database/roles/ilbuy-readwrite \
  db_name=ilbuy-postgres \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\"; GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

ok "PostgreSQL 动态凭据配置完成"

# Transit（加密即服务）
vault secrets enable transit 2>/dev/null || log "transit 引擎已存在"
vault write transit/keys/ilbuy-data type=aes256-gcm96
ok "Transit 加密引擎启用"

# PKI（内部 CA）
vault secrets enable pki 2>/dev/null || log "pki 引擎已存在"
vault secrets tune -max-lease-ttl=87600h pki
vault write pki/root/generate/internal \
  common_name="ilbuy-internal-ca" \
  ttl=87600h \
  key_type=rsa \
  key_bits=4096 > /dev/null
vault write pki/roles/ilbuy-internal \
  allowed_domains="ilbuy-ops.svc.cluster.local,ilbuy-l1.svc.cluster.local,ilbuy-l2.svc.cluster.local,ilbuy-l3.svc.cluster.local,ilbuy-l4.svc.cluster.local,ilbuy-l5.svc.cluster.local,ilbuy-l6.svc.cluster.local,ilbuy-l7.svc.cluster.local,ilbuy-l8.svc.cluster.local,ilbuy-infra.svc.cluster.local" \
  allow_subdomains=true \
  max_ttl=720h
ok "PKI 内部 CA 配置完成"

# ── Step 3: 写入初始 Secret ──────────────────────────────────────────────────
log "--- 写入基础设施 Secret ---"

vault kv put secret/ilbuy/infra/rabbitmq \
  url="amqp://ilbuy:${RABBITMQ_PASSWORD:-changeme}@rabbitmq.ilbuy-infra.svc.cluster.local:5672/ilbuy" \
  username="ilbuy" \
  password="${RABBITMQ_PASSWORD:-changeme}"

vault kv put secret/ilbuy/infra/redis \
  host="redis.ilbuy-infra.svc.cluster.local" \
  port="6379" \
  password="${REDIS_PASSWORD:-}"

vault kv put secret/ilbuy/infra/clickhouse \
  host="clickhouse.ilbuy-infra.svc.cluster.local" \
  port="9000" \
  username="default" \
  password="${CLICKHOUSE_PASSWORD:-changeme}"

ok "基础设施 Secret 写入完成"

# ── Step 4: 配置 K8s Auth ────────────────────────────────────────────────────
log "--- 配置 Kubernetes Auth ---"

vault auth enable kubernetes 2>/dev/null || log "kubernetes auth 已启用"

# 获取 K8s 集群信息
K8S_HOST=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || echo "https://kubernetes.default.svc")
K8S_CA=$(kubectl config view --minify --flatten -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' 2>/dev/null | base64 -d || cat /var/run/secrets/kubernetes.io/serviceaccount/ca.crt 2>/dev/null || echo "")
SA_TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token 2>/dev/null || echo "")

if [ -n "${SA_TOKEN}" ] && [ -n "${K8S_CA}" ]; then
  vault write auth/kubernetes/config \
    kubernetes_host="${K8S_HOST}" \
    kubernetes_ca_cert="${K8S_CA}" \
    token_reviewer_jwt="${SA_TOKEN}"
  ok "K8s Auth 配置完成"
else
  log "⚠️  无法自动配置 K8s Auth，请手动执行 vault write auth/kubernetes/config ..."
fi

# ── Step 5: 写入策略 ─────────────────────────────────────────────────────────
log "--- 写入访问策略 ---"
vault policy write ilbuy-microservice "$(dirname "$0")/policies/ilbuy-policy.hcl"
ok "ilbuy-microservice 策略写入完成"

# ── Step 6: 创建 K8s Auth Role ───────────────────────────────────────────────
log "--- 创建 K8s Auth Role ---"

# 为所有 ilbuy-* 命名空间的 ServiceAccount 创建统一 Role
vault write auth/kubernetes/role/ilbuy-services \
  bound_service_account_names="ilbuy-svc,default" \
  bound_service_account_namespaces="ilbuy-l1,ilbuy-l2,ilbuy-l3,ilbuy-l4,ilbuy-l5,ilbuy-l6,ilbuy-l7,ilbuy-l8,ilbuy-infra" \
  policies="ilbuy-microservice" \
  ttl="1h" \
  max_ttl="24h"

ok "K8s Auth Role 配置完成"

log ""
log "=== Vault 初始化完成 ==="
log "Vault UI: ${VAULT_ADDR}/ui"
if [ -f "${INIT_OUTPUT_FILE}" ]; then
  log "⚠️  Init Key 文件: ${INIT_OUTPUT_FILE}  — 请加密保存后删除此文件！"
fi
