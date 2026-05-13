#!/bin/bash
# 从 om 构建机传输镜像到 seed 目标服务器并启动
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

SERVER="seed"
IMAGES_DIR="./images"
REMOTE_DEPLOY="/root/zhihu_alpha"

VERSION=${1:-}
if [ -z "$VERSION" ]; then
  echo "Usage: ./ops/deploy.sh <version>"
  echo ""
  echo "Available images:"
  ls -lht "${IMAGES_DIR}"/zhihu_alpha_*.tar.gz 2>/dev/null | awk '{print "  "$NF, "("$5")"}' || echo "  No images found. Run ./ops/build.sh first."
  exit 1
fi

IMAGE_FILE="${IMAGES_DIR}/zhihu_alpha_${VERSION}.tar.gz"
if [ ! -f "${IMAGE_FILE}" ]; then
  echo "Error: ${IMAGE_FILE} not found"
  exit 1
fi

echo "=== [1/3] Transferring image to server ==="
scp "${IMAGE_FILE}" ${SERVER}:/root/images/

echo "=== [2/3] Loading image on server ==="
ssh ${SERVER} "gunzip -c /root/images/zhihu_alpha_${VERSION}.tar.gz | docker load"

echo "=== [3/3] Starting services ==="
ssh ${SERVER} << REMOTE
  cd ${REMOTE_DEPLOY}
  export DEPLOY_VERSION=${VERSION}
  docker compose -f docker-compose.prod.yml up -d --no-build
  echo ""
  docker compose -f docker-compose.prod.yml ps
REMOTE

echo ""
echo "Deploy complete: ${VERSION}"
echo "Site: https://zppy.funnytop.club"
