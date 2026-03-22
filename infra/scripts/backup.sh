#!/usr/bin/env bash
# ============================================================
# ILbuy 数据备份脚本
# 用途：备份 MySQL、Redis、ClickHouse、MinIO 数据
# 用法：
#   bash backup.sh                     # 备份所有
#   bash backup.sh mysql               # 仅备份 MySQL
#   bash backup.sh redis               # 仅备份 Redis
#   bash backup.sh clickhouse          # 仅备份 ClickHouse
#   bash backup.sh minio               # 仅备份 MinIO
#   bash backup.sh --clean 7           # 清理 7 天以前的备份
# 依赖：docker, mysqldump（MySQL备份），mc（MinIO备份），tar, gzip
# ============================================================
set -euo pipefail

# ──────────────────────────────────────────────────────────
#  配置
# ──────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/data/ilbuy/backups}"
DATE_STR="$(date +%Y%m%d_%H%M%S)"
RETAIN_DAYS="${RETAIN_DAYS:-30}"

# MySQL
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-ilbuy123}"
MYSQL_DATABASES=( user_db product_db order_db supplier_db finance_db message_db nacos_config )

# Redis
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-ilbuy123}"
REDIS_CONTAINER="${REDIS_CONTAINER:-ilbuy-redis}"

# ClickHouse
CH_HOST="${CH_HOST:-127.0.0.1}"
CH_PORT="${CH_PORT:-8123}"
CH_CONTAINER="${CH_CONTAINER:-ilbuy-clickhouse}"
CH_DATABASES=( ilbuy_analytics )

# MinIO
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://127.0.0.1:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKETS=( ilbuy-reports ilbuy-images ilbuy-contracts )
MINIO_BACKUP_BUCKET="${MINIO_BACKUP_BUCKET:-}"   # 如设置，则同步到远端备份桶

# ──────────────────────────────────────────────────────────
#  颜色输出
# ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
section() { echo -e "\n${BLUE}══ $* ══${NC}\n"; }

# ──────────────────────────────────────────────────────────
#  初始化目录
# ──────────────────────────────────────────────────────────
init_dirs() {
  mkdir -p "${BACKUP_DIR}"/{mysql,redis,clickhouse,minio}
}

# ──────────────────────────────────────────────────────────
#  MySQL 备份
# ──────────────────────────────────────────────────────────
backup_mysql() {
  section "MySQL 备份"
  local mysql_dir="${BACKUP_DIR}/mysql/${DATE_STR}"
  mkdir -p "$mysql_dir"

  local success=0 fail=0

  for db in "${MYSQL_DATABASES[@]}"; do
    local dump_file="${mysql_dir}/${db}.sql.gz"
    info "备份数据库: ${db} -> ${dump_file}"

    if docker exec ilbuy-mysql mysqldump \
        -uroot -p"${MYSQL_ROOT_PASSWORD}" \
        --single-transaction \
        --routines \
        --triggers \
        --events \
        --set-gtid-purged=OFF \
        "${db}" 2>/dev/null | gzip > "${dump_file}"; then
      local size
      size=$(du -sh "${dump_file}" | cut -f1)
      info "✓ ${db} 备份完成 (${size})"
      ((success++)) || true
    else
      error "✗ ${db} 备份失败"
      rm -f "${dump_file}"
      ((fail++)) || true
    fi
  done

  info "MySQL 备份完成：成功 ${success} 个，失败 ${fail} 个"
  [[ $fail -eq 0 ]] || return 1
}

# ──────────────────────────────────────────────────────────
#  Redis 备份（触发 BGSAVE，然后复制 dump.rdb）
# ──────────────────────────────────────────────────────────
backup_redis() {
  section "Redis 备份"
  local redis_dir="${BACKUP_DIR}/redis"
  mkdir -p "$redis_dir"

  info "触发 Redis BGSAVE..."
  docker exec "${REDIS_CONTAINER}" \
    redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning BGSAVE 2>/dev/null

  # 等待 BGSAVE 完成
  local timeout=60 elapsed=0
  while [[ $elapsed -lt $timeout ]]; do
    local status
    status=$(docker exec "${REDIS_CONTAINER}" \
      redis-cli -a "${REDIS_PASSWORD}" --no-auth-warning LASTSAVE 2>/dev/null)
    sleep 2; elapsed=$((elapsed + 2))
    local current_time
    current_time=$(date +%s)
    [[ $((current_time - status)) -lt 5 ]] && break
  done

  local dump_file="${redis_dir}/dump_${DATE_STR}.rdb.gz"
  info "复制 RDB 文件: ${dump_file}"
  docker cp "${REDIS_CONTAINER}:/data/dump.rdb" - 2>/dev/null | gzip > "${dump_file}"

  local size
  size=$(du -sh "${dump_file}" | cut -f1)
  info "✓ Redis 备份完成 (${size})"
}

