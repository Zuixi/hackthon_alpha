# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 热点诊断接口 `GET /api/hot/source-status`：返回知乎当前抓取来源判定（`newsnow`/`zhihu_api`/`mixed`/`unknown`）、最新批次号与来源分布计数，便于快速确认是否触发原生 API 回退。
- **多平台热点聚合**：热点广场从单一知乎数据源升级为 8 平台聚合（知乎、微博、抖音、今日头条、B站、百度、澎湃新闻、贴吧），知乎使用原生 API，其余平台通过 NewsNow 聚合 API 抓取。
- **NewsNow 抓取服务**：新增 `newsnow_fetcher.py`，异步 HTTP 客户端支持失败重试、数据清洗（标题校验、URL 追踪参数去除）、平台间请求间隔控制。
- **关键词过滤引擎**：移植 TrendRadar 的 frequency.py 核心设计，支持普通词、必须词(+)、排除词(!)、正则(/pattern/)、显示别名(=>)、组别名([])、每组上限(@N)、全局过滤([GLOBAL_FILTER]) 等完整语法。
- **关键词规则配置**：新增 `backend/config/keyword_rules.txt`，预置科技、社会民生、财经、国际、娱乐体育等主题分组规则。
- **热点 API 扩展**：新增 `GET /api/hot/platforms`（平台列表及数量统计）、`GET /api/hot/grouped`（按关键词分组返回），现有 `GET /api/hot` 支持 `platform` 过滤参数（逗号分隔）。
- **热点广场 UI 重设计**：支持四种视图模式（全部/按平台/按主题/历史），平台芯片过滤栏（可多选）、标题搜索框、平台品牌色标签（知乎蓝、微博红、抖音黑等）、关键词分组卡片。
- **热榜定时采集**：后台调度器每 30 分钟自动调用知乎热榜 API 抓取数据并持久化到 PostgreSQL，每次抓取带 `fetch_batch` 批次标识。
- **热榜历史时间线**：新增 `GET /api/hot/history?days=5` 接口，返回按天分组、按批次聚合的热榜历史数据，最多保留最近 5 天。
- **热榜数据自动清理**：调度器每轮抓取后自动清理 5 天前的过期热榜数据，控制数据库体积。
- **热榜历史视图 UI**：前端热点广场新增「最新/历史」切换，历史模式以天为卡片、每日可展开多个抓取批次，支持按批次时间浏览。
- **Redis 缓存层**：引入 Redis 7 容器，支持热点数据、关注列表、关注动态的分级缓存（热点 1h、关注列表 5min、关注动态 3min），缓存服务自带连接失败优雅降级。
- **社交圈页面**：新增 `/social` 路由，提供「关注列表」和「关注动态」双 Tab 视图，关注列表支持分页浏览、头像展示和外链跳转，关注动态以时间线卡片形式展示。
- **知乎关注列表 API**：后端新增 `GET /api/social/followees`，调用知乎 OAuth `GET /user/followees` 获取用户关注列表，结果缓存到 Redis（5 分钟 TTL）。
- **知乎关注动态 API**：后端新增 `GET /api/social/moments`，调用知乎 OAuth `GET /user/moments` 获取关注动态，结果缓存到 Redis（3 分钟 TTL）。
- **侧边栏导航**：新增「社交圈」导航入口。
- `README.md` 新增"队伍与项目介绍"板块，补充约 200 字的项目愿景、团队协作方式与核心功能闭环说明，便于在路演和评审场景中快速理解项目价值。
- 新增 `frontend/Dockerfile`，支持前端通过 Docker 容器启动 Vite 服务。
- 新增 `docker-compose.prod.yml`，提供生产版容器编排（frontend + backend + postgres）。
- 新增 `frontend/Dockerfile.prod` 与 `frontend/nginx.prod.conf`，支持前端构建产物由 Nginx 提供并同源反代 `/api`。
- 新增后端协作指南，按模块职责、业务域流程与外部依赖约定描述后端架构，支持 Agent 在不依赖具体文件名的前提下稳定修改后端能力。

### Fixed

