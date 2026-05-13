#!/bin/bash
# 在 seed 服务器上执行：备份 PostgreSQL 数据库
# Cron: 0 3 * * * /root/zhihu_alpha/ops/backup.sh >> /var/log/zhihu_backup.log 2>&1
set -euo pipefail

BACKUP_DIR="/root/backups/zhihu_alpha"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "${BACKUP_DIR}"

echo "[${DATE}] Starting backup..."

docker exec zhihu_alpha_db_prod \
  pg_dump -U creator creator_assistant | gzip > "${BACKUP_DIR}/db_${DATE}.sql.gz"

SIZE=$(du -h "${BACKUP_DIR}/db_${DATE}.sql.gz" | cut -f1)
echo "[${DATE}] Backup done: db_${DATE}.sql.gz (${SIZE})"

# Keep only the last 7 days of backups
find "${BACKUP_DIR}" -name "db_*.sql.gz" -mtime +7 -delete
echo "[${DATE}] Cleanup complete"
