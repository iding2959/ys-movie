# 专用工作流 API

本文件夹包含针对特定ComfyUI工作流封装的专用API。

## 📁 文件结构

```
specialized/
├── __init__.py           # 模块导出
├── text2image.py         # 文生图API（基于qwen_t2i_distill工作流）
├── wan22_i2v.py          # Wan2.2图生视频API（支持5-30秒智能拼接）
├── super_video.py        # SuperVideo视频放大API（4x超分辨率）
├── infinitetalk_i2v.py   # InfiniteTalk音频驱动视频API（口型同步）
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

### text2image.py

**路径**: `/api/text2image`

**功能**: 简化的文生图接口，基于 `qwen_t2i_distill` 工作流

**特点**:
- 只需提供提示词即可生成
- 自动处理随机种子
- 支持自定义尺寸和步数

**使用示例**:
```python
import requests

url = "http://localhost:8000/api/text2image"
data = {
    "prompt": "A beautiful landscape",
    "negative_prompt": "blurry",
    "width": 1328,
    "height": 1328,
    "steps": 10,
    "seed": -1
}

response = requests.post(url, json=data)
result = response.json()
print(f"任务ID: {result['data']['task_id']}")
```

### wan22_i2v.py

**路径**: `/api/wan22_i2v`

**功能**: Wan2.2图生视频，支持智能时长控制

**特点**:
- 支持5-30秒视频生成
- 自动片段拼接（每5秒一个片段）
- 颜色匹配确保视觉连贯
- 一键上传图片并生成

**主要端点**:
1. `/api/wan22_i2v/upload_and_generate` - 上传图片并生成（推荐）
2. `/api/wan22_i2v/generate` - 使用已上传图片生成

**使用示例**:
```python
import requests

url = "http://localhost:8000/api/wan22_i2v/upload_and_generate"

with open("image.png", "rb") as f:
    files = {"image": f}
    data = {
        "prompt": "A beautiful woman walking",
        "duration": 10,  # 10秒 = 2个片段
        "width": 480,
        "height": 832,
        "frame_rate": 16
    }
    
    response = requests.post(url, files=files, data=data)
    result = response.json()
    print(f"任务ID: {result['data']['task_id']}")
```

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

### infinitetalk_i2v.py

**路径**: `/api/infinitetalk-i2v`

**功能**: 音频驱动的口型同步视频生成，让静态图片开口说话

**特点**:
- 上传人物图片和音频，生成口型同步视频
- 支持多种分辨率（720x480、480x720、832x480）
- 自动音频裁剪和人声分离
- 高质量口型同步效果

**主要端点**:
1. `/api/infinitetalk-i2v/generate` - 生成音频驱动视频（POST）
2. `/api/task/{task_id}` - 查询任务状态（GET，通用接口）

**使用示例**:
```python
import requests

# 1. 提交生成任务（最简单方式，只需上传文件）
url = "http://localhost:8000/api/infinitetalk-i2v/generate"

with open("person.png", "rb") as img_file, open("audio.wav", "rb") as audio_file:
    files = {
        "image": img_file,
        "audio": audio_file
    }
    # 所有参数都是可选的，会自动使用最优默认值
    # 音频时长会自动检测
    response = requests.post(url, files=files)
    result = response.json()
    task_id = result['data']['task_id']

# 2. 查询任务状态（使用通用接口）
status_url = f"http://localhost:8000/api/task/{task_id}"
response = requests.get(status_url)
task_info = response.json()

# 3. 高级用法：自定义参数
with open("person.png", "rb") as img_file, open("audio.wav", "rb") as audio_file:
    files = {
        "image": img_file,
        "audio": audio_file
    }
    data = {
        "prompt": "A person passionately speaking",
        "width": 720,
        "height": 480,
        "steps": 4,
        "cfg": 1.0,
        "fps": 25,
        "audio_start_time": "0:00",
        "audio_end_time": "10:00"
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

- [Wan2.2 API 完整文档](../../../WAN22_I2V_API.md)
- [通用API文档](../../../API_USAGE.md)
- [FastAPI官方文档](https://fastapi.tiangolo.com/)

## 💡 未来规划

计划添加的专用API：

- [x] Wan2.2图生视频API
- [x] SuperVideo视频放大API
- [x] InfiniteTalk音频驱动视频API
- [ ] HiDream图像生成API
- [ ] 视频编辑API（剪辑、拼接、特效）
- [ ] 图像超分辨率API
- [ ] 风格迁移API
- [ ] 图像修复API

## 🤝 贡献指南

添加新的专用API时，请确保：

1. 遵循现有代码风格
2. 添加完整的类型注解
3. 编写清晰的文档字符串
4. 添加使用示例
5. 更新本README

---

**最后更新**: 2025-11-12
**维护者**: ComfyAPI Team

