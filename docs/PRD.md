# 创作者助手 - 产品需求文档 (PRD)

**版本**: v1.0  
**日期**: 2026-05-11  
**作者**: 黑客松参赛团队  

---

## 1. 产品概述

### 1.1 产品定位
为知乎创作者提供的一站式内容创作辅助平台，帮助创作者发现热点、激发灵感、沉淀思考、分析数据。

### 1.2 核心价值主张
- **热点发现**: 聚合多平台24小时热点，让创作者不错过任何话题机会
- **智能对话**: AI辅助头脑风暴，帮助创作者快速找到切入角度
- **灵感沉淀**: 结构化记录创作素材，支持标签管理和关联检索
- **数据洞察**: 可视化展示作品数据，帮助创作者了解内容表现

### 1.3 目标用户
- 知乎活跃创作者（个人博主、自媒体、专业答主）
- 关注内容创作的效率和质量
- 需要数据化分析来优化创作策略

---

## 2. 功能需求

### 2.1 用户系统

#### 2.1.1 登录/注册
- 支持知乎 OAuth2.0 登录
- 首次登录自动创建用户档案
- 获取用户基本信息（昵称、头像、知乎ID）

#### 2.1.2 用户档案
- 展示用户基本信息
- 关联创作者作品列表

### 2.2 热点广场

#### 2.2.1 热点展示
- **数据来源**: 通过爬虫抓取 tophub.today 的24小时热点
- **支持平台**: 知乎热榜、微博热搜、B站热门、抖音热榜
- **展示字段**: 排名、标题、热度值、平台标识
- **排序方式**: 按热度值降序（默认），支持按时间排序
- **筛选功能**: 按平台筛选（单选/多选）
- **刷新机制**: 每小时自动更新，支持手动刷新

#### 2.2.2 热点操作
- 点击热点 → 跳转创作对话（携带热点上下文）
- 点击"记录灵感" → 快速创建关联该热点的灵感卡片
- 点击外部链接 → 跳转原始页面查看详情

### 2.3 创作对话

#### 2.3.1 对话列表
- 展示所有历史对话会话
- 按最后更新时间排序
- 显示关联的热点标题
- 支持删除会话

#### 2.3.2 对话界面
- **Chat界面**: 类似ChatGPT的对话式UI
- **系统Prompt设计**:
  ```
  你是创作者的AI助手，帮助创作者基于热点话题进行内容创作。
  当前讨论的热点：{hotTopicTitle}
  
  你可以：
  1. 分析热点事件的背景和核心争议点
  2. 提供多个切入角度供创作者选择
  3. 帮助梳理论点和论据
  4. 给出内容结构建议
  5. 回答创作者的具体问题
  
  请用专业、有洞察力的方式回答，帮助创作者产出优质内容。
  ```
- **上下文管理**: 携带历史对话记录（最近20轮）
- **快捷操作**:
  - 一键生成灵感卡片（提取AI回复关键内容）
  - 重新生成回答
  - 复制对话内容

#### 2.3.3 AI模型配置
- **使用模型**: MiniMax API
- **参数设置**:
  - Temperature: 0.7（平衡创造性和一致性）
  - Max Tokens: 2000
  - Model: MiniMax-Text-01

### 2.4 灵感卡片

#### 2.4.1 卡片列表
- **展示方式**: 卡片网格/列表双模式
- **卡片内容**: 内容摘要、标签、关联热点、创建时间
- **筛选功能**:
  - 按标签筛选（支持多选）
  - 按时间范围筛选
  - 关键词搜索（标题和内容）
- **排序方式**: 创建时间（新→旧/旧→新）、最近编辑

#### 2.4.2 卡片详情
- 完整内容展示（支持Markdown渲染）
- 关联热点/对话的快速跳转
- 标签编辑
- 删除操作

#### 2.4.3 创建卡片
- **入口**:
  - 热点广场点击"记录灵感"
  - 对话界面点击"生成卡片"
  - 卡片库点击"新建"
- **字段**:
  - 内容（富文本/Markdown编辑器）
  - 标签（支持输入创建新标签，支持从已有标签选择）
  - 关联热点（可选，自动填充）
  - 关联对话（可选，自动填充）

### 2.5 数据分析

#### 2.5.1 概览指标
- 总阅读量
- 总点赞数
- 总收藏数
- 总评论数
- 作品总数
- 数据更新时间

