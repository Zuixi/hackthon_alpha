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

## USER PROFILES

