# API 统一响应格式说明

## 📋 响应格式

所有返回 JSON 数据的 API 接口都使用统一的响应格式（媒体流接口除外）：

```json
{
  "code": 200,
  "success": true,
  "message": "操作成功",
  "data": {
    // 实际数据
  }
}
```

## 🎯 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 业务状态码（200: 成功, 400: 客户端错误, 404: 未找到, 500: 服务器错误） |
| `success` | bool | 操作是否成功 |
| `message` | string | 响应消息，描述操作结果 |
| `data` | any | 实际的业务数据，可以是对象、数组或其他类型 |

## 📝 响应示例

### ✅ 成功响应

```json
{
  "code": 200,
  "success": true,
  "message": "获取任务状态成功",
  "data": {
    "task_id": "abc-123",
    "status": "completed",
    "result": { ... }
  }
}
```

### ❌ 错误响应

```json
{
  "code": 404,
  "success": false,
  "message": "任务不存在",
  "data": null
}
```

## 🔧 使用方式

### 在代码中使用

```python
from core.response import R

# 成功响应
@router.get("/example")
async def example():
    return R.success(
        data={"key": "value"},
        message="操作成功"
    )

# 错误响应
@router.get("/error")
async def error_example():
    return R.error(
        message="操作失败",
        code=500
    )

# 快捷方法
return R.not_found(message="资源不存在")  # 404
return R.client_error(message="参数错误")  # 400
return R.server_error(message="服务器错误")  # 500
return R.unauthorized(message="未授权")  # 401
return R.forbidden(message="禁止访问")  # 403
```

## 📊 状态码说明

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 | 成功 | 操作成功完成 |
| 400 | 客户端错误 | 请求参数错误、格式错误等 |
| 401 | 未授权 | 需要身份认证 |
| 403 | 禁止访问 | 无权限访问 |
| 404 | 未找到 | 资源不存在 |
| 500 | 服务器错误 | 服务器内部错误 |
| 503 | 服务不可用 | 服务暂时不可用（如 ComfyUI 服务器连接失败） |

## 🚫 例外情况

以下接口**不使用**统一响应格式，直接返回数据流：

- `GET /api/image/{filename}` - 返回图片流
- `GET /api/task/{task_id}/image` - 返回任务图片流
- `GET /api/video/{filename}` - 返回视频流
- `GET /api/task/{task_id}/video` - 返回任务视频流

这些接口返回 `StreamingResponse`，MIME 类型根据文件类型自动设置。

## 💡 前端处理示例

### JavaScript/Fetch

```javascript
fetch('/api/tasks')
  .then(res => res.json())
  .then(response => {
    if (response.success) {
      console.log('数据:', response.data);
      console.log('消息:', response.message);
    } else {
      console.error('错误:', response.message);
    }
  });
```

### Axios

```javascript
axios.get('/api/tasks')
  .then(response => {
    const { success, message, data } = response.data;
    if (success) {
      console.log('数据:', data);
    } else {
      console.error('错误:', message);
    }
  })
  .catch(error => {
    console.error('请求失败:', error);
  });
```

### Python/requests

```python
import requests

response = requests.get('http://localhost:8000/api/tasks')
result = response.json()

if result['success']:
    print('数据:', result['data'])
else:
    print('错误:', result['message'])
```

## 🔄 迁移说明

### 旧格式
```json
{
  "task_id": "abc-123",
  "status": "completed"
}
```

### 新格式
```json
{
  "code": 200,
  "success": true,
  "message": "获取任务状态成功",
  "data": {
    "task_id": "abc-123",
    "status": "completed"
  }
}
```

前端代码需要调整为从 `response.data` 中获取实际数据。

## ✨ 优势

1. **统一性**: 所有接口返回格式一致，便于前端统一处理
2. **清晰性**: 通过 `success` 字段明确操作是否成功
3. **信息丰富**: `message` 字段提供友好的提示信息
4. **易于扩展**: 可以轻松添加其他字段如 `timestamp`、`trace_id` 等
5. **标准化**: 符合 RESTful API 最佳实践

