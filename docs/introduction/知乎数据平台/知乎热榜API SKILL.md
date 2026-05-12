接口说明、鉴权方式、示例代码与接入指南。

Docs

## 知乎热榜 Skill

## 能力说明

该 Skill 提供面向 AI 助手与 Agent 的知乎热榜获取能力，适合用于热点追踪、内容推荐、趋势发现等场景。

输出为包含标题、链接、缩略图与摘要的热榜条目列表，便于上层应用直接消费。

## 下载方式

可直接下载 Skill 压缩包：

- `https://developer.zhihu.com/download/hot_list_skills.zip`

## 适用场景

- 获取当前知乎热点内容
- 为助手提供热点推荐素材
- 用于趋势观察与热点发现

## 输入参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `limit` | Int | 否 | 期望返回数量，默认 `30` ，最大 `30` |

示例：

```json
{
  "limit": 10
}
```

## 输出参数

返回 JSON，主要字段如下：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `code` | Int | 调用结果状态码， `0` 表示成功 |
| `message` | String | 状态说明 |
| `total` | Int | 实际热榜总条数 |
| `item_count` | Int | 实际返回条数 |
| `items` | Array\[Item\] | 热榜列表 |

Item：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `title` | String | 热榜标题 |
| `url` | String | 对应链接 |
| `thumbnail_url` | String | 缩略图 URL，无封面图时为空字符串 |
| `summary` | String | 内容摘要，无摘要时为空字符串 |

响应示例：

```json
{
  "code": 0,
  "message": "success",
  "total": 10,
  "item_count": 10,
  "items": [
    {
      "title": "如何评价某个热点问题？",
      "url": "https://www.zhihu.com/question/123456789",
      "thumbnail_url": "https://pic1.zhimg.com/v2-d4b0f8158e064dbcc71eb6ce970230a9.jpg",
      "summary": "这是该问题的内容摘要"
    }
  ]
}
```