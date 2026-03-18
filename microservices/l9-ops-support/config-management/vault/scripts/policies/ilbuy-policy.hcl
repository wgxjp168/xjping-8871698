# =============================================================================
# ILbuy Vault Policy — 微服务 Secret 访问策略
# =============================================================================

# ── 数据库凭据（动态 Secret）────────────────────────────────────────────────
path "database/creds/ilbuy-readonly" {
  capabilities = ["read"]
}

path "database/creds/ilbuy-readwrite" {
  capabilities = ["read"]
}

# ── 各层静态 Secret ──────────────────────────────────────────────────────────
# L1 用户权益层
path "secret/data/ilbuy/l1/*" {
  capabilities = ["read", "list"]
}

# L2 AI决策层
path "secret/data/ilbuy/l2/*" {
  capabilities = ["read", "list"]
}

# L3 数据处理层
path "secret/data/ilbuy/l3/*" {
  capabilities = ["read", "list"]
}

# L4 数据存储层
path "secret/data/ilbuy/l4/*" {
  capabilities = ["read", "list"]
}

# L5 报告生成层
path "secret/data/ilbuy/l5/*" {
  capabilities = ["read", "list"]
}

# L6 交付履约层
path "secret/data/ilbuy/l6/*" {
  capabilities = ["read", "list"]
}

# L7 商业变现层（支付密钥只读）
path "secret/data/ilbuy/l7/*" {
  capabilities = ["read", "list"]
}

# L8 反馈优化层
path "secret/data/ilbuy/l8/*" {
  capabilities = ["read", "list"]
}

# ── 公共基础设施密钥 ────────────────────────────────────────────────────────
path "secret/data/ilbuy/infra/rabbitmq" {
  capabilities = ["read"]
}

path "secret/data/ilbuy/infra/clickhouse" {
  capabilities = ["read"]
}

path "secret/data/ilbuy/infra/redis" {
  capabilities = ["read"]
}

# ── PKI 证书（服务间 mTLS）──────────────────────────────────────────────────
path "pki/issue/ilbuy-internal" {
  capabilities = ["create", "update"]
}

path "pki/cert/*" {
  capabilities = ["read"]
}

# ── Token 自更新 ─────────────────────────────────────────────────────────────
path "auth/token/renew-self" {
  capabilities = ["update"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

# ── Transit 加密（敏感字段加解密）──────────────────────────────────────────
path "transit/encrypt/ilbuy-data" {
  capabilities = ["create", "update"]
}

path "transit/decrypt/ilbuy-data" {
  capabilities = ["create", "update"]
}
