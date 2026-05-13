# PROJECT CONTEXT MEMORY

SUMMARIZE global project status/system environment/user preferences/etc BY USING ONE SIMPLE SENTENCE.

## MEMORY LISTS

- 后端协作文档应以“分层职责 + 业务域流程 + 外部依赖约定”组织，避免绑定具体文件名以提升长期可维护性。
- 当前团队偏好后端 Agent 指南采用精简清单风格，便于快速扫读和执行。
- 前端 Agent 指南也采用同一精简清单规范，突出鉴权流、React Query 缓存一致性与流式对话稳定性。
- OAuth 登录链路要求后端与前端统一使用前端回调地址（`${FRONTEND_URL}/auth/callback`）作为默认 `redirect_uri`，避免授权成功后回跳失败。
- 前端 OAuth 回调页需要兼容不同参数来源（query/hash）和参数命名（`code`/`authorization_code`/`auth_code`），避免授权码解析失败。
- Docker 构建加速必须覆盖系统源与语言包源两层：Debian/Alpine 系统源 + PyPI/npm 镜像，并结合多阶段构建控制最终镜像体积。

- 缓存策略已从内存字典迁移到 Redis，热点 1h TTL、关注列表 5min TTL、关注动态 3min TTL；cache service 设计为连接失败自动降级（不阻塞请求）。
- Docker Compose 中 Redis 镜像需使用华为 SWR 镜像源（`swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/redis:7-alpine`），避免 Docker Hub 拉取超时。
- 前端社交圈页面（`/social`）通过 Tab 切换关注列表和关注动态，数据来源为知乎 OAuth API，需要用户已绑定知乎 token。
- 热榜数据由后台调度器每 30 分钟自动抓取（FastAPI lifespan + asyncio），存入 PostgreSQL 并自动清理 5 天前数据；前端支持"最新/历史"双视图，历史以天为卡片按批次展示。
- 知乎开发者接口 Bearer 鉴权凭证已统一收敛到 `ZHIHU_ACCESS_SECRET`，仓库内仅保留单一开发者鉴权变量。
- 知乎开发者接口域名统一使用 `https://developer.zhihu.com`（而非 `https://api.zhihu.com`），否则热榜调度会出现 404。
- 热点广场已升级为多平台聚合：NewsNow 覆盖知乎/微博/抖音/头条/B站/百度/澎湃/贴吧，调度器每 30 分钟统一抓取并共享 `fetch_batch`；知乎原生 API 保留为可配置回退源（`HOT_ZHIHU_SOURCE_MODE`）。
- 关键词过滤引擎支持普通词、必须词(+)、排除词(!)、正则(//)、别名(=>)、组名([])、上限(@N) 等语法，规则文件位于 `backend/config/keyword_rules.txt`。
- 前端热点广场支持四种视图：全部（混合排序）、按平台（分组折叠）、按主题（关键词分组）、历史（按天/批次），并支持平台芯片过滤和标题搜索。
- 后端新增 `GET /api/hot/source-status` 用于诊断知乎当前来源（按最新批次实际入库 `source` 聚合判定），可快速确认是否已回退到原生 API。
- 合并高风险分支时优先采用“选择性合并”策略：仅引入目标能力（本次为 `backend/app/agent/*` 与 chat 接入），保留主分支既有热点/社交链路并通过 `docker compose up -d` + 核心接口冒烟验证回归。
- 社交圈已扩展粉丝能力：新增 `followers` 列表与按天快照统计，粉丝数由后台调度器按 `Asia/Shanghai` 每日 20:00 固定采集；前端分页必须使用后端返回的 `has_more/is_end`，禁止硬编码页大小推断是否可翻页。
- 热点广场体验策略：`全部` 视图默认采用卡片布局，平台筛选区保持全量平台平铺，避免通过 `+N` 折叠隐藏平台入口。
- 热点广场平台筛选在窄屏使用横向滚动（`overflow-x-auto + min-w-max`），在较宽屏幕继续允许换行，兼顾可达性与信息密度。
- 热点广场 UI 已按 `ui-polish.md` 精细化重构：排名 10 级渐变色阶、平台品牌色圆点、状态 Badge（新上榜/飙升/高热/下降中）、Sparkline SVG 趋势图、热度值格式化（w/亿）、Hover 滑入操作按钮组、列表/卡片双视图切换（localStorage 持久化）、改进的骨架屏和空状态；状态和趋势数据为前端 Mock，后端扩展后可无缝切换。

## USER PROFILES

