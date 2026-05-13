# 灵感引擎 — 知乎创作者 AI 助手

> 2026 知乎 AI 黑客松「灵感引擎」赛道参赛作品

## 产品简介

「灵感引擎」是面向知乎创作者的一站式 AI 辅助平台，帮助创作者完成**热点发现 → 灵感激发 → 内容创作 → 一键发布**的完整工作流。

核心差异点：内置**自进化 Skill 系统**和**生产级 Agent 弹性架构**——Agent 能从每次对话中自动沉淀可复用的工作策略，并通过三层相似度漏斗智能合并冗余 skill，越用越聪明；同时具备流式容错、防循环保护、并行工具执行、优雅降级等生产级能力。

---

## 核心功能

### 1. 热点广场
- 实时聚合知乎热榜数据（通过知乎开放 API）
- 一键从热点进入创作对话，携带话题上下文

### 2. AI 创作对话
- 基于 ReAct 架构的智能 Agent，支持多轮对话 + 工具调用
- 内置 11 个知乎 API 工具（热榜、搜索、全网搜索、直答、圈子、发布等）
- 流式 SSE 响应，实时展示推理与工具调用过程
- 持久化记忆系统（MEMORY.md / USER.md），跨会话记住用户偏好，含自动回顾与 Nudge 机制
- FTS5 全文搜索历史会话，为后续创作提供参考
- **生产级弹性能力**：流式传输容错重试、空响应自动恢复、工具参数修复与类型强制
- **防循环保护**：自动检测重复工具调用和连续错误，防止无限循环
- **并行工具执行**：只读工具批量并发调度（asyncio.gather），写操作顺序执行
- **优雅降级**：达到最大迭代次数后 LLM 自动生成总结而非硬切断
- **智能结果管理**：大工具输出自动持久化 + preview，per-turn 总预算控制
- **Token 使用量追踪**：每轮/每会话 token 统计，支持缓存命中率分析

### 3. 灵感卡片
- 结构化沉淀创作素材，支持标签管理、关键词搜索
- 可关联热点话题和对话会话，形成创作知识图谱

### 4. 一键发布
- 通过知乎社区 API 直接发布想法（Pin）到指定圈子
- 支持评论、点赞等社区互动操作

### 5. 自进化 Skill 系统（核心技术亮点）
- **会话后自动提炼**：每次对话结束异步分析 transcript，发现可复用工作流
- **三层相似度漏斗**：Trigger Jaccard → TF-IDF 余弦 → LLM 语义判定
- **智能合并**：检测到相似 skill 时，LLM 自动重新提炼为一个更完整的 skill
- **运行时管理**：Agent 可通过 `skill_manage` 工具实时 create/edit/delete/patch skill
- **使用追踪**：记录每个 skill 的查看、使用、来源，支撑生命周期管理

---

## 技术架构

