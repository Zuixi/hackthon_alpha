接口说明、鉴权方式、示例代码与接入指南。

Docs

## 直答 Skill

## 能力说明

该 Skill 提供面向 AI 助手与 Agent 的直答能力，适合处理用户提问、知识问答、内容解释与总结等场景。

与底层接口相比，Skill 更强调面向助手调用的易用性，输入更简洁，输出更适合直接被上层应用消费。

## 下载方式

可直接下载 Skill 压缩包：

- `https://developer.zhihu.com/download/zhida_skills.zip`

## 适用场景

- 通用问答
- 知识解释与概念说明
- 内容总结与归纳
- 多轮对话中的单轮回答生成

## 输入参数

支持两种输入方式：

### 简化输入

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | String | 是 | 用户问题 |
| `model` | String | 是 | 模型档位，支持 `zhida-fast-1p5` 、 `zhida-thinking-1p5` 、 `zhida-agent` |
| `stream` | Bool | 否 | 是否流式处理，默认 `false` |

示例：

```json
{
  "query": "什么是 RAG？",
  "model": "zhida-thinking-1p5",
  "stream": false
}
```

### 对话式输入

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `model` | String | 是 | 模型档位，支持 `zhida-fast-1p5` 、 `zhida-thinking-1p5` 、 `zhida-agent` |
| `messages` | Array\[Message\] | 是 | 对话消息列表 |
| `stream` | Bool | 否 | 是否流式处理，默认 `false` |

Message：

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `role` | String | 否 | 消息角色 |
| `content` | String | 是 | 消息内容 |

示例：

```json
{
  "model": "zhida-agent",
  "messages": [
    {
      "role": "user",
      "content": "请总结一下 RAG 的核心思路"
    }
  ],
  "stream": true
}
```

## 输出参数

返回 JSON，主要字段如下：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `code` | Int | 调用结果状态码， `0` 表示成功 |
| `id` | String | 请求标识 |
| `model` | String | 实际使用的模型 |
| `stream` | Bool | 是否按流式方式处理 |
| `content` | String | 回答内容 |
| `reasoning_content` | String | 推理或思考内容 |
| `finish_reason` | String | 结束原因 |

响应示例：

```json
{
  "code": 0,
  "id": "chatcmpl-xxxx",
  "model": "zhida-thinking-1p5",
  "stream": false,
  "content": "RAG 是 Retrieval-Augmented Generation 的缩写，核心思路是在生成回答前先检索相关资料，再结合检索结果生成更准确的回答。",
  "reasoning_content": "先解释缩写，再说明工作流程与价值。",
  "finish_reason": "stop"
}
```

## 使用建议

1. `model` 为必填，不再提供默认模型兜底。
2. 对于通用问答场景，建议优先使用 `zhida-fast-1p5` 。
3. 对于更强调推理质量的场景，建议使用 `zhida-thinking-1p5` 。
4. 对于任务更复杂、需要更强规划能力的场景，可使用 `zhida-agent` 。
5. 简单问答场景可直接传 `query` ，接入成本更低。