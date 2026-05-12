# KNOWN GOTCHAS

- 维护后端协作文档时，优先按“模块职责”和“数据流”描述，避免绑定到具体文件名，减少目录调整后的文档失效风险。
- 后端协作文档建议控制在“快速扫读 1 分钟内可理解”的长度，优先清单化表达，避免过度展开。
- OAuth 场景下，`authorize` 与 `token exchange` 使用的 `redirect_uri` 必须完全一致，且优先使用前端回调地址（如 `${FRONTEND_URL}/auth/callback`），否则登录后会出现回跳失败或换 token 失败。
- OAuth 回调页不能只读取单一 `code` 参数；需要兼容查询串与 hash 中的 `code` / `authorization_code` / `auth_code`，否则会误判 “No authorization code received”。
- Docker 构建要同时兼顾速度和体积：构建阶段使用国内镜像源（PyPI 清华、npm npmmirror），运行阶段只保留必要产物并清理缓存，避免把编译依赖带入最终镜像。
- Debian 系基础镜像仅替换 pip 源不够，`apt` 仍会走海外默认源；需要显式替换系统源（兼容 `sources.list` 与 `debian.sources`）后再 `apt-get update`。
- 知乎 OAuth API 中关注列表(`/user/followees`)和关注动态(`/user/moments`)需要用户的 `zhihu_token`（而非 JWT），调用时需从 User model 取 `zhihu_token` 传入。
- Redis 缓存 key 需要包含用户维度（如 `social:followees:{user_id}`），避免不同用户缓存数据串扰。
- 知乎热榜 API (`developer.zhihu.com/api/v1/content/hot_list`) 使用 `Authorization: Bearer <access_secret>` 鉴权（不是 x-api-key），必须携带 `X-Request-Timestamp` 秒级时间戳头，查询参数 `Limit` 首字母大写且最大 30。
- `ZHIHU_DEV_BASE_URL` 必须配置为 `https://developer.zhihu.com`；若误设为 `https://api.zhihu.com`，热榜等开发者接口会返回 404。
- `ZHIHU_ACCESS_SECRET` 与开发者接口 Bearer 鉴权使用的是同一凭证，项目中应只保留 `ZHIHU_ACCESS_SECRET` 单变量，避免双变量配置漂移与排障歧义。
- 知乎热榜 API 响应结构：顶层 `Code/Message/Data`，Data 含 `Total` 和 `Items[]`（`Title/Url/ThumbnailUrl/Summary`），字段名均为 PascalCase。
- 热榜后台调度器使用 `asyncio.create_task` + FastAPI lifespan 实现，无需额外依赖（如 APScheduler/Celery）。
- `hot_topics` 表的 `fetch_batch` 字段用于关联同一批次抓取的数据，格式为 ISO 时间字符串（`YYYY-MM-DDTHH:MM:SS`），前端按此字段分组展示。
