#!/usr/bin/env bash
# =============================================================================
# ILbuy 数据备份脚本
# 覆盖：PostgreSQL + Elasticsearch + Nacos + 模型文件
# 用法: bash backup.sh [--target s3|local] [--bucket <bucket>] [--dry-run]
# =============================================================================
set -euo pipefail

# ── 配置 ────────────────────────────────────────────────────────────────────
BACKUP_TARGET="${BACKUP_TARGET:-local}"      # local | s3
BACKUP_ROOT="${BACKUP_ROOT:-/backup/ilbuy}"
S3_BUCKET="${S3_BUCKET:-s3://ilbuy-backups}"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DRY_RUN="${DRY_RUN:-false}"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
ok()   { echo -e "\033[32m[ OK ]\033[0m  $*"; }
warn() { echo -e "\033[33m[WARN]\033[0m  $*"; }
die()  { echo -e "\033[31m[ERR ]\033[0m  $*" >&2; exit 1; }
run()  { if [ "${DRY_RUN}" = true ]; then echo "[DRY-RUN] $*"; else eval "$*"; fi; }

for arg in "$@"; do
    case "${arg}" in
        --dry-run) DRY_RUN=true ;;
        --target=*) BACKUP_TARGET="${arg#*=}" ;;
        --bucket=*) S3_BUCKET="${arg#*=}" ;;
    esac
done

BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
[ "${DRY_RUN}" = false ] && mkdir -p "${BACKUP_DIR}"

log "=== ILbuy 数据备份 ==="
log "时间戳: ${TIMESTAMP}"
log "目标:   ${BACKUP_TARGET}"
[ "${DRY_RUN}" = true ] && warn "DRY RUN 模式"

# ── 函数: 上传到 S3 ──────────────────────────────────────────────────────────
upload_to_s3() {
    local local_path="$1"
    local s3_key="$2"
    if command -v aws > /dev/null && [ "${BACKUP_TARGET}" = "s3" ]; then
        run aws s3 cp "${local_path}" "${S3_BUCKET}/${s3_key}"
    fi
}

# ── 1. PostgreSQL 备份 ───────────────────────────────────────────────────────
log "--- PostgreSQL 全库备份 ---"
DATABASES=(ilbuy_l1 ilbuy_l2 ilbuy_l3 ilbuy_l5 ilbuy_l6 ilbuy_l7 ilbuy_l8 nacos_config sonarqube)

for DB in "${DATABASES[@]}"; do
    DUMP_FILE="${BACKUP_DIR}/postgres_${DB}_${TIMESTAMP}.sql.gz"
    log "备份数据库: ${DB} → ${DUMP_FILE}"
    run kubectl exec -n ilbuy-infra postgres-0 -- \
        pg_dump -U ilbuy "${DB}" \| gzip \> "${DUMP_FILE}" || \
        warn "数据库 ${DB} 备份失败，跳过"
    upload_to_s3 "${DUMP_FILE}" "postgres/${TIMESTAMP}/${DB}.sql.gz"
done

ok "PostgreSQL 备份完成"

# ── 2. Elasticsearch 快照备份 ────────────────────────────────────────────────
log "--- Elasticsearch 快照备份 ---"
ES_HOST="https://elasticsearch-client.ilbuy-ops.svc.cluster.local:9200"
ES_USER="elastic"
ES_PASS="${ELASTIC_PASSWORD:-changeme}"
SNAPSHOT_NAME="ilbuy-backup-${TIMESTAMP}"

# 注册快照仓库（需要预先配置 S3 仓库）
run kubectl exec -n ilbuy-ops elasticsearch-0 -- curl -sf -X PUT \
    "${ES_HOST}/_snapshot/ilbuy-backups/${SNAPSHOT_NAME}" \
    -u "${ES_USER}:${ES_PASS}" \
    -H "Content-Type: application/json" \
    --insecure \
    -d "{\"indices\":\"ilbuy-*\",\"ignore_unavailable\":true,\"include_global_state\":false}" || \
    warn "ES 快照创建失败"

ok "Elasticsearch 快照备份完成: ${SNAPSHOT_NAME}"

# ── 3. Nacos 配置备份 ────────────────────────────────────────────────────────
log "--- Nacos 配置备份 ---"
NACOS_HOST="${NACOS_HOST:-http://nacos-client.ilbuy-ops.svc.cluster.local:8848}"
NACOS_BACKUP="${BACKUP_DIR}/nacos_configs_${TIMESTAMP}"
mkdir -p "${NACOS_BACKUP}" 2>/dev/null || true

for NS in ilbuy-dev ilbuy-staging ilbuy-prod; do
    NS_FILE="${NACOS_BACKUP}/${NS}.json"
    log "备份 Nacos 命名空间: ${NS}"
    run curl -sf "${NACOS_HOST}/nacos/v1/cs/configs?tenant=${NS}&pageSize=1000&pageNo=1" \
        \> "${NS_FILE}" || warn "Nacos ${NS} 备份失败"
done

NACOS_ARCHIVE="${BACKUP_DIR}/nacos_${TIMESTAMP}.tar.gz"
run tar -czf "${NACOS_ARCHIVE}" -C "${BACKUP_DIR}" "nacos_configs_${TIMESTAMP}"
upload_to_s3 "${NACOS_ARCHIVE}" "nacos/${TIMESTAMP}/configs.tar.gz"

ok "Nacos 配置备份完成"

# ── 4. 模型文件备份 ──────────────────────────────────────────────────────────
log "--- ML 模型文件备份 ---"
MODEL_BACKUP="${BACKUP_DIR}/models_${TIMESTAMP}.tar.gz"

# 从 model-iteration-svc Pod 导出模型
MODEL_POD=$(kubectl get pods -n ilbuy-l8 -l app=model-iteration-svc \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "${MODEL_POD}" ]; then
    run kubectl exec "${MODEL_POD}" -n ilbuy-l8 -- \
        tar -czf - /app/model_store \| cat \> "${MODEL_BACKUP}"
    upload_to_s3 "${MODEL_BACKUP}" "models/${TIMESTAMP}/model_store.tar.gz"
    ok "模型文件备份完成"
else
    warn "未找到 model-iteration-svc Pod，跳过模型备份"
fi

# ── 5. 清理旧备份 ────────────────────────────────────────────────────────────
log "--- 清理 ${RETENTION_DAYS} 天前的本地备份 ---"
run find "${BACKUP_ROOT}" -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} + 2>/dev/null || true
ok "旧备份清理完成"

# ── 6. 备份报告 ──────────────────────────────────────────────────────────────
echo ""
log "=== 备份完成报告 ==="
if [ "${DRY_RUN}" = false ]; then
    BACKUP_SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1 || echo "未知")
    log "备份目录: ${BACKUP_DIR}"
    log "备份大小: ${BACKUP_SIZE}"
fi
log "时间戳: ${TIMESTAMP}"
[ "${BACKUP_TARGET}" = "s3" ] && log "S3 路径: ${S3_BUCKET}/${TIMESTAMP}/"
ok "所有备份任务完成"
