# ============================================================
# HashiCorp Vault — ILbuy 访问策略
# 用途：控制各微服务对 Secret 的读取权限（最小权限原则）
# 应用方式：
#   vault policy write ilbuy-policy ilbuy-policy.hcl
#   vault write auth/kubernetes/role/ilbuy-app \
#     bound_service_account_names=ilbuy-app \
#     bound_service_account_namespaces=ilbuy \
#     policies=ilbuy-policy ttl=1h
# ============================================================

# ── 数据库密码（只读） ───────────────────────────────────
path "secret/data/ilbuy/db/*" {
  capabilities = ["read"]
}

# ── Redis 密码（只读） ───────────────────────────────────
path "secret/data/ilbuy/redis" {
  capabilities = ["read"]
}

# ── 第三方 API 密钥（只读） ──────────────────────────────
path "secret/data/ilbuy/api-keys/*" {
  capabilities = ["read"]
}

# ── JWT Secret（只读） ───────────────────────────────────
path "secret/data/ilbuy/jwt" {
  capabilities = ["read"]
}

# ── MinIO/OSS 密钥（只读） ───────────────────────────────
path "secret/data/ilbuy/storage/*" {
  capabilities = ["read"]
}

# ── 支付密钥（只读，仅 order-svc） ───────────────────────
path "secret/data/ilbuy/payment/*" {
  capabilities = ["read"]
}

# ── AI 大模型 API 密钥（只读，仅 ai-svc） ───────────────
path "secret/data/ilbuy/llm/*" {
  capabilities = ["read"]
}

# ── 短信/邮件密钥（只读，仅 message-svc） ───────────────
path "secret/data/ilbuy/notification/*" {
  capabilities = ["read"]
}

# ── 证书（只读） ─────────────────────────────────────────
path "secret/data/ilbuy/certs/*" {
  capabilities = ["read"]
}

# ── 禁止写入（防止 Secret 被服务篡改） ──────────────────
path "secret/data/ilbuy/*" {
  denied_parameters = {
    "*" = []
  }
  capabilities = ["read"]
}

# ── 允许 Token 自续期 ────────────────────────────────────
path "auth/token/renew-self" {
  capabilities = ["update"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
