# ComfyUI API 中间件

一个基于FastAPI的ComfyUI API封装中间件，提供RESTful API和Web调试界面。

## 功能特点

- ✅ **完整的ComfyUI API封装** - 支持所有ComfyUI核心功能
- ✅ **Web调试界面** - 美观的前端界面，支持工作流上传、参数调整、任务执行
- ✅ **实时状态更新** - WebSocket实时推送任务状态
- ✅ **工作流管理** - 支持工作流上传、保存、参数编辑
- ✅ **任务队列管理** - 查看队列状态，支持任务中断
- ✅ **历史记录** - 查看历史执行记录和结果
- ✅ **参数智能识别** - 自动识别工作流中的可编辑参数

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1. 复制 `.env.example` 为 `.env`
2. 修改配置文件中的 ComfyUI 服务器地址

```env
COMFYUI_COMFYUI_SERVER=192.168.48.123:8188
```

### 启动服务

```bash
python start.py
```

或指定参数：

```bash
python start.py --host 0.0.0.0 --port 8000 --comfyui-server 192.168.48.123:8188
```

### 访问服务

- **调试界面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/health

## 📚 文档

- **[API使用文档](./API_USAGE.md)** - 完整的API使用指南，包括参数说明和多种语言示例
- **[Postman使用指南](./POSTMAN_GUIDE.md)** - 如何使用Postman测试API，包含预配置的Collection
- **[示例代码](./examples/)** - Python示例代码，包括基础用法、批量生成、高级用法
- **[常见错误修复](./COMMON_ERRORS.md)** - 422、404等常见错误的快速修复指南⚡
- **[故障排查](./TROUBLESHOOTING.md)** - 常见问题和解决方案

## 🚀 快速开始 - API调用

### 方式1：使用示例代码（推荐）

```bash
# 运行基础示例
cd examples
python basic_usage.py

# 或批量生成
python batch_generate.py

# 或高级用法
python advanced_usage.py
```

### 方式2：Python代码

```python
# 完整示例见 examples/basic_usage.py
from examples.basic_usage import generate_image

result = generate_image(
    prompt="A beautiful sunset over the ocean",
    negative_prompt="blurry, low quality",
    seed=-1,  # 随机种子
    steps=20,
    width=1024,
    height=1024
)
```

### 方式3：使用Postman（推荐测试工具）

1. 导入Collection：
   ```
   在Postman中导入 ComfyUI_API.postman_collection.json
   ```

2. 发送请求：
   - 打开 "3. 提交工作流" 请求
   - 修改Body中的提示词
   - 点击 Send
   - task_id会自动保存到环境变量

3. 查询结果：
   - 打开 "4. 查询任务状态" 请求
   - 点击 Send（自动使用保存的task_id）

详细使用方法请查看 **[Postman使用指南](./POSTMAN_GUIDE.md)**

### 方式4：直接使用curl

```bash
curl -X POST http://localhost:8000/api/workflow/submit \
  -H "Content-Type: application/json" \
  -d @workflows/qwen_t2i_distill.json
```

更多示例请查看 **[API使用文档](./API_USAGE.md)**

## API 使用示例

### 提交工作流

```python
import requests
import json

# 读取工作流文件
with open('workflow.json', 'r') as f:
    workflow = json.load(f)

# 提交任务
response = requests.post(
    'http://localhost:8000/api/workflow/submit',
    json={
        'workflow': workflow,
        'params': {
            '6.text': '你的提示词',  # 修改节点6的text参数
            '3.seed': 12345,         # 修改节点3的seed参数
        },
        'timeout': 600
    }
)

task = response.json()
print(f"任务ID: {task['task_id']}")
```

### 查询任务状态

```python
task_id = "your-task-id"
response = requests.get(f'http://localhost:8000/api/task/{task_id}')
status = response.json()
print(f"任务状态: {status['status']}")
```

### WebSocket 实时监听

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'task_update') {
    console.log(`任务 ${data.task_id} 状态: ${data.status}`);
  }
};
```

## 主要API端点

### 系统管理
- `GET /api/health` - 健康检查
- `GET /api/system/info` - 系统信息
- `GET /api/nodes` - 获取所有节点信息
- `GET /api/queue` - 队列状态
- `POST /api/queue/clear` - 清空队列

### 工作流管理
- `POST /api/workflow/submit` - 提交工作流
- `POST /api/workflow/upload` - 上传工作流文件
- `GET /api/workflows` - 列出所有工作流
- `GET /api/workflow/{filename}` - 获取工作流详情
- `POST /api/workflow/update` - 更新工作流参数

### 任务管理
- `GET /api/task/{task_id}` - 获取任务状态
- `GET /api/tasks` - 列出所有任务
- `POST /api/interrupt/{prompt_id}` - 中断任务
- `GET /api/history` - 获取历史记录

### 资源获取
- `GET /api/image/{filename}` - 获取生成的图片

## 项目结构

```
├── main.py              # FastAPI主应用
├── comfyui_client.py    # ComfyUI客户端封装
├── config.py            # 配置管理
├── start.py             # 启动脚本
├── requirements.txt     # 依赖列表
├── static/              
│   └── index.html       # Web调试界面
├── workflows/           # 工作流存储目录
├── uploads/             # 上传文件目录
└── outputs/             # 输出文件目录
```

## 工作流参数说明

系统会自动识别工作流中的可编辑参数，主要包括：

- **CLIPTextEncode节点** - 文本提示词
- **KSampler节点** - 种子、步数、CFG、降噪强度
- **EmptySD3LatentImage节点** - 图像尺寸、批量大小
- **其他节点** - 根据widgets_values自动识别

## 注意事项

1. 确保ComfyUI服务器正常运行并可访问
2. 大型模型生成可能需要较长时间，请适当设置timeout
3. WebSocket连接会自动重连，无需手动处理
4. 支持同时运行多个任务（取决于ComfyUI服务器配置）

## 许可证

MIT