#### 2.5.2 趋势图表
- **阅读量趋势图**:
  - 图表类型: 折线图
  - 时间维度: 7天/30天/90天/全部
  - X轴: 日期
  - Y轴: 阅读量
  - 支持多作品对比
  
- **互动数据趋势图**:
  - 图表类型: 堆叠面积图或分组柱状图
  - 指标: 点赞、收藏、评论
  - 时间维度可选

#### 2.5.3 作品表现对比
- **图表类型**: 横向柱状图
- **对比维度**: 阅读量/点赞数/收藏数
- **排序**: 按选中指标降序
- **限制**: 最多展示Top 20作品

#### 2.5.4 数据表格
- **字段**: 作品标题、类型、发布时间、阅读量、点赞、收藏、评论
- **排序**: 支持点击表头排序
- **分页**: 每页20条
- **搜索**: 支持标题搜索

---

## 3. 技术架构

### 3.1 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Next.js 14 (App Router) | React服务端组件，SEO友好 |
| UI组件 | shadcn/ui + Tailwind CSS | 现代化组件库，快速开发 |
| 状态管理 | React Hooks + Context | 轻量级状态管理 |
| 数据获取 | SWR | 缓存和重新验证 |
| 可视化 | Recharts | React图表库 |
| **后端** | **FastAPI (Python)** | **高性能异步Python框架** |
| **数据库** | **PostgreSQL** | **关系型数据库** |
| **ORM** | **SQLAlchemy** | **Python ORM** |
| **迁移** | **Alembic** | **数据库迁移工具** |
| **认证** | **JWT + OAuth** | **知乎OAuth集成** |
| **AI服务** | **MiniMax API** | **对话生成** |
| **爬虫** | **Playwright + APScheduler** | **定时抓取热点** |
| **部署** | **Docker + Docker Compose** | **容器化部署** |

### 3.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Frontend (Next.js)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  热点广场    │  │  创作对话    │  │  灵感卡片  │ 数据中心 │  │
│  │   (SSR)     │  │   (CSR)     │  │    (CSR)   │  (SSR)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST API
┌──────────────────────────▼──────────────────────────────────┐
│                 Backend API (FastAPI + Python)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  /api/hot   │  │  /api/chat  │  │  /api/cards         │  │
│  │  /api/auth  │  │             │  │  /api/works         │  │
│  └─────────────┘  └─────────────┘  │  /api/stats         │  │
│                                    └─────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              定时任务 (APScheduler)                      │  │
│  │         每小时执行热点爬虫任务                           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌────────────────┐  ┌────────────────┐
│  PostgreSQL  │  │   MiniMax API  │  │  知乎OAuth     │
│  (数据存储)   │  │                │  │  + 作品抓取    │
└──────────────┘  └────────────────┘  └────────────────┘
```

### 3.3 项目结构

```
creator-assistant/
├── docker-compose.yml              # Docker编排配置
├── frontend/                       # Next.js 前端
│   ├── Dockerfile
│   ├── app/
│   │   ├── api/                    # 前端API路由（转发到后端）
│   │   ├── dashboard/
│   │   │   ├── hot/page.tsx
│   │   │   ├── chat/
│   │   │   ├── cards/page.tsx
│   │   │   └── analytics/page.tsx
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── next.config.js
├── backend/                        # FastAPI 后端
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI入口
│   │   ├── config.py               # 配置管理
│   │   ├── database.py             # 数据库连接
│   │   ├── models/                 # SQLAlchemy模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── hot_topic.py
│   │   │   ├── chat.py
│   │   │   ├── idea_card.py
│   │   │   └── work.py
│   │   ├── routers/                # API路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── hot.py
│   │   │   ├── chat.py
│   │   │   ├── cards.py
│   │   │   └── stats.py
│   │   ├── services/               # 业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── minimax.py          # MiniMax API封装
│   │   │   ├── crawler.py          # 爬虫服务
│   │   │   └── zhihu.py            # 知乎API封装
│   │   └── tasks/                  # 定时任务
│   │       └── hot_crawler.py
│   ├── alembic/                    # 数据库迁移
│   ├── requirements.txt
│   └── .env
└── nginx/                          # Nginx反向代理
    └── nginx.conf
```

### 3.4 数据模型 (SQLAlchemy)

```python
# backend/app/models/user.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    zhihu_id = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    avatar = Column(String)
    email = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# backend/app/models/hot_topic.py