- 知乎 OAuth 回调"`No authorization code received`"问题：前端回调页改为同时解析 query/hash 中的 `code`、`authorization_code`、`auth_code`，并透传更明确的 OAuth 错误信息，避免因参数位置或命名差异导致登录中断。
- OAuth 重定向一致性问题：`/api/auth/login-url` 与 `/api/auth/callback` 在未显式传入 `redirect_uri` 时统一回退到前端回调地址（`${FRONTEND_URL}/auth/callback`），避免授权后回跳或换 token 因地址不一致失败。
- `.env` 文件路径解析：`config.py` 自动搜索项目根目录和 backend 目录，不再依赖 CWD。
- `.env` 变量名与 `config.py` 对齐（`MINIMAX_KEY` → `MINIMAX_API_KEY`，`ZHIHU_ACCESS_SECRET` → `ZHIHU_APP_KEY`）。
- OAuth 基础 URL 修正为 `https://openapi.zhihu.com`（授权、换 token、获取用户信息），符合官方文档。
- MiniMax API 基址修正为 `https://api.minimax.io`，默认模型更新为 `MiniMax-M1`。
- `http://localhost:8000/` 返回 404 问题：FastAPI 现在挂载构建后的前端 SPA 静态文件，前后端同源运行。
- MiniMax 服务增加完善的容错处理：API key 缺失降级提示、HTTP 错误 / 超时 / 连接失败分别捕获、`base_resp.status_code` 校验。
- OAuth 登录失败问题：`exchange_oauth_token` 改为请求 `https://openapi.zhihu.com/access_token`，并使用 `application/x-www-form-urlencoded` 传参，避免 `/token` 路径 404 与 JSON 体不被识别。
- OAuth 错误信息增强：当 token / user 接口返回业务错误结构时，后端会抛出明确错误，便于定位 `app_id/app_key/redirect_uri/code` 不匹配问题。
- OAuth `redirect_uri` 兼容处理：后端新增规范化逻辑（去首尾空格、仅填写域名时自动补 `/auth/callback`），并在授权链接生成时统一 URL 编码，避免因 `http://127.0.0.1 ` 这类配置导致登录失败。
- 新增"开发免 OAuth"开关：`BYPASS_OAUTH_LOGIN=true` 时，后端鉴权返回本地调试用户，前端直接判定为已登录，便于快速浏览整站页面效果。
- `backend/app/services/minimax.py` 按 MiniMax Anthropic 兼容文档重写：改用 `https://api.minimaxi.com/anthropic/v1/messages`，消息体升级为 Anthropic `messages/content` 结构，流式解析 `content_block_delta` 的 `text_delta`，更适配 Agent 工作流与 M2 系列模型。
- 对话流式链路升级：`chat.py` 改为透传 `thinking/text/tool_use` 事件块，前端 `chat-session.tsx` 升级 SSE 解析与渲染，支持在打字机输出正文时同步展示推理过程与工具调用输入。
- 对话页面的 `thinking` 区块改为默认折叠并支持手动展开/收起，减少长推理内容对正文阅读区域的挤占。
- `docker compose up -d` 后端容器端口占用问题：后端宿主机映射改为可配置端口（`BACKEND_PORT`），避免与本机已有 `8000` 端口服务冲突导致启动失败。
- 前端容器启动失败（Vite 要求 Node `20.19+` 且 `rolldown` 原生绑定加载异常）问题：前端镜像升级到 Node 22（`swr` 镜像源）并调整依赖安装为 `npm install --include=optional`，容器可稳定启动。
- 热榜调度调用开发者接口 404 问题：`ZHIHU_DEV_BASE_URL` 默认值与示例配置统一修正为 `https://developer.zhihu.com`。

### Changed

- 热榜调度器新增 `HOT_ZHIHU_SOURCE_MODE`（`newsnow_first`/`newsnow_only`/`native_only`）知乎来源策略：默认先走 NewsNow（含知乎源），仅在 NewsNow 未抓到知乎时回退知乎原生 API，降低比赛期间原生接口额度消耗风险。
- **HotTopic 模型扩展**：新增 `platform`（平台标识）和 `source`（数据来源）字段，新增 Alembic 迁移，现有数据自动回填为 `zhihu` / `zhihu_api`。
- **热榜调度器升级**：从单一知乎抓取改为多阶段调度（先知乎原生 API → 再 NewsNow 全部平台 → 清理过期数据），各阶段错误隔离互不阻塞，知乎 API 未配置时仍可抓取其他平台。
- **热点 API 响应格式**：`HotTopicResponse` 新增 `platform`、`platform_name`、`source` 字段，缓存 key 增加 platform 维度避免串扰。
- **后端 Dockerfile**：新增 `COPY config ./config` 将关键词规则文件打入镜像。
- **后端日志配置**：`main.py` 新增 `logging.basicConfig(level=logging.INFO)` 确保自定义 logger 输出到容器标准输出。
- **前端热点广场重写**：从单一列表/历史双视图升级为全部/按平台/按主题/历史四视图，新增平台芯片过滤、标题搜索、关键词分组卡片等交互组件。
- **知乎热榜 API 鉴权修正**：从 `x-api-key` 改为 `Authorization: Bearer` + `X-Request-Timestamp`，查询参数 `Limit`（大写）对齐官方文档。
- **热点广场数据源**：从请求驱动拉取改为后台调度器预填充，API 接口直接返回数据库中最新批次数据。
- **HotTopic 模型**：新增 `fetch_batch`（抓取批次标识）和 `thumbnail_url`（缩略图）字段，新增 Alembic 迁移。
- **热点广场 UI 增强**：新增排序切换（热度/时间）、Top3 高亮排名、关注者数量展示、统计栏。
- **热点缓存迁移**：从内存字典缓存迁移到 Redis 缓存（1 小时 TTL），支持多实例部署下缓存共享。
- **Docker Compose**：新增 Redis 服务（华为 SWR 镜像源）、后端新增 `REDIS_URL` 环境变量和 Redis 健康检查依赖。
- `docker-compose.prod.yml` 同步添加 Redis 服务和持久化 volume。
- `backend/requirements.txt` 新增 `redis` 依赖。
- `backend/app/config.py` 新增 `REDIS_URL` 配置项。
- `backend/Dockerfile` 与 `frontend/Dockerfile` 升级为多阶段构建，并补充系统包源替换（Debian 使用清华 apt 镜像、Alpine 使用清华 apk 镜像）；同时保留 Python 清华源与 npm `npmmirror`，并通过选择性复制构建产物缩小最终镜像体积。
- `backend/app/config.py` 新增 `FRONTEND_URL` 配置项，并将 `ZHIHU_REDIRECT_URI` 默认值对齐到前端回调地址 `http://localhost:5173/auth/callback`。
- `frontend/AGENTS.md` 按统一规范补充为精简清单版，覆盖前端分层约束、核心业务规则、变更原则与完成标准。
- `backend/AGENTS.md` 进一步精简为清单式结构，保留核心分层约束、业务规则、变更原则和完成标准，提升可读性与执行效率。
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
- 知乎开发者鉴权配置去冗余：后端开发者接口统一只读取 `ZHIHU_ACCESS_SECRET`，彻底移除历史兼容变量，避免双变量配置不一致。

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
