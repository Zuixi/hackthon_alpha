接口说明、鉴权方式、示例代码与接入指南。

Docs

## 知乎搜索 Skill

## 能力说明

该 Skill 提供面向 AI 助手与 Agent 的知乎站内搜索能力，适合在回答问题前补充知乎内容、检索高相关讨论、获取站内观点与经验。

与底层接口相比，Skill 会将搜索结果整理为更适合上层应用处理的结构化数据。

## 下载方式

可直接下载 Skill 压缩包：

- `https://developer.zhihu.com/download/zhihu_search_skills.zip`

## 适用场景

- 为问答系统补充知乎站内参考内容
- 基于关键词检索问题、回答与文章
- 生成基于知乎内容的推荐或摘要

## 输入参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | String | 是 | 搜索关键词 |
| `count` | Int | 否 | 期望返回数量，默认 `10` ，最大 `10` |

示例：

```json
{
  "query": "RAG",
  "count": 5
}
```

## 输出参数

返回 JSON，主要字段如下：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `code` | Int | 调用结果状态码， `0` 表示成功 |
| `message` | String | 状态说明 |
| `item_count` | Int | 实际返回条数 |
| `items` | Array\[Item\] | 搜索结果列表 |

Item：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `title` | String | 内容标题 |
| `summary` | String | 内容摘要 |
| `url` | String | 内容链接 |
| `author_name` | String | 作者名称 |
| `vote_up_count` | Int | 赞同数 |
| `comment_count` | Int | 评论数 |
| `edit_time` | Int | 更新时间戳 |

响应示例：

```json
{
  "code": 0,
  "message": "success",
  "item_count": 2,
  "items": [
    {
      "title": "RAG 评测方法综述",
      "summary": "本文介绍了主流 RAG 评测框架，包括 RAGAS、TruLens ...",
      "url": "https://zhuanlan.zhihu.com/p/123456789",
      "author_name": "张三",
      "vote_up_count": 128,
      "comment_count": 15,
      "edit_time": 1710000000
    }
  ]
}
```

## 使用建议

1. 建议使用更具体的关键词，以提高结果相关性。
2. 如仅需为回答补充少量参考内容，通常设置 `count=3` 到 `5` 即可。
3. 若需要更大范围的信息补充，可考虑使用全网搜索 Skill。