from sqlalchemy import Column, String, Integer, DateTime, Index
from app.database import Base

class HotTopic(Base):
    __tablename__ = "hot_topics"
    
    id = Column(String, primary_key=True, index=True)
    platform = Column(String, nullable=False)  # zhihu, weibo, bilibili, douyin
    external_id = Column(String)
    title = Column(String, nullable=False)
    url = Column(String)
    hot_value = Column(String)  # 热度值（字符串存储）
    rank = Column(Integer)
    fetched_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_platform_fetched', 'platform', 'fetched_at'),
    )

# backend/app/models/chat.py
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    hot_topic_id = Column(String, ForeignKey("hot_topics.id"))
    title = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    user = relationship("User", back_populates="chat_sessions")
    hot_topic = relationship("HotTopic")
    messages = relationship("Message", back_populates="session", cascade="all, delete")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(Enum("user", "assistant", name="message_role"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    session = relationship("ChatSession", back_populates="messages")

# backend/app/models/idea_card.py
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, ARRAY
from app.database import Base

class IdeaCard(Base):
    __tablename__ = "idea_cards"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(String), default=[])
    hot_topic_id = Column(String, ForeignKey("hot_topics.id"))
    chat_session_id = Column(String, ForeignKey("chat_sessions.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# backend/app/models/work.py
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Date
from sqlalchemy.orm import relationship
from app.database import Base

class Work(Base):
    __tablename__ = "works"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    zhihu_work_id = Column(String, unique=True)
    title = Column(String, nullable=False)
    type = Column(String)  # article, answer, pin
    url = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    
    stats = relationship("WorkStat", back_populates="work", cascade="all, delete")

class WorkStat(Base):
    __tablename__ = "work_stats"
    
    id = Column(String, primary_key=True, index=True)
    work_id = Column(String, ForeignKey("works.id"))
    date = Column(Date, nullable=False)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    collections = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    
    work = relationship("Work", back_populates="stats")
    
    __table_args__ = (
        UniqueConstraint('work_id', 'date', name='uix_work_date'),
        Index('idx_work_date', 'work_id', 'date'),
    )
```

---

## 4. API 设计

### 4.1 热点相关

```python
# GET /api/hot
# 获取热点列表
@app.get("/api/hot")
async def get_hot_topics(
    platform: Optional[str] = None,
    limit: int = 50
) -> List[HotTopicResponse]:
    pass

# POST /api/hot/refresh
# 手动触发热点刷新（管理员）
@app.post("/api/hot/refresh")
async def refresh_hot_topics() -> RefreshResponse:
    pass
```

### 4.2 对话相关

```python
# GET /api/chat
# 获取对话列表
@app.get("/api/chat")
async def get_chat_sessions(
    current_user: User = Depends(get_current_user)
) -> List[ChatSessionResponse]:
    pass

# POST /api/chat
# 创建新对话或继续对话
@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
) -> ChatResponse:
    pass

# GET /api/chat/{session_id}
# 获取对话详情
@app.get("/api/chat/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> ChatSessionDetailResponse:
    pass

# DELETE /api/chat/{session_id}
# 删除对话
@app.delete("/api/chat/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    pass
```

### 4.3 灵感卡片相关

```python
# GET /api/cards
@app.get("/api/cards")
async def get_cards(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
) -> CardsResponse:
    pass

# POST /api/cards
@app.post("/api/cards")
async def create_card(
    request: CreateCardRequest,
    current_user: User = Depends(get_current_user)
) -> CardResponse:
    pass

# GET /api/cards/{card_id}
@app.get("/api/cards/{card_id}")
async def get_card(
    card_id: str,
    current_user: User = Depends(get_current_user)
) -> CardResponse:
    pass

# PUT /api/cards/{card_id}
@app.put("/api/cards/{card_id}")
async def update_card(
    card_id: str,
    request: UpdateCardRequest,
    current_user: User = Depends(get_current_user)
) -> CardResponse:
    pass

# DELETE /api/cards/{card_id}
@app.delete("/api/cards/{card_id}")
async def delete_card(
    card_id: str,
    current_user: User = Depends(get_current_user)
):
    pass
```

### 4.4 作品数据相关

```python
# GET /api/works
@app.get("/api/works")
async def get_works(
    current_user: User = Depends(get_current_user)
) -> List[WorkResponse]:
    pass

# GET /api/stats
@app.get("/api/stats")
async def get_stats(
    work_id: Optional[str] = None,
    days: int = 30,
    current_user: User = Depends(get_current_user)
) -> StatsResponse:
    pass
```

---

## 5. Docker 部署配置

### 5.1 docker-compose.yml

```yaml
version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    container_name: creator_assistant_db
    environment:
      POSTGRES_USER: ${DB_USER:-creator}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-password}
      POSTGRES_DB: ${DB_NAME:-creator_assistant}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-creator}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI 后端
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: creator_assistant_backend
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-creator}:${DB_PASSWORD:-password}@postgres:5432/${DB_NAME:-creator_assistant}
      - MINIMAX_API_KEY=${MINIMAX_API_KEY}
      - ZHIHU_CLIENT_ID=${ZHIHU_CLIENT_ID}
      - ZHIHU_CLIENT_SECRET=${ZHIHU_CLIENT_SECRET}
      - JWT_SECRET=${JWT_SECRET}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Next.js 前端
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: creator_assistant_frontend
    environment:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
    ports:
      - "3000:3000"
    depends_on:
      - backend

  # Nginx 反向代理 (生产环境)
  nginx:
    image: nginx:alpine
    container_name: creator_assistant_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    profiles:
      - production

volumes:
  postgres_data:
```

### 5.2 Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.3 Frontend Dockerfile

```dockerfile
FROM node:20-alpine

WORKDIR /app

# 安装依赖
COPY package*.json ./
RUN npm ci

# 复制代码
COPY . .

# 构建
RUN npm run build

# 暴露端口
EXPOSE 3000

# 启动
CMD ["npm", "start"]
```

### 5.4 Backend requirements.txt

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
psycopg2-binary==2.9.9
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
httpx==0.26.0
playwright==1.41.0
apscheduler==3.10.4
beautifulsoup4==4.12.3
python-dotenv==1.0.0
```

---

## 6. 爬虫设计

### 6.1 数据来源
- **目标网站**: https://tophub.today/
- **抓取平台**: 知乎热榜、微博热搜、B站热门、抖音热榜

### 6.2 反爬策略
1. **使用 Playwright**: 模拟真实浏览器行为
2. **请求间隔**: 3-5秒随机延迟
3. **User-Agent轮换**: Playwright自动处理
4. **失败重试**: 指数退避，最多3次

### 6.3 Python爬虫实现

```python
# backend/app/services/crawler.py
import asyncio
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from app.models.hot_topic import HotTopic
from app.database import SessionLocal

PLATFORM_CONFIGS = {
    'zhihu': {'id': 'mproPpoq6O', 'name': '知乎'},
    'weibo': {'id': 'KqndgxeLl9', 'name': '微博'},
    'bilibili': {'id': '74KvxwokxM', 'name': 'B站'},
    'douyin': {'id': 'DpQvNABoNE', 'name': '抖音'},
}

async def crawl_platform(platform: str, page):
    """抓取单个平台的热点"""
    config = PLATFORM_CONFIGS[platform]
    url = f"https://tophub.today/n/{config['id']}"
    
    try:
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)  # 等待页面渲染
        
        topics = []
        rows = await page.query_selector_all('table tbody tr')
        
        for i, row in enumerate(rows[:50]):  # 最多50条
            try:
                cells = await row.query_selector_all('td')
                if len(cells) < 3:
                    continue
                    
                rank = await cells[0].inner_text()
                title_elem = await cells[1].query_selector('a')
                title = await title_elem.inner_text() if title_elem else await cells[1].inner_text()
                link = await title_elem.get_attribute('href') if title_elem else ''
                hot_value = await cells[2].inner_text()
                
                topics.append({
                    'platform': platform,
                    'rank': int(rank.strip()),
                    'title': title.strip(),
                    'url': f"https://tophub.today{link}" if link else '',
                    'hot_value': hot_value.strip(),
                })
            except Exception as e:
                print(f"Error parsing row {i}: {e}")
                continue
                
        return topics
    except Exception as e:
        print(f"Failed to crawl {platform}: {e}")
        return []

async def crawl_all_hot_topics():
    """抓取所有平台热点"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        all_topics = []
        for platform in PLATFORM_CONFIGS.keys():
            topics = await crawl_platform(platform, page)
            all_topics.extend(topics)
            await asyncio.sleep(5)  # 平台间延迟
        
        await browser.close()
        return all_topics

def save_topics_to_db(topics: list):
    """保存热点到数据库"""
    db = SessionLocal()
    try:
        for topic_data in topics:
            topic = HotTopic(**topic_data)
            db.add(topic)
        db.commit()
    finally:
        db.close()
```

### 6.4 定时任务配置

```python
# backend/app/tasks/hot_crawler.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.crawler import crawl_all_hot_topics, save_topics_to_db

scheduler = BackgroundScheduler()

def crawl_job():
    """定时抓取任务"""
    import asyncio
    topics = asyncio.run(crawl_all_hot_topics())
    save_topics_to_db(topics)
    print(f"Crawled {len(topics)} hot topics")

# 每小时执行一次
scheduler.add_job(crawl_job, 'interval', hours=1, id='hot_crawler')

def start_scheduler():
    scheduler.start()
```

---

## 7. MiniMax API 封装

```python
# backend/app/services/minimax.py
import httpx
from typing import List, Dict, Optional
from app.config import settings

class MiniMaxService:
    BASE_URL = "https://api.minimax.chat/v1"
    
    def __init__(self):
        self.api_key = settings.MINIMAX_API_KEY
        self.group_id = settings.MINIMAX_GROUP_ID
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """调用MiniMax API进行对话"""
        
        url = f"{self.BASE_URL}/text/chatcompletion_v2"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "MiniMax-Text-01",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # 解析响应
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                raise Exception(f"MiniMax API error: {data}")

# 系统Prompt模板
CREATIVE_ASSISTANT_PROMPT = """你是创作者的AI助手，帮助创作者基于热点话题进行内容创作。

当前讨论的热点：{hot_topic_title}

你可以：
1. 分析热点事件的背景和核心争议点
2. 提供多个切入角度供创作者选择
3. 帮助梳理论点和论据
4. 给出内容结构建议
5. 回答创作者的具体问题

请用专业、有洞察力的方式回答，帮助创作者产出优质内容。"""

minimax_service = MiniMaxService()
```

---

## 8. 开发排期

### Day 1 (5月11日) - 基础设施 + 热点广场
- [ ] 项目初始化 (Docker + FastAPI + Next.js)
- [ ] PostgreSQL + SQLAlchemy模型设计
- [ ] Alembic迁移配置
- [ ] Playwright爬虫开发
- [ ] 热点API (/api/hot)
- [ ] 热点广场前端页面
- [ ] Docker Compose本地运行

**Day1产出**: 可本地运行的热点列表页面

### Day 2 (5月12日) - 用户系统 + 创作对话
- [ ] 知乎OAuth集成
- [ ] JWT认证中间件
- [ ] MiniMax API集成
- [ ] 对话API (/api/chat)
- [ ] 对话页面前端
- [ ] 对话历史列表

**Day2产出**: 可登录并与AI对话

### Day 3 (5月13日) - 灵感卡片 + 数据面板
- [ ] 灵感卡片API (/api/cards)
- [ ] 卡片页面前端
- [ ] 作品数据API (/api/works, /api/stats)
- [ ] 数据面板图表
- [ ] UI优化 + Bug修复
- [ ] 部署脚本

**Day3产出**: 完整功能Demo

### Day 4 (5月14日) - 提交前
- [ ] 最终测试
- [ ] 部署到服务器
- [ ] 文档完善
- [ ] 正式提交

---

## 9. 环境变量配置

```bash
# .env 文件示例

# Database
DB_USER=creator
DB_PASSWORD=your_secure_password
DB_NAME=creator_assistant
DATABASE_URL=postgresql://creator:password@postgres:5432/creator_assistant

# MiniMax
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_GROUP_ID=your_group_id

# Zhihu OAuth
ZHIHU_CLIENT_ID=your_zhihu_client_id
ZHIHU_CLIENT_SECRET=your_zhihu_client_secret
ZHIHU_REDIRECT_URI=http://localhost:8000/api/auth/callback

# JWT
JWT_SECRET=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 10. 风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| tophub反爬升级 | 无法获取热点 | 使用Playwright模拟浏览器；准备备用数据源 |
| MiniMax API不稳定 | 对话功能异常 | 准备备用AI服务；添加失败提示 |
| Docker部署复杂 | 部署失败 | 准备简化版本（前端直连Vercel，后端Railway） |
| 知乎OAuth审核 | 无法登录 | 使用JWT模拟登录进行演示 |
| 时间不足 | 功能不完整 | 优先保证热点+对话两个核心功能 |

---

**文档结束**