```
┌────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                      │
│  React 19 · TypeScript · Tailwind CSS v4 · shadcn/ui           │
│  react-router-dom v7 · TanStack React Query · react-markdown   │
│  Pages: /hot · /chat · /chat/:id · /cards · /login             │
└────────────────────────┬───────────────────────────────────────┘
                         │ HTTP/REST + SSE
┌────────────────────────▼───────────────────────────────────────┐
│                   Backend (FastAPI + Python)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Layer (Routers)                     │   │
│  │  /api/auth · /api/hot · /api/chat · /api/cards            │   │
│  │  /api/publish · /api/health                               │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │               Agent System (ReAct Loop)                   │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │  Transport   │  │  Tool        │  │  Memory        │  │   │
│  │  │  (MiniMax/   │  │  Registry    │  │  (MEMORY.md +  │  │   │
│  │  │  OpenAI)     │  │  (16 tools)  │  │   USER.md)     │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │  Session DB  │  │  Context     │  │  Skill Engine  │  │   │
│  │  │  (SQLite +   │  │  Compressor  │  │  (Similarity + │  │   │
│  │  │   FTS5)      │  │  (增量摘要)   │  │   Consolidate) │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │   │
│  │  │  Guardrails  │  │  Token       │  │  Prompt Cache  │  │   │
│  │  │  (防循环+     │  │  Tracker     │  │  (stable/ctx/  │  │   │
│  │  │   熔断)       │  │  (usage统计)  │  │   volatile)    │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │  PostgreSQL   │  │  SQLite        │  │  File System     │   │
│  │  (Users,      │  │  (Agent        │  │  (SKILL.md,      │   │
│  │   Sessions,   │  │   Transcripts) │  │   .usage.json,   │   │
│  │   Cards...)   │  │                │  │   MEMORY.md)     │   │
│  └───────────────┘  └────────────────┘  └──────────────────┘   │
└─────────────────────────────┬──────────────────────────────────┘
                              │
          ┌───────────────────┼────────────────────┐
          ▼                   ▼                    ▼
   ┌─────────────┐   ┌──────────────┐    ┌──────────────────┐
   │  知乎开放API │   │  MiniMax LLM │    │  MCP 扩展服务     │
   │  (Data +     │   │  (abab6.5)   │    │  (可选外部工具)    │
   │  Community)  │   │              │    │                  │
   └─────────────┘   └──────────────┘    └──────────────────┘
```

---

## 项目结构

```
hackthon_alpha/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── main.py                   # 应用入口，CORS，路由挂载
│   │   ├── config.py                 # 全局配置（环境变量）
│   │   ├── database.py               # SQLAlchemy 引擎 + 会话
│   │   ├── auth.py                   # JWT 认证依赖
│   │   │
│   │   ├── models/                   # 数据模型
│   │   │   ├── user.py               # 用户（知乎 OAuth）
│   │   │   ├── hot_topic.py          # 热点话题缓存
│   │   │   ├── chat.py               # 对话会话 + 消息
│   │   │   └── idea_card.py          # 灵感卡片
│   │   │
│   │   ├── routers/                  # API 路由
│   │   │   ├── auth.py               # OAuth 登录 + JWT
│   │   │   ├── hot.py                # 热点列表
│   │   │   ├── chat.py               # 对话 CRUD + SSE 流式消息
│   │   │   ├── cards.py              # 灵感卡片 CRUD
│   │   │   └── publish.py            # 知乎发布
│   │   │
│   │   ├── services/                 # 业务服务
│   │   │   ├── zhihu.py              # 知乎 API 封装
│   │   │   ├── zhihu_tools.py        # 工具定义 + HMAC 签名
│   │   │   └── minimax.py            # MiniMax API 直调
│   │   │
│   │   └── agent/                    # AI Agent 系统
│   │       ├── agent_loop.py         # ReAct 主循环 + 全局单例
│   │       ├── config.py             # Agent 专属配置
│   │       ├── tool_guardrails.py    # 防循环保护 + 错误熔断
│   │       ├── token_tracker.py      # Token 使用量追踪
│   │       │
│   │       ├── transports/           # LLM 多供应商适配
│   │       │   ├── minimax.py        # MiniMax Anthropic 兼容 API
│   │       │   └── chat_completions.py # OpenAI 兼容 API
│   │       │
│   │       ├── tools/                # 工具注册中心
│   │       │   ├── registry.py       # ToolRegistry + 参数修复/类型强制
│   │       │   ├── zhihu_tools.py    # 11 个知乎 API 工具
│   │       │   ├── memory_tool.py    # 持久化记忆工具
│   │       │   ├── session_search.py # FTS5 会话搜索工具
│   │       │   ├── skill_tool.py     # SkillLoader + 只读工具
│   │       │   └── skill_manager.py  # SkillManager + CRUD 工具
│   │       │
│   │       ├── memory/               # 记忆系统
│   │       │   ├── memory_store.py   # 文件存储（MEMORY.md / USER.md）
│   │       │   ├── memory_manager.py # 多 Provider 编排
│   │       │   ├── memory_provider.py# 抽象接口
│   │       │   └── memory_reviewer.py# LLM 自动记忆回顾
│   │       │
│   │       ├── session/              # 会话存储
│   │       │   └── session_db.py     # SQLite + FTS5 全文搜索
│   │       │
│   │       ├── context/              # 上下文管理
│   │       │   └── compressor.py     # Token 压缩 + 增量摘要 + Anthropic 格式适配
│   │       │
│   │       ├── skill_engine/         # Skill 智能引擎
│   │       │   ├── similarity.py     # 三层漏斗相似度检测
│   │       │   ├── consolidator.py   # LLM 多 Skill 合并
│   │       │   ├── extractor.py      # 会话后自动提炼
│   │       │   └── usage.py          # 使用追踪
│   │       │
│   │       ├── skills/               # Skill 定义文件
│   │       │   ├── hotspot_analysis/ # 热点分析 Skill
│   │       │   ├── creative_writing/ # 创意写作 Skill
│   │       │   ├── publishing/       # 内容发布 Skill
│   │       │   ├── .archive/         # 合并归档
│   │       │   └── .usage.json       # 使用统计
│   │       │
│   │       └── mcp/                  # MCP 协议扩展
│   │           ├── client.py         # MCP 客户端
│   │           └── config.py         # MCP 服务器配置
│   │
│   ├── alembic/                      # 数据库迁移
│   ├── data/                         # 运行时数据
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
│
├── frontend/                         # React 前端
│   ├── src/
│   │   ├── pages/                    # 页面组件
│   │   │   ├── hot.tsx               # 热点广场
│   │   │   ├── chat.tsx              # 对话列表
│   │   │   ├── chat-session.tsx      # 对话详情
│   │   │   ├── cards.tsx             # 灵感卡片
│   │   │   └── login.tsx             # 登录页
│   │   ├── components/               # UI 组件
│   │   ├── lib/api.ts                # API 客户端
│   │   ├── hooks/use-auth.ts         # 认证 Hook
│   │   └── App.tsx                   # 路由配置
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                             # 文档
├── docker-compose.yml                # 开发环境编排
└── docker-compose.prod.yml           # 生产环境编排
```

