# 部署指南

## 环境概览

| 角色 | 主机 | 连接方式 | 用途 |
|------|------|----------|------|
| 构建机 | `BUILD_HOST` | `ssh ${BUILD_HOST}` | 拉取代码、构建 Docker 镜像 |
| 目标服务器 | `TARGET_HOST` (`APP_DOMAIN`) | `ssh ${TARGET_HOST}` | 运行生产服务 |

- 服务器架构：Linux amd64 (Debian 6.1)
- 服务器镜像存放地址：`<IMAGE_STORE_DIR>`
- 服务器部署目录：`<DEPLOY_DIR>`
- 说明：仓库内仅保留占位符，真实主机别名/域名/路径请保存在私有运维文档或密码管理器中。

## 首次部署

### 1. 初始化目标服务器

```bash
# 上传初始化脚本并执行
scp ops/server-init.sh ${TARGET_HOST}:<REMOTE_ROOT_DIR>/
ssh ${TARGET_HOST} 'bash <REMOTE_ROOT_DIR>/server-init.sh'
```

脚本会安装 Nginx/Certbot/Docker，配置 SSL 证书、cron 定时任务。

### 2. 上传配置文件到服务器

```bash
# 复制生产环境变量（编辑填入真实密钥后上传）
cp .env.prod.example .env.prod
# 编辑 .env.prod 填入真实值...
scp .env.prod ${TARGET_HOST}:<DEPLOY_DIR>/
scp docker-compose.prod.yml ${TARGET_HOST}:<DEPLOY_DIR>/
scp -r ops/ ${TARGET_HOST}:<DEPLOY_DIR>/
```

### 3. 在 om 机器构建并部署

```bash
ssh ${BUILD_HOST}
cd <BUILD_WORKDIR>

# 构建镜像（自动 git pull）
./ops/build.sh

# 部署到服务器（使用 build.sh 输出的版本号）
./ops/deploy.sh <version>
```

## 日常迭代部署

```bash
ssh ${BUILD_HOST}
cd <BUILD_WORKDIR>

# 1. 构建新版本
./ops/build.sh
# 输出示例: Version: 20260513_180000

# 2. 部署到服务器
./ops/deploy.sh 20260513_180000
```

## 回滚

```bash
# 查看可用版本
ls -lt images/zhihu_alpha_*.tar.gz

# 部署旧版本
./ops/deploy.sh <old_version>
```

## 运维

### 查看服务状态

```bash
ssh ${TARGET_HOST} 'cd <DEPLOY_DIR> && docker compose -f docker-compose.prod.yml ps'
```

### 查看日志

```bash
ssh ${TARGET_HOST} 'cd <DEPLOY_DIR> && docker compose -f docker-compose.prod.yml logs -f --tail=100 backend'
```

### 手动备份

```bash
ssh ${TARGET_HOST} '<DEPLOY_DIR>/ops/backup.sh'
```

### 自动任务（已通过 server-init.sh 配置）

| 任务 | 频率 | 日志 |
|------|------|------|
| 数据库备份 | 每日 03:00 | `/var/log/zhihu_backup.log` |
| 健康检查 | 每 5 分钟 | `/var/log/zhihu_health.log` |
| SSL 证书续期 | 每日 00:00/12:00 | syslog |

## 架构说明

```
用户 -> HTTPS:443 (宿主机 Nginx + Let's Encrypt)
  -> proxy_pass :8080 (Docker Frontend Nginx)
    -> /api/* -> backend:8000 (FastAPI)
    -> /* -> SPA 静态文件
  Backend -> postgres:5432 (内部网络)
  Backend -> redis:6379 (内部网络, 需密码)
```

PostgreSQL/Redis 不暴露到宿主机网络，仅 Docker 内部通信。