# ──────────────────────────────────────────────────────────
#  ClickHouse 备份（通过 clickhouse-backup 或 CREATE TABLE AS SELECT）
# ──────────────────────────────────────────────────────────
backup_clickhouse() {
  section "ClickHouse 备份"
  local ch_dir="${BACKUP_DIR}/clickhouse/${DATE_STR}"
  mkdir -p "$ch_dir"

  for db in "${CH_DATABASES[@]}"; do
    info "备份 ClickHouse 数据库: ${db}"

    # 获取所有表
    local tables
    tables=$(docker exec "${CH_CONTAINER}" \
      clickhouse-client --query "SHOW TABLES FROM ${db}" 2>/dev/null || echo "")

    if [[ -z "$tables" ]]; then
      warn "数据库 ${db} 为空或不存在，跳过"
      continue
    fi

    local db_dir="${ch_dir}/${db}"
    mkdir -p "$db_dir"

    # 导出建表 DDL
    docker exec "${CH_CONTAINER}" \
      clickhouse-client --query "SHOW CREATE DATABASE ${db}" \
      > "${db_dir}/create_database.sql" 2>/dev/null || true

    # 逐表导出数据（Parquet 格式）
    while IFS= read -r table; do
      [[ -z "$table" ]] && continue
      local table_file="${db_dir}/${table}.parquet"
      info "  导出表: ${db}.${table}"
      docker exec "${CH_CONTAINER}" \
        clickhouse-client --query "SELECT * FROM ${db}.${table} FORMAT Parquet" \
        > "${table_file}" 2>/dev/null || warn "  跳过: ${table}"

      # 保存建表语句
      docker exec "${CH_CONTAINER}" \
        clickhouse-client --query "SHOW CREATE TABLE ${db}.${table}" \
        > "${db_dir}/${table}.ddl.sql" 2>/dev/null || true
    done <<< "$tables"

    # 打包压缩
    local archive="${ch_dir}/${db}.tar.gz"
    tar -czf "$archive" -C "$ch_dir" "$db"
    rm -rf "$db_dir"
    local size
    size=$(du -sh "$archive" | cut -f1)
    info "✓ ${db} 备份完成 (${size})"
  done
}

# ──────────────────────────────────────────────────────────
#  MinIO 备份（通过 mc mirror 同步到本地目录）
# ──────────────────────────────────────────────────────────
backup_minio() {
  section "MinIO 备份"
  local minio_dir="${BACKUP_DIR}/minio/${DATE_STR}"
  mkdir -p "$minio_dir"

  # 配置 mc alias
  docker run --rm \
    --network ilbuy-middleware_ilbuy-net \
    -v "${minio_dir}:/backup" \
    minio/mc:latest \
    sh -c "
      mc alias set local ${MINIO_ENDPOINT} ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY} --api s3v4;
      $(for bucket in "${MINIO_BUCKETS[@]}"; do
          echo "echo 'Backing up bucket: ${bucket}';";
          echo "mc mirror --preserve local/${bucket} /backup/${bucket} || true;";
        done)
    " 2>/dev/null || warn "MinIO 备份部分失败"

  # 打包压缩
  local archive="${BACKUP_DIR}/minio/minio_${DATE_STR}.tar.gz"
  if [[ -d "$minio_dir" ]]; then
    tar -czf "$archive" -C "${BACKUP_DIR}/minio" "${DATE_STR}"
    rm -rf "$minio_dir"
    local size
    size=$(du -sh "$archive" | cut -f1)
    info "✓ MinIO 备份完成 (${size})"
  fi
}

# ──────────────────────────────────────────────────────────
#  清理旧备份
# ──────────────────────────────────────────────────────────
clean_old_backups() {
  local days="${1:-$RETAIN_DAYS}"
  section "清理 ${days} 天前的备份"

  local count=0
  while IFS= read -r f; do
    rm -rf "$f"
    info "删除: $f"
    ((count++)) || true
  done < <(find "${BACKUP_DIR}" -maxdepth 3 \
    \( -name "*.sql.gz" -o -name "*.rdb.gz" -o -name "*.tar.gz" -o -name "*.parquet" \) \
    -mtime "+${days}" 2>/dev/null)

  info "✓ 共清理 ${count} 个旧备份文件"
}

# ──────────────────────────────────────────────────────────
#  主流程
# ──────────────────────────────────────────────────────────
main() {
  local target="${1:-all}"

  # 特殊参数处理
  if [[ "$target" == "--clean" ]]; then
    clean_old_backups "${2:-$RETAIN_DAYS}"
    return 0
  fi

  section "ILbuy 数据备份 (${DATE_STR})"
  info "备份目录: ${BACKUP_DIR}"
  init_dirs

  local backup_start
  backup_start=$(date +%s)

  case "$target" in
    all)
      backup_mysql
      backup_redis
      backup_clickhouse
      backup_minio
      ;;
    mysql)       backup_mysql ;;
    redis)       backup_redis ;;
    clickhouse)  backup_clickhouse ;;
    minio)       backup_minio ;;
    *)
      error "未知目标: ${target}"
      echo "可选: all | mysql | redis | clickhouse | minio | --clean [days]"
      exit 1 ;;
  esac

  # 自动清理旧备份
  clean_old_backups "${RETAIN_DAYS}"

  local backup_end elapsed
  backup_end=$(date +%s)
  elapsed=$((backup_end - backup_start))

  section "备份完成 (耗时 ${elapsed}s)"
  info "备份目录大小: $(du -sh "${BACKUP_DIR}" | cut -f1)"
}

main "$@"