---

## 技术栈详情

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 前端框架 | React | 19 | UI 渲染 |
| 构建工具 | Vite | 8 | 开发服务器 + 构建 |
| 路由 | react-router-dom | 7 | 客户端路由 |
| 数据获取 | TanStack React Query | - | 缓存 + 自动刷新 |
| 样式 | Tailwind CSS | 4 | 原子化 CSS |
| 组件库 | shadcn/ui + Base UI | - | 高质量 UI 组件 |
| 后端框架 | FastAPI | - | 异步 HTTP API |
| ORM | SQLAlchemy | 2.x | 数据库抽象层 |
| 迁移 | Alembic | - | Schema 版本管理 |
| 主数据库 | PostgreSQL | 15 | 关系型存储 |
| 搜索引擎 | SQLite FTS5 | - | Agent 会话全文搜索 |
| AI 模型 | MiniMax abab6.5-chat | - | 对话生成 + 工具调用 |
| 中文分词 | jieba | - | TF-IDF 相似度计算 |
| 认证 | JWT + OAuth 2.0 | - | 知乎账号登录 |
| 流式传输 | SSE (Server-Sent Events) | - | 实时 Agent 响应 |
| 容器化 | Docker + Docker Compose | - | 开发 / 生产部署 |

---

## API 一览

