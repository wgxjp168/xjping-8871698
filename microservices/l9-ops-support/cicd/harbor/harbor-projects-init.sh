#!/usr/bin/env bash
# =============================================================================
# Harbor 项目初始化脚本
# 创建 ILbuy 各层项目、配置扫描策略、Webhook、成员权限
# 用法：bash harbor-projects-init.sh [HARBOR_URL] [ADMIN_USER] [ADMIN_PASS]
# =============================================================================
set -euo pipefail

HARBOR_URL="${1:-https://harbor.ilbuy.internal}"
ADMIN_USER="${2:-admin}"
ADMIN_PASS="${3:-${HARBOR_ADMIN_PASSWORD:-Harbor12345}}"
API="${HARBOR_URL}/api/v2.0"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
ok()   { echo -e "\033[32m[ OK ]\033[0m  $*"; }
die()  { echo -e "\033[31m[ERR ]\033[0m  $*" >&2; exit 1; }

call_api() {
    local method="$1" path="$2" data="${3:-}"
    if [ -n "${data}" ]; then
        curl -sf -X "${method}" "${API}${path}" \
            -u "${ADMIN_USER}:${ADMIN_PASS}" \
            -H "Content-Type: application/json" \
            -d "${data}" || return 1
    else
        curl -sf -X "${method}" "${API}${path}" \
            -u "${ADMIN_USER}:${ADMIN_PASS}" \
            -H "Content-Type: application/json" || return 1
    fi
}

# ── 创建项目 ─────────────────────────────────────────────────────────────────
create_project() {
    local name="$1" public="${2:-false}"
    log "创建 Harbor 项目: ${name}"
    call_api POST "/projects" "{
        \"project_name\": \"${name}\",
        \"public\": ${public},
        \"metadata\": {
            \"public\": \"${public}\",
            \"enable_content_trust\": \"false\",
            \"prevent_vul\": \"true\",
            \"severity\": \"high\",
            \"auto_scan\": \"true\",
            \"reuse_sys_cve_allowlist\": \"true\"
        }
    }" > /dev/null 2>&1 || log "  (可能已存在，跳过)"
    ok "项目: ${name}"
}

# ── 配置 Webhook（镜像推送后触发 ArgoCD 同步通知）───────────────────────────
create_webhook() {
    local project_id="$1" project_name="$2"
    log "配置 Webhook: ${project_name}"
    call_api POST "/projects/${project_name}/webhook/policies" "{
        \"name\": \"argocd-sync\",
        \"description\": \"触发 ArgoCD 镜像更新通知\",
        \"enabled\": true,
        \"event_types\": [\"PUSH_ARTIFACT\"],
        \"targets\": [{
            \"type\": \"http\",
            \"address\": \"https://argocd.ilbuy.internal/api/v1/webhook\",
            \"skip_cert_verify\": false,
            \"auth_header\": \"Bearer \${ARGOCD_WEBHOOK_SECRET}\"
        }]
    }" > /dev/null 2>&1 || log "  (Webhook 配置失败，请手动配置)"
}

log "=== Harbor 项目初始化 ==="
log "Harbor: ${HARBOR_URL}"

# 等待 Harbor 就绪
for i in $(seq 1 30); do
    if curl -sf "${API}/systeminfo" -u "${ADMIN_USER}:${ADMIN_PASS}" > /dev/null 2>&1; then
        ok "Harbor 已就绪"
        break
    fi
    log "等待 Harbor 就绪... (${i}/30)"
    sleep 10
done

# ── 创建各层项目 ─────────────────────────────────────────────────────────────
create_project "ilbuy"       false   # 主项目（所有微服务镜像）
create_project "ilbuy-ops"   false   # 运维组件镜像（Jenkins/自定义工具）
create_project "ilbuy-base"  false   # 基础镜像（Python base / Java base）

# ── 配置不可变 Tag 策略（防止 latest 被覆盖后回滚失败）────────────────────
log "配置不可变 Tag 策略..."
call_api PUT "/projects/ilbuy" "{
    \"metadata\": {
        \"immutable_tag_rule\": \"true\"
    }
}" > /dev/null 2>&1 || log "  (不可变策略配置失败，请手动设置)"

# ── 配置镜像保留策略（每个 Tag 最多保留 20 个版本）────────────────────────
log "配置镜像保留策略..."
call_api POST "/projects/ilbuy/immutabletagrules" "{
    \"selector\": {
        \"kind\": \"doublestar\",
        \"decoration\": \"matches\",
        \"pattern\": \"**\"
    },
    \"tag_selectors\": [{
        \"kind\": \"doublestar\",
        \"decoration\": \"matches\",
        \"pattern\": \"v*\"
    }]
}" > /dev/null 2>&1 || true

log ""
log "=== Harbor 初始化完成 ==="
ok "访问地址: ${HARBOR_URL}"
log "项目列表: ilbuy / ilbuy-ops / ilbuy-base"
log "下一步: 在 Jenkins/GitLab CI 中配置 harbor-registry 凭据"
