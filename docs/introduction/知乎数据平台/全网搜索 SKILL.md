接口说明、鉴权方式、示例代码与接入指南。

Docs

## 全网搜索 Skill

## 能力说明

该 Skill 提供面向 AI 助手与 Agent 的全网搜索能力，适合在生成回答前补充外部信息、扩展参考来源、获取更广范围的公开内容。

与底层接口相比，Skill 会将结果整理为更易消费的结构化输出。

## 下载方式

可直接下载 Skill 压缩包：

- `https://developer.zhihu.com/download/global_search_skills.zip`

## 适用场景

- 为问答系统补充站外公开信息
- 需要更广覆盖范围的内容检索
- 对某一主题进行快速信息扩展

## 输入参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | String | 是 | 搜索关键词 |
| `count` | Int | 否 | 期望返回数量，默认 `10` |

示例：

```json
{
  "query": "人工智能",
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
| `edit_time` | Int | 更新时间戳 |

响应示例：

```json
{
  "code": 0,
  "message": "success",
  "item_count": 2,
  "items": [
    {
      "title": "人工智能发展趋势与展望",
      "summary": "近年来，人工智能（AI）的发展速度令人瞩目 ...",
      "url": "https://example.com/article",
      "author_name": "张三",
      "edit_time": 1710000000
    }
  ]
}
```

## 使用建议

1. 若只需要知乎内容，建议改用知乎搜索 Skill，以获得更聚焦的结果。
2. 对于开放性问题，建议使用更完整的关键词组合，以提高内容覆盖质量。