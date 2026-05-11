# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `README.md` 新增“队伍与项目介绍”板块，补充约 200 字的项目愿景、团队协作方式与核心功能闭环说明，便于在路演和评审场景中快速理解项目价值。
- 新增 `frontend/Dockerfile`，支持前端通过 Docker 容器启动 Vite 服务。
- 新增 `docker-compose.prod.yml`，提供生产版容器编排（frontend + backend + postgres）。
- 新增 `frontend/Dockerfile.prod` 与 `frontend/nginx.prod.conf`，支持前端构建产物由 Nginx 提供并同源反代 `/api`。

### Fixed

- `.env` 文件路径解析：`config.py` 自动搜索项目根目录和 backend 目录，不再依赖 CWD。
- `.env` 变量名与 `config.py` 对齐（`MINIMAX_KEY` → `MINIMAX_API_KEY`，`ZHIHU_ACCESS_SECRET` → `ZHIHU_APP_KEY`）。
- OAuth 基础 URL 修正为 `https://openapi.zhihu.com`（授权、换 token、获取用户信息），符合官方文档。
- MiniMax API 基址修正为 `https://api.minimax.io`，默认模型更新为 `MiniMax-M1`。
- `http://localhost:8000/` 返回 404 问题：FastAPI 现在挂载构建后的前端 SPA 静态文件，前后端同源运行。
- MiniMax 服务增加完善的容错处理：API key 缺失降级提示、HTTP 错误 / 超时 / 连接失败分别捕获、`base_resp.status_code` 校验。
- OAuth 登录失败问题：`exchange_oauth_token` 改为请求 `https://openapi.zhihu.com/access_token`，并使用 `application/x-www-form-urlencoded` 传参，避免 `/token` 路径 404 与 JSON 体不被识别。
- OAuth 错误信息增强：当 token / user 接口返回业务错误结构时，后端会抛出明确错误，便于定位 `app_id/app_key/redirect_uri/code` 不匹配问题。
- OAuth `redirect_uri` 兼容处理：后端新增规范化逻辑（去首尾空格、仅填写域名时自动补 `/auth/callback`），并在授权链接生成时统一 URL 编码，避免因 `http://127.0.0.1 ` 这类配置导致登录失败。
- 新增“开发免 OAuth”开关：`BYPASS_OAUTH_LOGIN=true` 时，后端鉴权返回本地调试用户，前端直接判定为已登录，便于快速浏览整站页面效果。
- `backend/app/services/minimax.py` 按 MiniMax Anthropic 兼容文档重写：改用 `https://api.minimaxi.com/anthropic/v1/messages`，消息体升级为 Anthropic `messages/content` 结构，流式解析 `content_block_delta` 的 `text_delta`，更适配 Agent 工作流与 M2 系列模型。
- 对话流式链路升级：`chat.py` 改为透传 `thinking/text/tool_use` 事件块，前端 `chat-session.tsx` 升级 SSE 解析与渲染，支持在打字机输出正文时同步展示推理过程与工具调用输入。
- 对话页面的 `thinking` 区块改为默认折叠并支持手动展开/收起，减少长推理内容对正文阅读区域的挤占。
- `docker compose up -d` 后端容器端口占用问题：后端宿主机映射改为可配置端口（`BACKEND_PORT`），避免与本机已有 `8000` 端口服务冲突导致启动失败。
- 前端容器启动失败（Vite 要求 Node `20.19+` 且 `rolldown` 原生绑定加载异常）问题：前端镜像升级到 Node 22（`swr` 镜像源）并调整依赖安装为 `npm install --include=optional`，容器可稳定启动。

### Changed

- `ZHIHU_REDIRECT_URI` 默认值改为 `http://localhost:8000/auth/callback`，适配同源部署模式。
- `CORS_ORIGINS` 增加 `http://localhost:8000`。
- OAuth `exchange_oauth_token` 请求增加 `grant_type: authorization_code` 字段。
- `get_user_info` 改用 `Authorization: Bearer {token}` Header（符合官方规范）。
- 用户字段名适配官方 API 返回格式（`fullname` / `avatar_path` / `uid`）。
- `docker-compose.yml` 从仅数据库扩展为前后端 + PostgreSQL 全栈编排，支持一条命令启动所有服务。
- `docker-compose.yml` 后端 `ports` 从固定 `8000:8000` 调整为 `${BACKEND_PORT:-8000}:8000`，支持按环境覆盖宿主机端口。
- `docker-compose.yml` 的 `CORS_ORIGINS` 中 `localhost` 端口改为跟随 `BACKEND_PORT`，避免端口切换后跨域白名单不一致。
- `frontend/vite.config.ts` 的代理目标改为可通过 `VITE_API_PROXY_TARGET` 配置，便于容器内转发到后端服务。
- `README.md` 本地开发说明更新为 Docker Compose 全栈启动流程。
- `README.md` 补充生产环境 Docker 启动与停止命令说明。
- `README.md` 新增本地后端端口可配置说明（`BACKEND_PORT`）。
- 根目录 `.env` 默认 `ZHIHU_REDIRECT_URI` 同步到 `http://localhost:8001/auth/callback`，与本地默认 `BACKEND_PORT=8001` 对齐。
- `frontend/Dockerfile` 与 `frontend/Dockerfile.prod` 的 Node 基础镜像由 Node 20 Alpine 调整为 Node 22 Alpine ARM64（`swr` 镜像源），满足 Vite 8 的最低 Node 版本要求并避免跨架构仿真。
- 前端 Docker 安装依赖命令统一为 `npm install --include=optional`，确保可选原生依赖在容器内可正确安装。

## [0.1.0] - 2026-05-11

### Added

- **项目脚手架**：初始化前端（React + Vite + TypeScript + shadcn/ui + Tailwind CSS）和后端（FastAPI + SQLAlchemy + PostgreSQL）项目结构。
- **Docker Compose**：本地开发 PostgreSQL 服务编排。
- **Alembic**：数据库迁移框架集成。
- **数据模型**：User、HotTopic、ChatSession、Message、IdeaCard 五张核心表，UUID 主键。
- **知乎 OAuth 登录**：完整的授权码模式流程（引导授权 → 换取 token → 获取用户信息 → JWT 签发）。
- **热点广场**：集成知乎热榜 API，支持内存缓存（1 小时 TTL）和数据库回退，前端瀑布流展示。
- **AI 创作对话**：集成 MiniMax Chat API，支持 SSE 流式输出；对话上下文管理（最近 20 条历史）；知乎站内搜索结果注入 AI 上下文。
- **灵感卡片**：CRUD API 及前端管理界面，支持标签筛选和关键词搜索。
- **一键发布知乎**：从聊天消息或灵感卡片直接发布到知乎圈子。
- **从对话保存灵感卡**：AI 回复可一键保存为灵感卡片。
- **响应式布局**：桌面端固定侧边栏，移动端 Sheet 抽屉式导航。
- **Toast 通知**：集成 Sonner，全局统一的操作反馈。
- **部署配置**：Vercel（前端 SPA 路由）和 Railway（后端 Dockerfile + Procfile）。
- **环境变量模板**：`backend/.env.example` 和 `frontend/.env.example`。
- 项目 `README.md`。
- `.gitignore` 覆盖 Python / Node / Docker / IDE / OS 常见忽略项。
