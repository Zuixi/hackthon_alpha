#!/bin/bash
# 目标服务器首次初始化脚本（运行前请设置 APP_DOMAIN 和 APP_ADMIN_EMAIL）
# 使用方法：scp ops/server-init.sh ${TARGET_HOST}:<REMOTE_ROOT_DIR>/ && ssh ${TARGET_HOST} 'APP_DOMAIN=example.com APP_ADMIN_EMAIL=ops@example.com bash <REMOTE_ROOT_DIR>/server-init.sh'
set -euo pipefail

APP_DOMAIN=${APP_DOMAIN:-}
APP_ADMIN_EMAIL=${APP_ADMIN_EMAIL:-}
DEPLOY_DIR=${DEPLOY_DIR:-/opt/zhihu_alpha}

if [ -z "${APP_DOMAIN}" ] || [ -z "${APP_ADMIN_EMAIL}" ]; then
  echo "Error: APP_DOMAIN and APP_ADMIN_EMAIL are required."
  echo "Example: APP_DOMAIN=example.com APP_ADMIN_EMAIL=ops@example.com bash ops/server-init.sh"
  exit 1
fi

echo "=== [1/6] Installing packages ==="
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx docker.io docker-compose-plugin curl

systemctl enable docker
systemctl start docker

echo "=== [2/6] Setting up SSL ==="
certbot --nginx -d "${APP_DOMAIN}" --non-interactive --agree-tos -m "${APP_ADMIN_EMAIL}" || {
  echo "Certbot failed. Run manually: certbot --nginx -d ${APP_DOMAIN}"
}

echo "=== [3/6] Configuring host Nginx ==="
mkdir -p "${DEPLOY_DIR}" /root/backups/zhihu_alpha /root/images

if [ -f "${DEPLOY_DIR}/ops/nginx-host.conf" ]; then
  cp "${DEPLOY_DIR}/ops/nginx-host.conf" /etc/nginx/sites-available/zhihu_alpha
  ln -sf /etc/nginx/sites-available/zhihu_alpha /etc/nginx/sites-enabled/
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx
fi

echo "=== [4/6] Setting up certbot auto-renewal ==="
echo "0 0,12 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" \
  > /etc/cron.d/certbot-renew

echo "=== [5/6] Setting up cron jobs ==="
cat > /etc/cron.d/zhihu-alpha << CRON
# Database backup daily at 3:00 AM
0 3 * * * root ${DEPLOY_DIR}/ops/backup.sh >> /var/log/zhihu_backup.log 2>&1
# Health check every 5 minutes
*/5 * * * * root ${DEPLOY_DIR}/ops/healthcheck.sh >> /var/log/zhihu_health.log 2>&1
CRON

echo "=== [6/6] Summary ==="
echo ""
echo "Server initialized. Next steps:"
echo "  1. Upload .env.prod to ${DEPLOY_DIR}/"
echo "  2. Upload docker-compose.prod.yml to ${DEPLOY_DIR}/"
echo "  3. On build host: ./ops/build.sh && ./ops/deploy.sh <version>"
echo ""
echo "Verify: curl -I https://${APP_DOMAIN}"
