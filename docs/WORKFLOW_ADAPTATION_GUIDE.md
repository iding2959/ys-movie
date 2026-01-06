# ComfyUI 工作流适配指南

本文档详细说明如何将 ComfyUI 工作流适配为专用 API，包括常见错误及解决方案。

## 📋 目录

- [准备工作](#准备工作)
- [工作流导出](#工作流导出)
- [API 开发流程](#api-开发流程)
- [常见错误及解决方案](#常见错误及解决方案)
- [最佳实践](#最佳实践)
- [完整示例](#完整示例)

---

## 准备工作

### 1. 理解工作流结构

在开始适配之前，需要了解 ComfyUI 的两种工作流格式：

#### UI 格式（用于界面）
```json
{
  "id": "xxx",
  "nodes": [
    {
      "id": 203,
      "type": "LoadImage",
      "widgets_values": ["image.png"]
    }
  ],
  "links": [...],
  "groups": [...]
}
```

#### API 格式（用于后端提交）⭐
```json
{
  "203": {
    "inputs": {
      "image": "image.png"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "加载图像"
    }
  }
}
```

**重要**: 后端 API 必须使用 **API 格式**！

### 2. 确定需要暴露的参数

分析工作流，确定哪些参数需要让用户配置：

- ✅ 输入文件（图片、视频、音频）
- ✅ 提示词（prompt、negative_prompt）
- ✅ 生成参数（steps、cfg、seed、尺寸）
- ✅ 输出设置（帧率、时长、格式）
- ❌ 模型路径（通常固定）
- ❌ 内部节点连接（不应修改）

---

## 工作流导出

### 正确的导出方式 ⭐

在 ComfyUI 界面中：

1. 打开你的工作流
2. 点击右上角菜单
3. 选择 **"Save (API Format)"** 或 **"导出（API 格式）"**
4. 保存到 `workflows/` 目录

**验证导出格式**:
```python
import json

with open('workflows/your_workflow.json') as f:
    workflow = json.load(f)
    
# 正确的格式应该是：
# workflow = {"节点ID": {"inputs": {...}, "class_type": "..."}, ...}

# 检查是否是 API 格式
if "nodes" in workflow:
    print("❌ 错误：这是 UI 格式，请重新导出为 API 格式！")
else:
    print("✅ 正确：这是 API 格式")
```

---

## API 开发流程

### 步骤 1: 创建 API 文件

在 `core/api/specialized/` 创建新文件，例如 `my_workflow.py`：

```python
"""
我的工作流 API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from core.comfyui_client import ComfyUIClient
from core.models import TaskResponse
from core.managers import TaskManager, ConnectionManager
from core.response import R, ResponseModel
from pathlib import Path
from typing import Optional
import json
import logging
import random
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["我的工作流"])


def setup_my_workflow_routes(
  comfyui_server: str,
  task_manager: TaskManager,
  connection_manager: ConnectionManager,
  workflow_dir: Path,
  protocol: str = "http",
  ws_protocol: str = "ws"
):
  """设置路由"""
  
  async def wait_for_completion(prompt_id: str, timeout: int):
    """等待任务完成（后台任务）"""
    from datetime import datetime
    
    try:
      # 更新状态为执行中
      task_manager.update_task(prompt_id, {"status": "running"})
      
      # 广播状态更新
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "running"
      }))
      
      logger.info(f"开始等待任务完成: {prompt_id}")
      
      # 等待任务完成
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        result = await client.async_wait_for_completion(prompt_id, timeout)
        outputs = client.extract_outputs(result)
        
        final_result = {
          "prompt_id": prompt_id,
          "status": "completed",
          "outputs": outputs,
          "raw_result": result
        }
      
      # 更新任务结果
      task_manager.update_task(prompt_id, {
        "status": "completed",
        "result": final_result,
        "completed_at": datetime.now().isoformat()
      })
      
      # 广播完成消息
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "completed",
        "result": final_result
      }))
      
    except Exception as e:
      logger.error(f"执行任务 {prompt_id} 失败: {e}")
      error_msg = str(e)
      task_manager.update_task(prompt_id, {
        "status": "failed",
        "error": error_msg
      })
      
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "failed",
        "error": error_msg
      }))

  @router.post("/my-workflow/generate", response_model=ResponseModel[TaskResponse])
  async def generate(
    background_tasks: BackgroundTasks,
    # 你的参数...
  ):
    """生成接口"""
    try:
      # 1. 参数验证和处理
      # 2. 文件上传（如果需要）
      # 3. 加载和修改工作流
      # 4. 提交到 ComfyUI
      # 5. 创建任务记录
      # 6. 返回响应
      pass
    except Exception as e:
      logger.error(f"生成失败: {e}")
      raise HTTPException(status_code=500, detail=str(e))
  
  # ⚠️ 重要：必须返回 router！
  return router
```

### 步骤 2: 修改工作流参数

**错误方式 ❌** (针对 nodes 数组，UI 格式):
```python
for node in workflow.get("nodes", []):
  if node.get("id") == 203:
    node["widgets_values"][0] = "new_image.png"
```

**正确方式 ✅** (针对 API 格式):
```python
# 修改节点 203 的 image 参数
if "203" in workflow and "inputs" in workflow["203"]:
  workflow["203"]["inputs"]["image"] = "new_image.png"

# 修改节点 135 的多个参数
if "135" in workflow and "inputs" in workflow["135"]:
  workflow["135"]["inputs"]["positive_prompt"] = "your prompt"
  workflow["135"]["inputs"]["negative_prompt"] = "your negative"

# 修改节点 204 的数值参数
if "204" in workflow and "inputs" in workflow["204"]:
  workflow["204"]["inputs"]["steps"] = 20
  workflow["204"]["inputs"]["cfg"] = 7.5
  workflow["204"]["inputs"]["seed"] = 12345
```

### 步骤 3: 文件上传

#### 上传图片
```python
# 读取图片数据
image_data = await image_file.read()
image_filename = f"my_image_{seed}.png"

# 上传到 ComfyUI
async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
  upload_result = await client.async_upload_image(
    image_data=image_data,
    filename=image_filename,
    overwrite=True
  )
  uploaded_filename = upload_result.get('name', image_filename)
```

#### 上传音频（使用自定义方法）
```python
import aiohttp

# 读取音频数据
audio_data = await audio_file.read()
audio_ext = Path(audio_file.filename).suffix or '.mp3'
audio_filename = f"my_audio_{seed}{audio_ext}"

async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
  session = client._get_session()
  form = aiohttp.FormData()
  
  # 设置正确的 content_type
  content_type_map = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.m4a': 'audio/mp4'
  }
  content_type = content_type_map.get(audio_ext.lower(), 'audio/mpeg')
  
  form.add_field('image', audio_data, filename=audio_filename, content_type=content_type)
  form.add_field('overwrite', 'true')
  
  async with session.post(f"{client.api_url}/upload/image", data=form) as response:
    if response.status != 200:
      raise Exception(f"上传音频失败: {await response.text()}")
    upload_result = await response.json()
    uploaded_filename = upload_result.get('name', audio_filename)
```

### 步骤 4: 提交工作流

**错误方式 ❌**:
```python
# 使用同步方法
prompt_id = await client.queue_prompt(workflow)
```

**正确方式 ✅**:
```python
# 使用异步方法并处理响应
async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
  response = await client.async_queue_prompt(workflow)

# 验证响应
if not response or 'prompt_id' not in response:
  raise HTTPException(
    status_code=500,
    detail="ComfyUI提交失败，未返回prompt_id"
  )

prompt_id = response['prompt_id']
logger.info(f"工作流已提交，prompt_id: {prompt_id}")
```

### 步骤 5: 创建任务记录

**错误方式 ❌**:
```python
task_manager.create_task(prompt_id, "my_workflow", {...})
```

**正确方式 ✅**:
```python
task_manager.add_task(prompt_id, {
  "task_id": prompt_id,
  "prompt_id": prompt_id,
  "workflow_type": "my_workflow",
  "params": {
    "param1": value1,
    "param2": value2
  }
})
```

### 步骤 6: 返回响应

**错误方式 ❌**:
```python
return R.ok(data=..., msg="成功")
```

**正确方式 ✅**:
```python
return R.success(
  data=TaskResponse(
    task_id=prompt_id,
    status="pending",
    message="任务已提交"
  ),
  message="任务提交成功"
)
```

### 步骤 7: 注册路由

#### 7.1 更新 `__init__.py`
```python
# core/api/specialized/__init__.py
from .my_workflow import router as my_workflow_router, setup_my_workflow_routes

__all__ = [
  # ... 其他
  'my_workflow_router',
  'setup_my_workflow_routes'
]
```

#### 7.2 更新 `main.py`
```python
# main.py
from core.api.specialized.my_workflow import setup_my_workflow_routes

# 设置路由
my_workflow_router = setup_my_workflow_routes(
  COMFYUI_SERVER,
  task_manager,
  connection_manager,
  WORKFLOW_DIR,
  COMFYUI_PROTOCOL,
  COMFYUI_WS_PROTOCOL
)

# 注册路由
app.include_router(my_workflow_router)
```

---

## 常见错误及解决方案

### 错误 1: AttributeError: 'NoneType' object has no attribute 'routes'

**症状**:
```
AttributeError: 'NoneType' object has no attribute 'routes'
```

**原因**: `setup_xxx_routes` 函数没有返回 `router` 对象。

**解决方案**:
```python
def setup_my_workflow_routes(...):
  # ... 定义所有路由
  
  # ⚠️ 必须在函数末尾返回 router！
  return router
```

---

### 错误 2: AttributeError: 'ComfyUIClient' object has no attribute 'upload_file'

**症状**:
```
AttributeError: 'ComfyUIClient' object has no attribute 'upload_file'
```

**原因**: `ComfyUIClient` 没有通用的 `upload_file` 方法。

**解决方案**:
- 图片使用: `await client.async_upload_image(image_data, filename)`
- 音频使用: 直接调用 `/upload/image` 端点（见步骤 3）

---

### 错误 3: HTTP Error 400: Bad Request (提交工作流失败)

**症状**:
```
urllib.error.HTTPError: HTTP Error 400: Bad Request
```

**原因**: 工作流格式错误或参数修改方式不正确。

**常见问题**:
1. 使用了 UI 格式而不是 API 格式
2. 使用 `widgets_values` 数组而不是 `inputs` 字典
3. 使用 `nodes` 数组遍历而不是节点 ID 字典

**解决方案**:
```python
# ❌ 错误：针对 UI 格式
for node in workflow.get("nodes", []):
  if node.get("id") == 203:
    node["widgets_values"][0] = "image.png"

# ✅ 正确：针对 API 格式
if "203" in workflow and "inputs" in workflow["203"]:
  workflow["203"]["inputs"]["image"] = "image.png"
```

---

### 错误 4: AttributeError: 'TaskManager' object has no attribute 'create_task'

**症状**:
```
AttributeError: 'TaskManager' object has no attribute 'create_task'
```

**原因**: 方法名称错误。

**解决方案**:
```python
# ❌ 错误
task_manager.create_task(prompt_id, "type", {...})

# ✅ 正确
task_manager.add_task(prompt_id, {
  "task_id": prompt_id,
  "workflow_type": "type",
  "params": {...}
})
```

---

### 错误 5: AttributeError: type object 'R' has no attribute 'ok'

**症状**:
```
AttributeError: type object 'R' has no attribute 'ok'
```

**原因**: 响应方法名称错误。

**解决方案**:
```python
# ❌ 错误
return R.ok(data=..., msg="...")

# ✅ 正确
return R.success(data=..., message="...")
```

---

### 错误 6: 文件未正确上传或节点无法找到文件

**症状**: ComfyUI 报告找不到输入文件。

**原因**:
1. 文件名包含特殊字符或中文
2. 文件未成功上传到 `input` 目录
3. 节点参数中的文件名不匹配

**解决方案**:
```python
from datetime import datetime
import uuid

# 生成安全的文件名
file_ext = Path(file.filename).suffix.lower()
safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"

# 或使用 seed 作为标识
safe_filename = f"workflow_input_{seed}{file_ext}"

# 上传后获取实际文件名
upload_result = await client.async_upload_image(...)
uploaded_filename = upload_result.get('name', safe_filename)

# 使用实际的上传文件名修改工作流
workflow["203"]["inputs"]["image"] = uploaded_filename
```

---

## 最佳实践

### 1. 工作流节点查找

创建辅助函数来查找和识别节点：

```python
def find_node_by_class(workflow: dict, class_type: str) -> list:
  """根据 class_type 查找节点 ID"""
  return [
    node_id for node_id, node_data in workflow.items()
    if node_data.get("class_type") == class_type
  ]

# 使用示例
load_image_nodes = find_node_by_class(workflow, "LoadImage")
if load_image_nodes:
  node_id = load_image_nodes[0]
  workflow[node_id]["inputs"]["image"] = "my_image.png"
```

### 2. 参数验证

```python
from pydantic import BaseModel, Field, validator

class MyWorkflowRequest(BaseModel):
  prompt: str = Field(..., min_length=1, max_length=1000)
  steps: int = Field(default=20, ge=1, le=100)
  width: int = Field(default=512, ge=256, le=2048)
  height: int = Field(default=512, ge=256, le=2048)
  
  @validator('width', 'height')
  def validate_dimensions(cls, v):
    if v % 8 != 0:
      raise ValueError('尺寸必须是 8 的倍数')
    return v
```

### 3. 日志记录

```python
logger.info(f"收到请求: prompt='{prompt[:50]}...', steps={steps}")
logger.info(f"文件上传成功 - 图片: {uploaded_image}")
logger.info(f"工作流参数已更新: size={width}x{height}, seed={seed}")
logger.info(f"工作流已提交，prompt_id: {prompt_id}")
```

### 4. 错误处理

```python
try:
  # 你的逻辑
  pass
except HTTPException:
  # 直接抛出 HTTP 异常
  raise
except Exception as e:
  logger.error(f"处理失败: {e}")
  logger.error(f"完整错误堆栈: {traceback.format_exc()}")
  raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")
```

### 5. 工作流验证

在开发过程中验证工作流格式：

```python
def validate_workflow(workflow: dict) -> bool:
  """验证工作流格式"""
  if not isinstance(workflow, dict):
    logger.error("工作流必须是字典")
    return False
  
  if "nodes" in workflow:
    logger.error("检测到 UI 格式，请使用 API 格式")
    return False
  
  # 检查必需的节点
  required_nodes = ["203", "204", "135"]  # 根据实际情况调整
  for node_id in required_nodes:
    if node_id not in workflow:
      logger.error(f"缺少必需节点: {node_id}")
      return False
    if "inputs" not in workflow[node_id]:
      logger.error(f"节点 {node_id} 缺少 inputs")
      return False
  
  return True

# 使用
if not validate_workflow(workflow):
  raise HTTPException(status_code=500, detail="工作流格式错误")
```

---

## 完整示例

基于真实的 InfiniteTalk I2V API 实现：

### 文件结构
```
core/api/specialized/
├── infinitetalk_i2v.py          # API 实现
├── __init__.py                   # 导出配置

workflows/
├── infinitetalkI2V.json         # API 格式工作流

static/specialized/
├── infinitetalk_i2v.html        # 测试页面
├── infinitetalk_i2v.js          # 前端逻辑
```

### 核心代码片段

```python
# core/api/specialized/infinitetalk_i2v.py

@router.post("/infinitetalk-i2v/generate", response_model=ResponseModel[TaskResponse])
async def generate_video_from_audio(
  background_tasks: BackgroundTasks,
  image: UploadFile = File(...),
  audio: UploadFile = File(...),
  prompt: str = Form("A person speaking"),
  width: int = Form(720),
  height: int = Form(480),
  steps: int = Form(4),
  seed: Optional[int] = Form(None)
):
  try:
    # 1. 验证文件
    if not image.content_type.startswith('image/'):
      raise HTTPException(status_code=400, detail="必须上传图片文件")
    
    # 2. 处理图片
    image_data = await image.read()
    img = Image.open(io.BytesIO(image_data))
    img = resize_image_to_target(img, width, height)
    
    # 3. 保存临时文件并上传
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
      img.save(tmp.name, 'PNG')
      temp_image_path = tmp.name
    
    if seed is None:
      seed = random.randint(0, 2**32 - 1)
    
    # 4. 上传文件到 ComfyUI
    with open(temp_image_path, 'rb') as f:
      image_data = f.read()
    
    async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
      upload_result = await client.async_upload_image(
        image_data=image_data,
        filename=f"infinitetalk_input_{seed}.png",
        overwrite=True
      )
      uploaded_image = upload_result.get('name')
    
    # 5. 加载工作流
    workflow_file = workflow_dir / "infinitetalkI2V.json"
    with open(workflow_file, "r", encoding="utf-8") as f:
      workflow = json.load(f)
    
    # 6. 修改工作流参数
    if "203" in workflow:
      workflow["203"]["inputs"]["image"] = uploaded_image
    
    if "204" in workflow:
      workflow["204"]["inputs"]["steps"] = steps
      workflow["204"]["inputs"]["seed"] = seed
    
    if "135" in workflow:
      workflow["135"]["inputs"]["positive_prompt"] = prompt
    
    # 7. 提交工作流
    async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
      response = await client.async_queue_prompt(workflow)
    
    if not response or 'prompt_id' not in response:
      raise HTTPException(status_code=500, detail="提交失败")
    
    prompt_id = response['prompt_id']
    
    # 8. 创建任务记录
    task_manager.add_task(prompt_id, {
      "task_id": prompt_id,
      "workflow_type": "infinitetalk_i2v",
      "params": {"image": uploaded_image, "prompt": prompt}
    })
    
    # 9. 后台等待完成
    background_tasks.add_task(wait_for_completion, prompt_id, 600)
    
    # 10. 返回响应
    return R.success(
      data=TaskResponse(
        task_id=prompt_id,
        status="pending",
        message="任务已提交"
      ),
      message="任务提交成功"
    )
    
  except Exception as e:
    logger.error(f"生成失败: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

---

## 测试清单

在完成开发后，使用以下清单进行测试：

- [ ] 工作流文件是 API 格式（不是 UI 格式）
- [ ] 文件上传成功（检查 ComfyUI 的 input 目录）
- [ ] 工作流参数正确修改（打印 workflow JSON 验证）
- [ ] 提交到 ComfyUI 成功（获得 prompt_id）
- [ ] 任务记录创建成功（可以查询状态）
- [ ] 后台任务正常运行（检查日志）
- [ ] 结果正确返回（查看输出文件）
- [ ] 错误处理正常（测试各种异常情况）

---

## 调试技巧

### 1. 打印工作流 JSON

```python
logger.debug(f"修改后的工作流: {json.dumps(workflow, indent=2, ensure_ascii=False)}")
```

### 2. 验证文件上传

```python
logger.info(f"上传结果: {upload_result}")
logger.info(f"实际文件名: {uploaded_filename}")

# 检查 ComfyUI input 目录
# Windows: ComfyUI\input\
# Linux: ~/ComfyUI/input/
```

### 3. 检查 ComfyUI 日志

查看 ComfyUI 控制台输出，了解详细错误信息。

### 4. 使用 Postman 测试

参考 `docs/POSTMAN_GUIDE.md` 进行接口测试。

---

## 相关文档

- [API 使用指南](API_USAGE.md)
- [项目结构说明](PROJECT_STRUCTURE.md)
- [Postman 测试指南](POSTMAN_GUIDE.md)
- [Wan2.2 I2V API 文档](WAN22_I2V_API.md)

---

## 常见问题 (FAQ)

### Q: 如何知道工作流中有哪些节点？

A: 在文本编辑器中打开 JSON 文件，顶层的键就是节点 ID。例如：
```json
{
  "120": {...},  // 节点 120
  "203": {...},  // 节点 203
  "204": {...}   // 节点 204
}
```

### Q: 如何确定节点的参数名称？

A: 查看节点的 `inputs` 字段：
```json
"203": {
  "inputs": {
    "image": "xxx.png"  // 参数名是 "image"
  }
}
```

### Q: 音频文件为什么也通过 /upload/image 端点上传？

A: ComfyUI 的 `/upload/image` 端点实际上可以上传任意文件到 `input` 目录，不仅限于图片。只需设置正确的 `content_type` 即可。

### Q: 如何处理超大文件上传？

A: 
1. 增加 FastAPI 的文件大小限制
2. 使用流式上传
3. 考虑先上传到临时存储，再转移到 ComfyUI

### Q: 如何支持批量处理？

A: 可以在一个端点中循环提交多个工作流，或者创建批量专用端点。注意控制并发数量。

---

**最后更新**: 2025-11-12  
**维护者**: ComfyAPI Team

**相关案例**: InfiniteTalk I2V API 实现参考 `core/api/specialized/infinitetalk_i2v.py`

