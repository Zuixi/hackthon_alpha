# KNOWN GOTCHAS

- 维护后端协作文档时，优先按“模块职责”和“数据流”描述，避免绑定到具体文件名，减少目录调整后的文档失效风险。
- 后端协作文档建议控制在“快速扫读 1 分钟内可理解”的长度，优先清单化表达，避免过度展开。
- OAuth 场景下，`authorize` 与 `token exchange` 使用的 `redirect_uri` 必须完全一致，且优先使用前端回调地址（如 `${FRONTEND_URL}/auth/callback`），否则登录后会出现回跳失败或换 token 失败。
- OAuth 回调页不能只读取单一 `code` 参数；需要兼容查询串与 hash 中的 `code` / `authorization_code` / `auth_code`，否则会误判 “No authorization code received”。
- Docker 构建要同时兼顾速度和体积：构建阶段使用国内镜像源（PyPI 清华、npm npmmirror），运行阶段只保留必要产物并清理缓存，避免把编译依赖带入最终镜像。
- Debian 系基础镜像仅替换 pip 源不够，`apt` 仍会走海外默认源；需要显式替换系统源（兼容 `sources.list` 与 `debian.sources`）后再 `apt-get update`。
- 知乎 OAuth API 中关注列表(`/user/followees`)和关注动态(`/user/moments`)需要用户的 `zhihu_token`（而非 JWT），调用时需从 User model 取 `zhihu_token` 传入。
- Redis 缓存 key 需要包含用户维度（如 `social:followees:{user_id}`），避免不同用户缓存数据串扰。
