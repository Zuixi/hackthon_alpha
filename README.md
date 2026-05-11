# 知乎创作助手

AI 驱动的一站式内容创作平台，深度融入知乎生态，帮助创作者发现热点、激发灵感、沉淀思考。

## 队伍与项目介绍

我们是AC不AK小队，希望把“灵感发现 - 内容打磨 - 发布反馈”串成一个高效闭环。项目聚焦知乎创作者的真实痛点：不知道写什么、写作过程缺少结构、发布后难以持续复盘。为此，我们打造了知乎创作助手：通过接入知乎热榜与站内搜索，帮助创作者快速捕捉热点；借助 AI 对话能力进行选题共创、观点延展和素材整理；配合灵感卡片沉淀长期可复用的创作资产；最终支持一键发布到知乎圈子。我们希望它不仅是一个写作工具，更是创作者长期成长的智能搭档。

## 核心功能

- **热点广场** - 接入知乎官方热榜 API，实时展示知乎热点话题
- **创作对话** - 基于 LLM + 知乎搜索增强，与 AI 头脑风暴创作内容
- **灵感卡片** - 结构化记录创作素材，支持标签管理和搜索
- **一键发布** - 将创作内容直接发布到知乎圈子，形成创作闭环

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React + Vite + TypeScript + shadcn/ui + Tailwind CSS |
| 后端 | FastAPI (Python) + SQLAlchemy + PostgreSQL |
| AI |  (流式对话) + 知乎搜索增强上下文 |
| 数据源 | 知乎官方 API (热榜、搜索、圈子、OAuth) |
| 部署 | Vercel (前端) + Railway (后端 + PostgreSQL) |

## 知乎 API 集成

- **OAuth 登录** - 知乎账号一键登录
- **热榜 API** - 获取实时热点话题
- **搜索 API** - 为 AI 对话提供知乎站内参考内容
- **圈子 API** - 发布创作内容到知乎圈子

## 本地开发

### 前置条件

- Docker + Docker Compose（推荐，前后端 + 数据库一键启动）
- Node.js 20+（仅本地裸机开发前端时需要）
- Python 3.13+（仅本地裸机开发后端时需要）

### 启动步骤

```bash
# 1. 配置环境变量（根目录 .env）
cp backend/.env.example .env

# 2. 启动前后端 + PostgreSQL
docker compose up --build
```

默认访问：

- 前端: http://localhost:5173
- 后端 API: `http://localhost:${BACKEND_PORT:-8000}`（可在根目录 `.env` 通过 `BACKEND_PORT` 覆盖）

## 生产部署（Docker）

使用生产编排文件（前端静态构建 + Nginx，后端 FastAPI，PostgreSQL）：

```bash
# 1. 准备根目录 .env
cp backend/.env.example .env

# 2. 启动生产栈
docker compose -f docker-compose.prod.yml up --build -d
```

默认访问：

- 前端（Nginx）: http://localhost
- 后端 API（通过前端同源转发）: http://localhost/api

停止服务：

```bash
docker compose -f docker-compose.prod.yml down
```

### 环境变量

后端 `.env` 需要配置:

- `LLM_API_KEY` - LLM API 密钥
- `ZHIHU_APP_ID` / `ZHIHU_APP_KEY` - 知乎黑客松项目密钥
- `ZHIHU_DEV_API_KEY` - 知乎开发者 API 密钥
- `JWT_SECRET` - JWT 签名密钥

前端 `.env`:

- `VITE_API_URL` - 后端 API 地址 (开发环境通过 Vite proxy 转发)

## 项目结构

```
zhihu_alpha/
├── frontend/                 # React + Vite 前端
│   ├── src/
│   │   ├── components/       # UI 组件
│   │   ├── pages/            # 页面组件
│   │   ├── hooks/            # 自定义 hooks
│   │   ├── lib/              # 工具函数和 API 客户端
│   │   └── types/            # TypeScript 类型定义
│   └── vercel.json           # Vercel 部署配置
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── models/           # SQLAlchemy 数据模型
│   │   ├── routers/          # API 路由
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # 业务逻辑 (MiniMax, Zhihu API)
│   ├── alembic/              # 数据库迁移
│   └── railway.toml          # Railway 部署配置
└── docker-compose.yml        # 本地全栈编排（frontend + backend + postgres）
```

## 赛道

知乎 Hackathon「灵感引擎」赛道 - AI 赋能内容创作
