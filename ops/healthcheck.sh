#!/bin/bash
# 在 seed 服务器上执行：健康检查，失败时自动重启后端
# Cron: */5 * * * * /root/zhihu_alpha/ops/healthcheck.sh >> /var/log/zhihu_health.log 2>&1
set -euo pipefail

URL="https://zppy.funnytop.club/api/health"
DEPLOY_DIR="/root/zhihu_alpha"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${URL}" 2>/dev/null || echo "000")

if [ "${STATUS}" != "200" ]; then
  echo "[$(date)] ALERT: Health check failed (HTTP ${STATUS}), restarting backend..."
  cd "${DEPLOY_DIR}"
  docker compose -f docker-compose.prod.yml restart backend
  sleep 10
  STATUS_AFTER=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${URL}" 2>/dev/null || echo "000")
  echo "[$(date)] Restart result: HTTP ${STATUS_AFTER}"
fi
