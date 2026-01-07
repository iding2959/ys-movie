# 专用工作流 API

本文件夹包含针对特定ComfyUI工作流封装的专用API。

## 📁 文件结构

```
specialized/
├── __init__.py           # 模块导出
├── super_video.py        # SuperVideo视频放大API（4x超分辨率）
└── README.md             # 本文件
```

## 🎯 设计理念

### 为什么要创建specialized文件夹？

将专用工作流API与通用API分离，具有以下优势：

1. **清晰的代码组织**
   - 通用API（system, task, media, workflow）保留在 `core/api/`
   - 专用工作流API集中在 `core/api/specialized/`

2. **易于扩展**
   - 新增专用工作流API时，直接在此文件夹添加即可
   - 不会污染主API目录

3. **职责分明**
   - 通用API：处理ComfyUI的基础功能
   - 专用API：针对特定场景的高级封装

## 📝 如何添加新的专用API

### 步骤1: 创建新的API文件

在 `specialized/` 文件夹中创建新文件，例如 `my_workflow.py`：

```python
"""
我的自定义工作流API
"""
from fastapi import APIRouter, BackgroundTasks
from core.comfyui_client import ComfyUIClient
from core.managers import TaskManager, ConnectionManager
from core.response import R, ResponseModel
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/my_workflow", tags=["我的工作流"])


class MyWorkflowRequest(BaseModel):
    """请求参数"""
    prompt: str = Field(..., description="提示词")
    # 添加其他参数...


def setup_my_workflow_routes(
    comfyui_server: str,
    task_manager: TaskManager,
    connection_manager: ConnectionManager
):
    """设置路由"""
    
    @router.post("/generate", response_model=ResponseModel)
    async def generate(
        data: MyWorkflowRequest,
        background_tasks: BackgroundTasks
    ):
        """生成接口"""
        # 实现你的逻辑...
        pass
    
    return router
```

### 步骤2: 更新 `__init__.py`

在 `specialized/__init__.py` 中添加导出：

```python
from .my_workflow import router as my_workflow_router, setup_my_workflow_routes

__all__ = [
    # ... 其他导出
    'my_workflow_router',
    'setup_my_workflow_routes'
]
```

### 步骤3: 在 `main.py` 中注册

```python
# 导入
from core.api.specialized.my_workflow import setup_my_workflow_routes

# 设置路由
my_workflow_router = setup_my_workflow_routes(
    COMFYUI_SERVER,
    task_manager,
    connection_manager
)

# 注册到应用
app.include_router(my_workflow_router)
```

## 📚 现有API说明

### super_video.py

**路径**: `/api/super_video`

**功能**: AI视频超分辨率处理，将低分辨率视频放大4倍

**特点**:
- 支持多种放大模型（RealESRGAN, 4x_foolhardy等）
- 自动保留原视频的帧率和音频
- 智能分块处理大视频
- 支持GPU加速

**主要端点**:
1. `/api/super_video/upload_and_upscale` - 上传视频并放大
2. `/api/super_video/upscale` - 使用已上传视频放大

**使用示例**:
```python
import requests

url = "http://localhost:8000/api/super_video/upload_and_upscale"

with open("video.mp4", "rb") as f:
    files = {"video": f}
    data = {
        "model_name": "RealESRGAN_x4plus_anime_6B",
        "tile_size": 512,
        "timeout": 600
    }
    
    response = requests.post(url, files=files, data=data)
    result = response.json()
    print(f"任务ID: {result['data']['task_id']}")
```


## 🔧 最佳实践

### 1. 命名规范

- 文件名：使用小写字母和下划线，如 `text2image.py`、`wan22_i2v.py`
- 路由前缀：使用描述性名称，如 `/api/text2image`、`/api/wan22_i2v`
- 函数名：清晰描述功能，如 `setup_text2image_routes`

### 2. 参数验证

使用 Pydantic 模型进行参数验证：

```python
class MyRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000, description="提示词")
    steps: int = Field(default=10, ge=1, le=100, description="步数")
    seed: int = Field(default=-1, description="随机种子，-1为随机")
```

### 3. 错误处理

始终返回统一的响应格式：

```python
try:
    # 你的逻辑
    return R.success(data={...}, message="成功")
except Exception as e:
    logger.error(f"错误: {e}")
    return R.server_error(message=f"失败: {str(e)}")
```

### 4. 日志记录

记录关键操作：

```python
logger.info(f"📝 任务已提交: {prompt_id}")
logger.error(f"❌ 操作失败: {error}")
```

### 5. 后台任务

使用后台任务处理长时间运行的操作：

```python
background_tasks.add_task(wait_for_completion, prompt_id, timeout)
```

## 📖 参考文档

- [通用API文档](../../../docs/API_USAGE.md)
- [工作流适配指南](../../../docs/WORKFLOW_ADAPTATION_GUIDE.md)
- [FastAPI官方文档](https://fastapi.tiangolo.com/)

## 💡 未来规划

计划添加的专用API：

- [x] SuperVideo视频放大API
- [ ] 文生图API
- [ ] 图生视频API
- [ ] 音频驱动视频API
- [ ] 图像超分辨率API
- [ ] 风格迁移API

## 🤝 贡献指南

添加新的专用API时，请确保：

1. 遵循现有代码风格
2. 添加完整的类型注解
3. 编写清晰的文档字符串
4. 添加使用示例
5. 更新本README

---

**最后更新**: 2026-01-07
**维护者**: Chunli Ding

