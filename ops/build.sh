#!/bin/bash
# 在 om 构建机上执行：拉取最新代码 -> 构建 amd64 镜像 -> 保存到 images/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

VERSION=${1:-$(date +%Y%m%d_%H%M%S)}
IMAGES_DIR="./images"
mkdir -p "${IMAGES_DIR}"

echo "=== [1/4] Pulling latest code ==="
git fetch --all --prune
git checkout main
git pull

echo "=== [2/4] Building backend image ==="
docker build -t zhihu-backend:${VERSION} -f backend/Dockerfile.prod ./backend

echo "=== [3/4] Building frontend image ==="
docker build -t zhihu-frontend:${VERSION} \
  --build-arg VITE_API_URL="" \
  -f frontend/Dockerfile.prod ./frontend

echo "=== [4/4] Saving images ==="
docker save zhihu-backend:${VERSION} zhihu-frontend:${VERSION} \
  | gzip > "${IMAGES_DIR}/zhihu_alpha_${VERSION}.tar.gz"

# Keep only the 3 most recent image tarballs
ls -t "${IMAGES_DIR}"/zhihu_alpha_*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f

echo ""
echo "Build complete!"
echo "  Version : ${VERSION}"
echo "  Image   : ${IMAGES_DIR}/zhihu_alpha_${VERSION}.tar.gz"
echo "  Size    : $(du -h "${IMAGES_DIR}/zhihu_alpha_${VERSION}.tar.gz" | cut -f1)"
echo ""
echo "Next step: ./ops/deploy.sh ${VERSION}"