| 方法 | 路径 | 认证 | 功能 |
|------|------|------|------|
| GET | `/api/health` | 否 | 健康检查 |
| GET | `/api/auth/login-url` | 否 | 获取知乎 OAuth 登录 URL |
| POST | `/api/auth/callback` | 否 | OAuth 回调，返回 JWT |
| GET | `/api/auth/me` | 是 | 获取当前用户信息 |
| GET | `/api/hot` | 否 | 获取知乎热点列表 |
| GET | `/api/hot/{topic_id}` | 否 | 获取单条热点详情 |
| GET | `/api/chat` | 是 | 获取对话列表 |
| POST | `/api/chat` | 是 | 创建新对话 |
| GET | `/api/chat/{session_id}` | 是 | 获取对话详情 + 消息 |
| DELETE | `/api/chat/{session_id}` | 是 | 删除对话 |
| POST | `/api/chat/{session_id}/message` | 是 | 发送消息（SSE 流式响应） |
| GET | `/api/cards` | 是 | 获取灵感卡片列表 |
| POST | `/api/cards` | 是 | 创建灵感卡片 |
| GET | `/api/cards/tags` | 是 | 获取所有标签 |
| GET | `/api/cards/{card_id}` | 是 | 获取卡片详情 |
| PUT | `/api/cards/{card_id}` | 是 | 更新卡片 |
| DELETE | `/api/cards/{card_id}` | 是 | 删除卡片 |
| POST | `/api/publish` | 是 | 发布想法到知乎 |

---

## Agent 工具列表

Agent 通过 ReAct 循环自主调用以下 16 个工具：

| 工具名 | 类别 | 功能 |
|--------|------|------|
| `zhihu_hot_list` | 知乎 API | 获取实时热榜 |
| `zhihu_search` | 知乎 API | 站内搜索 |
| `zhihu_global_search` | 知乎 API | 全网搜索 |
| `zhihu_direct_answer` | 知乎 API | 知乎直答 Agent |
| `zhihu_get_ring_detail` | 知乎 API | 获取圈子详情 |
| `zhihu_publish_pin` | 知乎 API | 发布想法到圈子 |
| `zhihu_create_comment` | 知乎 API | 创建评论 |
| `zhihu_reaction` | 知乎 API | 点赞/表态 |
| `zhihu_get_comments` | 知乎 API | 获取评论列表 |
| `zhihu_story_list` | 知乎 API | 获取故事列表 |
| `zhihu_story_detail` | 知乎 API | 获取故事详情 |
| `memory` | Agent 内置 | 持久化记忆读写 |
| `session_search` | Agent 内置 | FTS5 会话历史搜索 |
| `skills_list` | Skill 系统 | 列出所有可用 Skill |
| `skill_view` | Skill 系统 | 查看 Skill 详细说明 |
| `skill_manage` | Skill 系统 | 创建/编辑/删除/微调 Skill |

---

## Agent 核心弹性架构

本项目的 Agent 具备生产级弹性能力，参考 Hermes-Agent 架构设计：

```
用户消息 ──→ System Prompt 三段缓存（stable/context/volatile）
                              │
                              ▼
                    ┌─── ReAct 循环 ───┐
                    │                   │
                    │   LLM API 调用    │
                    │   ↓               │
                    │   流式容错重试     │──→ 失败时最多重试 2 次
                    │   ↓               │
                    │   空响应恢复      │──→ 空回复自动 nudge 重试（最多 3 次）
                    │   ↓               │
                    │   参数修复+类型强制 │──→ 修复截断JSON、类型转换
                    │   ↓               │
                    │   防循环保护      │──→ 重复调用检测 + 连续错误熔断
                    │   ↓               │
                    │   ┌──────┴──────┐ │
                    │   │ 安全工具?    │ │
                    │   │ Y: 并行执行  │ │──→ asyncio.gather
                    │   │ N: 顺序执行  │ │
                    │   └──────┬──────┘ │
                    │          ↓         │
                    │   结果大小管理     │──→ >8KB 持久化 · >3KB 截断 · 轮次预算 15KB
                    │   ↓               │
                    │   Token 追踪      │──→ 按轮统计 input/output/cache tokens
                    │                   │
                    └───── 达到上限 ────→ 优雅降级（无工具收尾总结）
```

