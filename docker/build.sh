#!/usr/bin/env bash
# ============================================================
# RAGFlow Docker 构建 & 打包脚本
# 自动从 .env 读取 RAGFLOW_IMAGE，确保 tag 全程一致
#
# 用法:
#   ./build.sh              # 构建镜像
#   ./build.sh --no-cache   # 无缓存构建
#   ./build.sh pack         # 构建 + 打包为 .tar.gz
#   ./build.sh pack-only    # 仅打包（已构建过）
#   ./build.sh deploy       # 构建 + 部署到本地
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# ---------- 读取 RAGFLOW_IMAGE ----------
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found"
  exit 1
fi

IMAGE_TAG=$(grep -m1 '^RAGFLOW_IMAGE=' "$ENV_FILE" | cut -d'=' -f2)
if [[ -z "$IMAGE_TAG" ]]; then
  echo "ERROR: RAGFLOW_IMAGE not defined in $ENV_FILE"
  exit 1
fi

# 镜像名去掉 :tag 部分用于文件名
IMAGE_NAME_SAFE=$(echo "$IMAGE_TAG" | tr ':/' '-')
OUTPUT_DIR="$SCRIPT_DIR/dist"
TARBALL="$OUTPUT_DIR/${IMAGE_NAME_SAFE}.tar.gz"

# ---------- 默认 build args ----------
APT_MIRROR="${APT_MIRROR:-http://mirrors.aliyun.com/ubuntu}"
PYPI_MIRROR="${PYPI_MIRROR:-https://mirrors.aliyun.com/pypi/simple}"

# ---------- 函数 ----------
do_build() {
  echo "==> 构建镜像: $IMAGE_TAG"
  echo "==> 项目根目录: $PROJECT_ROOT"
  docker build \
    --build-arg APT_MIRROR="$APT_MIRROR" \
    --build-arg PYPI_MIRROR="$PYPI_MIRROR" \
    -f "$PROJECT_ROOT/Dockerfile" \
    -t "$IMAGE_TAG" \
    "${BUILD_ARGS[@]}" \
    "$PROJECT_ROOT"
  echo "==> 构建完成: $IMAGE_TAG"
}

do_pack() {
  mkdir -p "$OUTPUT_DIR"
  echo "==> 打包镜像: $IMAGE_TAG -> $TARBALL"
  docker save "$IMAGE_TAG" | gzip > "$TARBALL"
  echo "==> 打包完成: $TARBALL ($(du -h "$TARBALL" | cut -f1))"
  echo ""
  echo "云端部署步骤:"
  echo "  1. scp $TARBALL user@server:/path/"
  echo "  2. ssh user@server"
  echo "  3. docker load < ${IMAGE_NAME_SAFE}.tar.gz"
  echo "  4. cd docker && docker compose up -d --force-recreate ragflow-gpu"
}

do_deploy() {
  echo "==> 部署到本地..."
  cd "$SCRIPT_DIR"
  docker compose up -d --force-recreate ragflow-gpu
  echo "==> 部署完成"
}

# ---------- 解析命令 ----------
CMD="${1:-build}"
BUILD_ARGS=()

case "$CMD" in
  pack)
    shift
    BUILD_ARGS=("$@")
    do_build
    do_pack
    ;;
  pack-only)
    do_pack
    ;;
  deploy)
    shift
    BUILD_ARGS=("$@")
    do_build
    do_deploy
    ;;
  --no-cache|--*)
    # 当第一个参数是 docker build flag 时，当作普通构建
    BUILD_ARGS=("$@")
    do_build
    ;;
  build)
    shift || true
    BUILD_ARGS=("$@")
    do_build
    ;;
  *)
    echo "用法: $0 [build|pack|pack-only|deploy] [--no-cache ...]"
    echo ""
    echo "  build      构建镜像（默认）"
    echo "  pack       构建 + 打包为 .tar.gz"
    echo "  pack-only  仅打包已有镜像"
    echo "  deploy     构建 + 本地部署"
    echo ""
    echo "  额外参数会传给 docker build（如 --no-cache）"
    echo ""
    echo "当前 RAGFLOW_IMAGE=$IMAGE_TAG"
    exit 1
    ;;
esac
