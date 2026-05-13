#!/bin/bash
# seed 服务器首次初始化脚本
# 使用方法：scp ops/server-init.sh seed:/root/ && ssh seed 'bash /root/server-init.sh'
set -euo pipefail

echo "=== [1/6] Installing packages ==="
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx docker.io docker-compose-plugin curl

systemctl enable docker
systemctl start docker

echo "=== [2/6] Setting up SSL ==="
certbot --nginx -d zppy.funnytop.club --non-interactive --agree-tos -m admin@funnytop.club || {
  echo "Certbot failed. Run manually: certbot --nginx -d zppy.funnytop.club"
}

echo "=== [3/6] Configuring host Nginx ==="
DEPLOY_DIR="/root/zhihu_alpha"
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
cat > /etc/cron.d/zhihu-alpha << 'CRON'
# Database backup daily at 3:00 AM
0 3 * * * root /root/zhihu_alpha/ops/backup.sh >> /var/log/zhihu_backup.log 2>&1
# Health check every 5 minutes
*/5 * * * * root /root/zhihu_alpha/ops/healthcheck.sh >> /var/log/zhihu_health.log 2>&1
CRON

echo "=== [6/6] Summary ==="
echo ""
echo "Server initialized. Next steps:"
echo "  1. Upload .env.prod to ${DEPLOY_DIR}/"
echo "  2. Upload docker-compose.prod.yml to ${DEPLOY_DIR}/"
echo "  3. On om machine: ./ops/build.sh && ./ops/deploy.sh <version>"
echo ""
echo "Verify: curl -I https://zppy.funnytop.club"
