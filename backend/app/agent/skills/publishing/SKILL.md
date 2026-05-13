---
name: publishing
description: 帮助创作者将内容发布到知乎圈子，支持发布想法、评论互动等操作
triggers:
  - "发布到知乎"
  - "帮我发想法"
  - "发到圈子"
  - "发帖"
  - "评论"
  - "回复"
  - "点赞"
tools:
  - zhihu_publish_pin
  - zhihu_create_comment
  - zhihu_reaction
  - zhihu_get_ring_detail
  - zhihu_get_comments
---

# 知乎发布

## 可用圈子
| 圈子 ID | 圈子名称 |
|---------|----------|
| 2001009660925334090 | OpenClaw 人类观察员 |
| 2015023739549529606 | A2A for Reconnect |
| 2029619126742656657 | 黑客松脑洞补给站 |

## 工作流程

### 发布想法
1. 确认用户要发布的内容（必须用户明确同意）
2. 确认目标圈子（默认：黑客松脑洞补给站）
3. 调用 `zhihu_publish_pin` 发布
4. 返回发布结果

### 浏览圈子
调用 `zhihu_get_ring_detail` 获取圈子最新帖子和互动数据。

### 评论互动
获取帖子评论后，用户选择评论或回复，调用 `zhihu_create_comment` 发表。

## 安全规则
- **必须经过用户确认才能发布**
- 每小时最多发布 5 条想法
- 每小时每个想法下最多 20 条评论
- 禁止批量、高频、无意义的内容发布
