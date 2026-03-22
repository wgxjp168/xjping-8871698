#!/usr/bin/env bash
# ============================================================
# ILbuy 镜像构建脚本
# 用途：构建所有微服务 Docker 镜像并推送到镜像仓库
# 用法：
#   bash build.sh                        # 构建所有服务
#   bash build.sh gateway-svc            # 构建单个服务
#   bash build.sh -t v1.2.0              # 指定 tag
#   bash build.sh -t v1.2.0 --push       # 构建并推送
#   bash build.sh --no-cache             # 禁用缓存
# 依赖：docker, maven (Java 服务), python3 (Python 服务)
# ============================================================
set -euo pipefail

# ──────────────────────────────────────────────────────────
#  默认配置
# ──────────────────────────────────────────────────────────
REGISTRY="${REGISTRY:-registry.cn-hangzhou.aliyuncs.com/ilbuy}"
IMAGE_TAG="${IMAGE_TAG:-$(git describe --tags --always --dirty 2>/dev/null || echo 'dev')}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PUSH=false
NO_CACHE=""
TARGET_SVC=""
PARALLEL=4

# Java 微服务列表（Maven 模块名 → 服务名 → 端口）
declare -A JAVA_SVCS=(
  [gateway-svc]="gateway-svc:8080"
  [user-svc]="user-svc:8081"
  [product-svc]="product-svc:8082"
  [order-svc]="order-svc:8083"
  [supplier-svc]="supplier-svc:8084"
  [finance-svc]="finance-svc:8086"
  [message-svc]="message-svc:8087"
  [ai-svc]="ai-svc:8089"
)
# Python 微服务列表
declare -A PYTHON_SVCS=(
  [biz-data-svc]="biz_data_svc:8088"
)

# ──────────────────────────────────────────────────────────
#  颜色输出
# ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
section() { echo -e "\n${BLUE}══ $* ══${NC}\n"; }

# ──────────────────────────────────────────────────────────
#  参数解析
# ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--tag)     IMAGE_TAG="$2"; shift 2 ;;
    --push)       PUSH=true; shift ;;
    --no-cache)   NO_CACHE="--no-cache"; shift ;;
    -r|--registry) REGISTRY="$2"; shift 2 ;;
    -j|--parallel) PARALLEL="$2"; shift 2 ;;
    -h|--help)
      grep '^# ' "$0" | head -12 | sed 's/^# //'
      exit 0 ;;
    -*)
      error "未知参数: $1"
      exit 1 ;;
    *)
      TARGET_SVC="$1"; shift ;;
  esac
done

# ──────────────────────────────────────────────────────────
#  Maven 编译打包（Java 服务）
# ──────────────────────────────────────────────────────────
maven_build() {
  local svc="$1"
  section "Maven 构建: ${svc}"
  cd "${PROJECT_ROOT}"

  if [[ -n "$TARGET_SVC" && "$TARGET_SVC" != "$svc" ]]; then
    return 0
  fi

  # 找到对应的 Maven 模块目录
  local module_dir
  module_dir=$(find . -maxdepth 3 -name "pom.xml" -path "*/${svc}/*" | head -1 | xargs dirname)
  if [[ -z "$module_dir" ]]; then
    warn "未找到 Maven 模块: ${svc}，跳过 Maven 构建"
    return 0
  fi

  info "Maven 打包: ${module_dir}"
  mvn -f "${module_dir}/pom.xml" clean package -DskipTests -q
  info "✓ Maven 构建完成: ${svc}"
}

# ──────────────────────────────────────────────────────────
#  Docker 镜像构建
# ──────────────────────────────────────────────────────────
docker_build() {
  local svc="$1"
  local context_dir="$2"
  local image="${REGISTRY}/${svc}:${IMAGE_TAG}"
  local latest="${REGISTRY}/${svc}:latest"

  section "Docker 构建: ${svc}"

  if [[ ! -f "${context_dir}/Dockerfile" ]]; then
    error "Dockerfile 不存在: ${context_dir}/Dockerfile"
    return 1
  fi

  info "构建镜像: ${image}"
  docker build ${NO_CACHE} \
    --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --build-arg GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
    --build-arg IMAGE_TAG="${IMAGE_TAG}" \
    -t "${image}" \
    -t "${latest}" \
    "${context_dir}"

  info "✓ 构建完成: ${image}"

  if [[ "$PUSH" == "true" ]]; then
    info "推送镜像: ${image}"
    docker push "${image}"
    docker push "${latest}"
    info "✓ 推送完成: ${image}"
  fi
}

# ──────────────────────────────────────────────────────────
#  查找服务目录
# ──────────────────────────────────────────────────────────
find_svc_dir() {
  local svc="$1"
  # 优先在 services/ 目录下查找
  local dir
  dir=$(find "${PROJECT_ROOT}" -maxdepth 3 -type d -name "${svc}" | head -1)
  echo "$dir"
}

# ──────────────────────────────────────────────────────────
#  构建单个服务
# ──────────────────────────────────────────────────────────
build_svc() {
  local svc="$1"
  local svc_dir
  svc_dir=$(find_svc_dir "$svc")

  if [[ -z "$svc_dir" ]]; then
    warn "未找到服务目录: ${svc}，跳过"
    return 0
  fi

  docker_build "$svc" "$svc_dir"
}

# ──────────────────────────────────────────────────────────
#  主流程
# ──────────────────────────────────────────────────────────
main() {
  section "ILbuy 镜像构建"
  info "镜像仓库: ${REGISTRY}"
  info "镜像标签: ${IMAGE_TAG}"
  info "项目根目录: ${PROJECT_ROOT}"
  [[ "$PUSH" == "true" ]] && info "构建后推送: 是"
  [[ -n "$NO_CACHE" ]] && warn "已禁用 Docker 构建缓存"

  local build_start
  build_start=$(date +%s)

  if [[ -n "$TARGET_SVC" ]]; then
    # 构建单个服务
    info "目标服务: ${TARGET_SVC}"
    if [[ -v JAVA_SVCS[$TARGET_SVC] ]]; then
      maven_build "$TARGET_SVC"
    fi
    build_svc "$TARGET_SVC"
  else
    # 构建所有服务
    # 先执行 Maven 全量构建（更高效）
    section "Maven 全量构建"
    cd "${PROJECT_ROOT}"
    if find . -maxdepth 2 -name "pom.xml" | grep -q .; then
      mvn clean package -DskipTests -q -T "${PARALLEL}" || warn "Maven 构建部分失败，继续 Docker 构建"
      info "✓ Maven 全量构建完成"
    fi

    # 构建 Java 服务镜像
    for svc in "${!JAVA_SVCS[@]}"; do
      build_svc "$svc"
    done

    # 构建 Python 服务镜像
    for svc in "${!PYTHON_SVCS[@]}"; do
      build_svc "$svc"
    done
  fi

  local build_end elapsed
  build_end=$(date +%s)
  elapsed=$((build_end - build_start))
  section "构建完成 (耗时 ${elapsed}s)"

  # 汇总镜像信息
  info "已构建镜像列表："
  docker images "${REGISTRY}/*" --format "  {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" 2>/dev/null | grep "${IMAGE_TAG}" || true
}

main "$@"
