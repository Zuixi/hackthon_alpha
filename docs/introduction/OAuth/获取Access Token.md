接口目录

## 获取 access\_token

## 接口说明

使用用户授权后获得的 `authorization_code` 换取 `access_token` 。

> 授权流程请参考  [快速开始](./快速开始.md) 。

## 接口信息

| 说明        | 值                                       |
| ----------- | ---------------------------------------- |
| HTTP URL    | `https://openapi.zhihu.com/access_token` |
| HTTP Method | POST                                     |

## 请求参数

| 参数          | 类型   | 必填 | 说明                                  |
| ------------- | ------ | ---- | ------------------------------------- |
| app\_id       | string | 是   | 第三方 APP\_ID（需向知乎申请）        |
| app\_key      | string | 是   | 第三方 APP\_KEY（需向知乎申请）       |
| grant\_type   | string | 是   | 固定值： `authorization_code`         |
| redirect\_uri | string | 是   | 申请 APP\_ID 时所填写的重定向地址     |
| code          | string | 是   | 用户授权后生成的 `authorization_code` |

## 响应数据

### 成功响应示例

```json
{
  "access_token": "xxx",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 响应字段说明

| 字段          | 类型   | 说明                  |
| ------------- | ------ | --------------------- |
| access\_token | string | 访问令牌              |
| token\_type   | string | 令牌类型，如 `Bearer` |
| expires\_in   | long   | 过期时间（秒）        |

## curl 示例

```bash
curl -s -X POST "https://openapi.zhihu.com/access_token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "app_id=${APP_ID}" \
  -d "app_key=${APP_KEY}" \
  -d "grant_type=authorization_code" \
  -d "redirect_uri=${REDIRECT_URI}" \
  -d "code=${CODE}"
```