**关键特性**：
- **前缀缓存**：stable 段标记 `cache_control`，节省 60%+ 的重复 prompt token
- **增量式摘要**：连续压缩时基于旧摘要增量更新，信息损失更小
- **工具参数自愈**：`repair_tool_args` 修复尾随逗号、未闭合括号等常见 LLM 输出错误
- **10 个只读工具并行**：搜索、热榜等工具批量并发调度，显著降低延迟

---

## Skill 系统架构

这是本项目的核心技术亮点。相比 Hermes-Agent 纯 LLM 驱动的方案，我们引入了**算法级预筛 + LLM 精判**的两阶段架构：

```
会话结束 ──→ SkillExtractor ──→ 候选 Skill
                                    │
                                    ▼
                             SkillManager.create()
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Layer 1          Layer 2          Layer 3
           Trigger Jaccard   TF-IDF 余弦     LLM 语义判定
            (阈值 0.3)       (阈值 0.5)       (阈值 0.7)
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                              相似 skill 存在？
                              ╱              ╲
                            是                否
                            ▼                 ▼
                    SkillConsolidator    直接创建
                    (LLM 重写合并)      新 SKILL.md
                            │
                            ▼
                      归档旧 skill
                    写入合并后 skill
```

**优势**：
- Layer 1-2 的算法预筛避免了对每对 Skill 调用 LLM，节省 90%+ 的 API 成本
- 自动归档机制防止 Skill 膨胀
- 使用追踪数据支撑未来的智能推荐和自动清理

---

## 快速启动

### 前置要求
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Docker（可选）

### 本地开发

```bash
# 1. 启动 PostgreSQL（或用 Docker）
docker-compose up -d postgres

# 2. 后端
cd hackthon_alpha/backend
pip install -r requirements.txt
cp .env.example .env  # 填写 API 密钥
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 3. 前端
cd hackthon_alpha/frontend
npm install
npm run dev  # 默认 http://localhost:5173
```

### Docker 一键部署

```bash
cd hackthon_alpha
docker-compose up -d          # 开发环境
docker-compose -f docker-compose.prod.yml up -d  # 生产环境
```

---

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `DATABASE_URL` | 是 | PostgreSQL 连接串 |
| `MINIMAX_API_KEY` | 是 | MiniMax LLM API 密钥 |
| `MINIMAX_MODEL` | 否 | 模型名称（默认 abab6.5-chat） |
| `ZHIHU_APP_ID` | 是 | 知乎应用 ID |
| `ZHIHU_APP_KEY` | 是 | 知乎应用密钥 |
| `ZHIHU_DEV_API_KEY` | 是 | 知乎数据平台 API Key |
| `ZHIHU_COMMUNITY_APP_KEY` | 是 | 知乎社区 API Key |
| `ZHIHU_COMMUNITY_APP_SECRET` | 是 | 知乎社区 API Secret |
| `JWT_SECRET` | 是 | JWT 签名密钥 |
| `CORS_ORIGINS` | 否 | 允许的跨域来源 |
| `SKILL_AUTO_EXTRACT` | 否 | 是否自动提炼 Skill（默认 true） |
| `SKILL_SIMILARITY_THRESHOLD` | 否 | Skill 合并阈值（默认 0.7） |
| `MEMORY_AUTO_REVIEW` | 否 | 是否自动记忆回顾（默认 true） |
| `MEMORY_NUDGE_INTERVAL` | 否 | 记忆提醒间隔轮次（默认 8） |
| `MAX_EMPTY_RETRIES` | 否 | 空响应重试次数（默认 3） |
| `MAX_STREAM_RETRIES` | 否 | 流式传输重试次数（默认 2） |
| `TOOL_MAX_REPEAT` | 否 | 工具重复调用上限（默认 3） |
| `PARALLEL_TOOL_ENABLED` | 否 | 启用并行工具执行（默认 true） |
| `TOOL_RESULT_PERSIST_THRESHOLD` | 否 | 大结果持久化阈值字符数（默认 8000） |
| `BYPASS_OAUTH_LOGIN` | 否 | 开发模式跳过 OAuth（默认 false） |
