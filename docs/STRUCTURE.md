# 项目结构说明

## 📁 项目结构

```
Comfyapi/
├── core/                       # 核心业务代码
│   ├── __init__.py            # 模块导出
│   ├── models.py              # Pydantic 数据模型定义
│   ├── managers.py            # 任务管理器和连接管理器
│   ├── utils.py               # 工具函数
│   └── api/                   # API 路由模块
│       ├── __init__.py        # API 路由导出
│       ├── system.py          # 系统信息接口 (~140行)
│       ├── text2image.py      # 文生图接口 (~200行)
│       ├── workflow.py        # 工作流管理接口 (~300行)
│       ├── task.py            # 任务查询接口 (~180行)
│       └── media.py           # 媒体文件获取接口 (~450行)
├── workflows/                  # 工作流文件存储
├── uploads/                    # 上传文件存储
├── outputs/                    # 输出文件存储
├── static/                     # 静态文件
├── comfyui_client.py          # ComfyUI 客户端封装
├── config.py                  # 配置文件
├── main.py                    # 主应用入口 (~130行)
└── requirements.txt           # 依赖包列表
```

## 🎯 设计原则

### 1. 单一职责原则
每个模块都有明确的职责：
- **models.py**: 只定义数据模型
- **managers.py**: 只管理任务和连接
- **utils.py**: 只提供工具函数
- **api/*.py**: 每个文件只负责一类接口

### 2. 依赖注入
所有路由通过 `setup_*_routes()` 函数接收依赖，便于测试和维护：

```python
# 示例
def setup_text2image_routes(
  comfyui_server: str,
  task_manager: TaskManager,
  connection_manager: ConnectionManager,
  workflow_dir: Path
):
  # 路由定义...
  return router
```

### 3. 文件大小限制
- 单个文件不超过 500 行代码
- main.py 精简到 ~130 行
- 最大的文件 media.py 约 450 行

## 📦 模块说明

### core/models.py
定义所有 Pydantic 数据模型：
- `WorkflowSubmit`: 工作流提交
- `WorkflowUpdate`: 工作流更新
- `TaskResponse`: 任务响应
- `SystemInfo`: 系统信息
- `SimpleText2ImageRequest`: 文生图请求

### core/managers.py
提供两个管理器类：
- `TaskManager`: 管理任务状态和结果
- `ConnectionManager`: 管理 WebSocket 连接

### core/utils.py
提供工具函数：
- `apply_params_to_workflow()`: 将参数应用到工作流

### core/api/system.py
系统信息相关接口：
- `GET /api/health` - 健康检查
- `GET /api/system/info` - 系统信息
- `GET /api/diagnose` - 系统诊断
- `GET /api/nodes` - 节点信息
- `GET /api/queue` - 队列状态
- `POST /api/queue/clear` - 清空队列
- `POST /api/interrupt/{prompt_id}` - 中断任务

### core/api/text2image.py
文生图接口：
- `POST /api/text2image` - 简化的文生图接口
- 包含后台任务处理逻辑

### core/api/workflow.py
工作流管理接口：
- `POST /api/workflow/submit` - 提交工作流
- `POST /api/workflow/upload` - 上传工作流文件
- `GET /api/workflows` - 列出工作流
- `GET /api/workflow/{filename}` - 获取工作流
- `POST /api/workflow/update` - 更新工作流节点

### core/api/task.py
任务查询接口：
- `GET /api/task/{task_id}` - 获取任务状态
- `GET /api/tasks` - 列出所有任务
- `GET /api/history` - 获取历史记录
- `GET /api/history/{prompt_id}` - 获取指定历史记录

### core/api/media.py
媒体文件获取接口：
- `GET /api/image/{filename}` - 获取图片
- `GET /api/task/{task_id}/image` - 获取任务图片
- `GET /api/task/{task_id}/images` - 获取任务图片列表
- `GET /api/video/{filename}` - 获取视频
- `GET /api/task/{task_id}/video` - 获取任务视频
- `GET /api/task/{task_id}/videos` - 获取任务视频列表

### main.py
应用入口，职责：
- 创建 FastAPI 应用
- 配置 CORS
- 创建管理器实例
- 注册所有路由
- 提供根路径和 WebSocket 端点
- 挂载静态文件

## 🚀 使用方式

### 启动服务

```bash
python main.py
```

或

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 环境变量

- `COMFYUI_SERVER`: ComfyUI 服务器地址（默认: 192.168.48.123:8188）

### 示例代码

```python
from core.managers import TaskManager
from core.utils import apply_params_to_workflow

# 创建任务管理器
task_manager = TaskManager()

# 添加任务
task_manager.add_task("task_001", {
  "workflow_type": "text2image",
  "params": {"prompt": "a cat"}
})

# 应用参数到工作流
workflow = {"1": {"inputs": {"seed": 0}}}
params = {"1.seed": 42}
new_workflow = apply_params_to_workflow(workflow, params)
```

## 🔧 扩展指南

### 添加新的 API 模块

1. 在 `core/api/` 创建新文件，如 `new_feature.py`
2. 定义路由和 setup 函数：

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["新功能"])

def setup_new_feature_routes(comfyui_server: str):
  @router.get("/new_feature")
  async def new_feature():
    return {"message": "Hello"}
  
  return router
```

3. 在 `core/api/__init__.py` 导出：

```python
from .new_feature import router as new_feature_router
__all__ = [..., 'new_feature_router']
```

4. 在 `main.py` 注册路由：

```python
from core.api.new_feature import setup_new_feature_routes

new_feature_router = setup_new_feature_routes(COMFYUI_SERVER)
app.include_router(new_feature_router)
```

### 添加新的数据模型

在 `core/models.py` 添加：

```python
class NewModel(BaseModel):
  field1: str
  field2: int
```

### 添加新的工具函数

在 `core/utils.py` 添加：

```python
def new_utility_function(param1, param2):
  # 实现
  pass
```

## 📊 代码统计

- **总文件数**: 12 个核心文件
- **main.py**: ~130 行（减少 90%）
- **最大文件**: media.py ~450 行（< 500 行限制）
- **平均文件大小**: ~200 行
- **耦合度**: 低（通过依赖注入）
- **可测试性**: 高（模块化设计）

## ✅ 优势

1. **模块化**: 每个功能独立，易于维护
2. **可扩展**: 添加新功能只需创建新模块
3. **可测试**: 依赖注入便于单元测试
4. **清晰**: 结构清晰，易于理解
5. **解耦**: 业务逻辑与路由分离
6. **规范**: 遵循编码规范，文件大小合理

## 🔄 迁移说明

从旧版本迁移：
1. 所有 API 路径保持不变
2. 功能完全兼容
3. 只是代码组织方式改变
4. 无需修改客户端代码

## 📝 最佳实践

1. 新增功能时，先在对应模块添加
2. 如果模块超过 500 行，考虑拆分
3. 使用依赖注入而非全局变量
4. 保持 main.py 简洁，只负责组装
5. 工具函数放在 utils.py
6. 数据模型放在 models.py

basicSR 
`pip install --no-cache-dir -U "git+https://github.com/XPixelGroup/BasicSR.git"`