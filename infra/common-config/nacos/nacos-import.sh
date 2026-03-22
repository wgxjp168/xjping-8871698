#!/usr/bin/env bash
# ============================================================
# Nacos 配置批量导入脚本
# 用途：将 dev/ 或 prod/ 目录下的 YAML 配置文件批量导入 Nacos
# 用法：
#   bash nacos-import.sh dev    # 导入开发环境配置
#   bash nacos-import.sh prod   # 导入生产环境配置
# 依赖：curl, jq
# ============================================================
set -euo pipefail

# ──────────────────────────────────────────────────────────
#  参数
# ──────────────────────────────────────────────────────────
ENV="${1:-dev}"
NACOS_HOST="${NACOS_HOST:-http://127.0.0.1:8848}"
NACOS_USER="${NACOS_USER:-nacos}"
NACOS_PASS="${NACOS_PASS:-nacos}"
GROUP="DEFAULT_GROUP"

# 命名空间 ID（需提前在 Nacos 控制台创建）
if [[ "$ENV" == "prod" ]]; then
    NAMESPACE_ID="${NACOS_PROD_NS:-ilbuy-prod}"
    CONFIG_DIR="$(dirname "$0")/prod"
else
    NAMESPACE_ID="${NACOS_DEV_NS:-ilbuy-dev}"
    CONFIG_DIR="$(dirname "$0")/dev"
fi

# ──────────────────────────────────────────────────────────
#  颜色输出
# ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ──────────────────────────────────────────────────────────
#  获取 Nacos Access Token
# ──────────────────────────────────────────────────────────
get_token() {
    local token
    token=$(curl -sf -X POST "${NACOS_HOST}/nacos/v1/auth/login" \
        -d "username=${NACOS_USER}&password=${NACOS_PASS}" \
        | jq -r '.accessToken' 2>/dev/null) || true

    if [[ -z "$token" || "$token" == "null" ]]; then
        warn "Nacos 认证失败或未开启鉴权，将不带 Token 导入"
        echo ""
    else
        echo "$token"
    fi
}

# ──────────────────────────────────────────────────────────
#  确保命名空间存在
# ──────────────────────────────────────────────────────────
ensure_namespace() {
    local token="$1"
    local auth_param=""
    [[ -n "$token" ]] && auth_param="&accessToken=${token}"

    # 查询现有命名空间
    local exists
    exists=$(curl -sf "${NACOS_HOST}/nacos/v1/console/namespaces${auth_param}" \
        | jq -r --arg ns "$NAMESPACE_ID" \
          '.data[]? | select(.namespace == $ns) | .namespace' 2>/dev/null) || true

    if [[ -z "$exists" ]]; then
        info "创建命名空间: ${NAMESPACE_ID}"
        curl -sf -X POST "${NACOS_HOST}/nacos/v1/console/namespaces" \
            -d "customNamespaceId=${NAMESPACE_ID}&namespaceName=ilbuy-${ENV}&namespaceDesc=ILbuy ${ENV} environment${auth_param}" > /dev/null
    else
        info "命名空间已存在: ${NAMESPACE_ID}"
    fi
}

# ──────────────────────────────────────────────────────────
#  导入单个配置文件
# ──────────────────────────────────────────────────────────
import_config() {
    local file="$1"
    local token="$2"
    local data_id
    data_id=$(basename "$file")

    local content
    content=$(cat "$file")
    local auth_param=""
    [[ -n "$token" ]] && auth_param="&accessToken=${token}"

    # 先尝试删除旧配置（忽略错误）
    curl -sf -X DELETE \
        "${NACOS_HOST}/nacos/v1/cs/configs?dataId=${data_id}&group=${GROUP}&tenant=${NAMESPACE_ID}${auth_param}" \
        > /dev/null 2>&1 || true

    # 发布新配置
    local resp
    resp=$(curl -sf -X POST "${NACOS_HOST}/nacos/v1/cs/configs" \
        --data-urlencode "dataId=${data_id}" \
        --data-urlencode "group=${GROUP}" \
        --data-urlencode "tenant=${NAMESPACE_ID}" \
        --data-urlencode "content=${content}" \
        --data-urlencode "type=yaml" \
        ${auth_param:+-d "accessToken=${token}"}) || { error "导入失败: ${data_id}"; return 1; }

    if [[ "$resp" == "true" ]]; then
        info "✓ 导入成功: ${data_id}"
    else
        error "✗ 导入失败: ${data_id} (response: ${resp})"
        return 1
    fi
}

# ──────────────────────────────────────────────────────────
#  主流程
# ──────────────────────────────────────────────────────────
main() {
    info "=== ILbuy Nacos 配置导入 ==="
    info "环境: ${ENV}  |  Nacos: ${NACOS_HOST}  |  Namespace: ${NAMESPACE_ID}"
    info "配置目录: ${CONFIG_DIR}"

    if [[ ! -d "$CONFIG_DIR" ]]; then
        error "配置目录不存在: ${CONFIG_DIR}"
        exit 1
    fi

    # 检查 Nacos 连通性
    if ! curl -sf "${NACOS_HOST}/nacos/v1/console/health/ready" > /dev/null 2>&1; then
        error "Nacos 服务不可达: ${NACOS_HOST}"
        exit 1
    fi
    info "Nacos 连接正常"

    # 获取 Token
    local token
    token=$(get_token)

    # 确保命名空间
    ensure_namespace "$token"

    # 遍历所有 YAML 文件
    local success=0 fail=0
    for f in "${CONFIG_DIR}"/*.yaml "${CONFIG_DIR}"/*.yml; do
        [[ -f "$f" ]] || continue
        if import_config "$f" "$token"; then
            ((success++)) || true
        else
            ((fail++)) || true
        fi
    done

    echo ""
    info "=== 导入完成：成功 ${success} 个，失败 ${fail} 个 ==="
    [[ $fail -eq 0 ]] || exit 1
}

main "$@"
