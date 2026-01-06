# ComfyUI API 使用文档

本文档详细说明如何通过API调用ComfyUI工作流，包括参数修改和自定义。

## 📋 目录

- [快速开始](#快速开始)
- [API端点说明](#api端点说明)
- [工作流结构](#工作流结构)
- [修改参数](#修改参数)
- [Python示例](#python示例)
- [curl示例](#curl示例)
- [常见场景](#常见场景)

---

## 🚀 快速开始

### 1. 启动服务

```bash
python start.py
```

服务默认运行在 `http://localhost:8000`

### 2. 准备工作流文件

工作流文件位于 `workflows/` 目录：
- `qwen_t2i_distill.json` - Qwen文生图模型
- `HiDream-l1.json` - HiDream文生图模型

### 3. 调用API提交任务

```bash
curl -X POST http://localhost:8000/api/workflow/submit \
  -H "Content-Type: application/json" \
  -d @workflows/qwen_t2i_distill.json
```

---

## 📡 API端点说明

### 提交工作流

**POST** `/api/workflow/submit`

提交一个工作流任务到ComfyUI执行。

**⚠️ 重要：请求体格式**

API期望以下格式的JSON：
```json
{
  "workflow": { 工作流JSON对象 },
  "params": {},      // 可选：动态参数
  "timeout": 600     // 可选：超时时间（秒），默认600
}
```

**请求体示例：**
```json
{
  "workflow": {
    "3": { "class_type": "KSampler", ... },
    "6": { "class_type": "CLIPTextEncode", ... }
  },
  "params": {},
  "timeout": 600
}
```

**响应示例：**
```json
{
  "task_id": "ca5bbc73-b893-4944-9a58-ecb75855e4e2",
  "status": "queued",
  "message": "任务已提交"
}
```

### 查询任务状态

**GET** `/api/task/{task_id}`

查询指定任务的执行状态和结果。

⚠️ 注意：路径是 `/api/task/` （单数），不是 `/api/tasks/`

**响应示例：**
```json
{
  "task_id": "ca5bbc73-b893-4944-9a58-ecb75855e4e2",
  "status": "completed",
  "created_at": "2025-10-16T15:30:00",
  "outputs": [
    {
      "type": "image",
      "url": "/api/image/image_001.png?type=output"
    }
  ]
}
```

### 查询所有任务

**GET** `/api/tasks`

获取所有任务列表。

### 查询队列状态

**GET** `/api/queue`

查询ComfyUI当前的任务队列状态。

---

## 🔧 工作流结构

ComfyUI工作流是一个JSON对象，每个节点由节点ID作为key：

```json
{
  "节点ID": {
    "class_type": "节点类型",
    "inputs": {
      "参数名": "参数值",
      "连接输入": ["源节点ID", 输出索引]
    }
  }
}
```

### 常见节点类型

#### 1. KSampler（采样器）

控制图像生成的核心参数：

```json
{
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "seed": 11686055649067,        // 随机种子，使用-1自动随机
      "steps": 10,                    // 采样步数，越高质量越好但越慢
      "cfg": 1,                       // CFG引导强度
      "sampler_name": "dpmpp_sde_gpu", // 采样器名称
      "scheduler": "simple",          // 调度器
      "denoise": 1,                   // 降噪强度 (0-1)
      "model": ["66", 0],             // 模型连接
      "positive": ["6", 0],           // 正面提示词连接
      "negative": ["7", 0],           // 负面提示词连接
      "latent_image": ["72", 0]       // 潜空间图像连接
    }
  }
}
```

#### 2. CLIPTextEncode（文本编码器）

用于输入提示词：

```json
{
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "您的提示词内容",
      "clip": ["38", 0]
    }
  }
}
```

#### 3. EmptySD3LatentImage（空白潜空间图像）

设置图像尺寸：

```json
{
  "72": {
    "class_type": "EmptySD3LatentImage",
    "inputs": {
      "width": 1328,        // 图像宽度
      "height": 1328,       // 图像高度
      "batch_size": 1       // 批量大小
    }
  }
}
```

#### 4. SaveImage（保存图像）

保存生成的图像：

```json
{
  "60": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "ComfyUI",  // 文件名前缀
      "images": ["8", 0]              // 图像输入连接
    }
  }
}
```

---

## ✏️ 修改参数

### 方法1：直接修改JSON文件

1. 复制工作流文件
2. 修改需要的参数
3. 提交修改后的JSON

```bash
# 复制模板
cp workflows/qwen_t2i_distill.json my_workflow.json

# 编辑参数（使用你喜欢的编辑器）
vim my_workflow.json

# 提交
curl -X POST http://localhost:8000/api/workflow/submit \
  -H "Content-Type: application/json" \
  -d @my_workflow.json
```

### 方法2：编程方式修改

在代码中读取、修改、提交：

```python
import json
import requests

# 读取工作流模板
with open('workflows/qwen_t2i_distill.json', 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# 修改参数
workflow['3']['inputs']['seed'] = -1  # 随机种子
workflow['3']['inputs']['steps'] = 20  # 采样步数
workflow['6']['inputs']['text'] = '你的正面提示词'  # 正面提示词
workflow['7']['inputs']['text'] = '你的负面提示词'  # 负面提示词
workflow['72']['inputs']['width'] = 1024  # 宽度
workflow['72']['inputs']['height'] = 1024  # 高度

# 提交任务
response = requests.post(
    'http://localhost:8000/api/workflow/submit',
    json=workflow
)

task = response.json()
print(f"任务ID: {task['task_id']}")
```

---

## 🐍 Python示例

### 完整示例：文生图工作流

```python
import json
import requests
import time

API_BASE = 'http://localhost:8000'

def submit_workflow(workflow_data):
    """提交工作流"""
    # 包装为API期望的格式
    payload = {
        "workflow": workflow_data,
        "params": {},
        "timeout": 600
    }
    response = requests.post(f'{API_BASE}/api/workflow/submit', json=payload)
    response.raise_for_status()
    return response.json()

def get_task_status(task_id):
    """查询任务状态"""
    response = requests.get(f'{API_BASE}/api/task/{task_id}')  # 注意：task单数
    response.raise_for_status()
    return response.json()

def wait_for_completion(task_id, timeout=300):
    """等待任务完成"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        task = get_task_status(task_id)
        
        if task['status'] == 'completed':
            print(f"✅ 任务完成！")
            return task
        elif task['status'] == 'failed':
            print(f"❌ 任务失败: {task.get('error', '未知错误')}")
            return task
        
        print(f"⏳ 任务状态: {task['status']}")
        time.sleep(2)
    
    print(f"⚠️ 任务超时")
    return None

# 示例1：使用qwen_t2i_distill工作流生成图片
def generate_image(prompt, negative_prompt="", seed=-1, steps=10, width=1024, height=1024):
    """生成图片"""
    
    # 读取工作流模板
    with open('workflows/qwen_t2i_distill.json', 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    # 修改参数
    workflow['3']['inputs']['seed'] = seed
    workflow['3']['inputs']['steps'] = steps
    workflow['6']['inputs']['text'] = prompt
    workflow['7']['inputs']['text'] = negative_prompt
    workflow['72']['inputs']['width'] = width
    workflow['72']['inputs']['height'] = height
    
    # 提交任务
    print(f"🚀 提交任务...")
    task = submit_workflow(workflow)
    task_id = task['task_id']
    print(f"📋 任务ID: {task_id}")
    
    # 等待完成
    result = wait_for_completion(task_id)
    
    if result and result['status'] == 'completed':
        # 下载图片
        if result.get('outputs'):
            for i, output in enumerate(result['outputs']):
                if output['type'] == 'image':
                    print(f"🖼️  图片URL: {API_BASE}{output['url']}")
    
    return result

# 使用示例
if __name__ == '__main__':
    result = generate_image(
        prompt="A beautiful sunset over the ocean, vibrant colors, peaceful scene",
        negative_prompt="blurry, low quality, distorted",
        seed=-1,  # 随机种子
        steps=20,
        width=1024,
        height=1024
    )
```

### 示例2：批量生成图片

```python
def batch_generate(prompts, base_workflow='workflows/qwen_t2i_distill.json'):
    """批量生成图片"""
    
    with open(base_workflow, 'r', encoding='utf-8') as f:
        workflow_template = json.load(f)
    
    tasks = []
    
    for i, prompt in enumerate(prompts):
        workflow = json.loads(json.dumps(workflow_template))  # 深拷贝
        
        # 修改参数
        workflow['3']['inputs']['seed'] = -1  # 每次随机
        workflow['6']['inputs']['text'] = prompt
        workflow['60']['inputs']['filename_prefix'] = f'batch_{i:03d}'
        
        # 提交
        print(f"提交任务 {i+1}/{len(prompts)}: {prompt[:50]}...")
        task = submit_workflow(workflow)
        tasks.append({
            'task_id': task['task_id'],
            'prompt': prompt
        })
    
    print(f"\n✅ 已提交 {len(tasks)} 个任务")
    return tasks

# 使用示例
prompts = [
    "A serene mountain landscape at dawn",
    "A bustling city street at night",
    "A colorful garden full of flowers",
    "A futuristic spaceship in orbit"
]

tasks = batch_generate(prompts)
```

---

## 💻 curl示例

### 提交任务

```bash
curl -X POST http://localhost:8000/api/workflow/submit \
  -H "Content-Type: application/json" \
  -d '{
    "3": {
      "class_type": "KSampler",
      "inputs": {
        "seed": -1,
        "steps": 20,
        "cfg": 1,
        "sampler_name": "dpmpp_sde_gpu",
        "scheduler": "simple",
        "denoise": 1,
        "model": ["66", 0],
        "positive": ["6", 0],
        "negative": ["7", 0],
        "latent_image": ["72", 0]
      }
    },
    "6": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": "A beautiful landscape",
        "clip": ["38", 0]
      }
    },
    ...
  }'
```

### 查询任务状态

```bash
curl http://localhost:8000/api/tasks/ca5bbc73-b893-4944-9a58-ecb75855e4e2
```

### 查询所有任务

```bash
curl http://localhost:8000/api/tasks
```

### 查询队列

```bash
curl http://localhost:8000/api/queue
```

---

## 🎯 常见场景

### 场景1：快速测试不同提示词

```python
prompts = [
    "photo of a cat",
    "photo of a dog",
    "photo of a bird"
]

for prompt in prompts:
    result = generate_image(prompt, seed=-1, steps=10)
```

### 场景2：测试不同采样步数

```python
for steps in [10, 20, 30, 50]:
    result = generate_image(
        prompt="beautiful landscape",
        steps=steps,
        seed=12345  # 固定种子以便对比
    )
```

### 场景3：测试不同分辨率

```python
resolutions = [
    (512, 512),
    (768, 768),
    (1024, 1024),
    (1328, 1328)
]

for width, height in resolutions:
    result = generate_image(
        prompt="portrait photo",
        width=width,
        height=height
    )
```

### 场景4：使用相同种子生成一致的图片

```python
# 生成一张图片并记录种子
seed = 123456789
result1 = generate_image("a red apple", seed=seed)

# 使用相同种子生成相同的图片
result2 = generate_image("a red apple", seed=seed)

# result1 和 result2 应该生成完全相同的图片
```

### 场景5：修改负面提示词改善质量

```python
negative_prompts = [
    "blurry, low quality",
    "blurry, low quality, distorted, ugly",
    "blurry, low quality, distorted, ugly, bad anatomy, worst quality"
]

for neg_prompt in negative_prompts:
    result = generate_image(
        prompt="beautiful portrait",
        negative_prompt=neg_prompt,
        seed=12345  # 固定种子以便对比
    )
```

---

## 🛠️ 高级用法

### 自定义工作流参数提取

如果你需要频繁修改特定参数，可以创建辅助函数：

```python
class WorkflowBuilder:
    def __init__(self, template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            self.workflow = json.load(f)
    
    def set_prompt(self, positive, negative=""):
        """设置提示词"""
        # 找到CLIPTextEncode节点
        for node_id, node in self.workflow.items():
            if node['class_type'] == 'CLIPTextEncode':
                if 'positive' in node.get('_meta', {}).get('title', '').lower():
                    node['inputs']['text'] = positive
                elif 'negative' in node.get('_meta', {}).get('title', '').lower():
                    node['inputs']['text'] = negative
        return self
    
    def set_sampler(self, seed=-1, steps=20, cfg=1):
        """设置采样器参数"""
        for node_id, node in self.workflow.items():
            if node['class_type'] == 'KSampler':
                node['inputs']['seed'] = seed
                node['inputs']['steps'] = steps
                node['inputs']['cfg'] = cfg
        return self
    
    def set_size(self, width, height):
        """设置图像尺寸"""
        for node_id, node in self.workflow.items():
            if node['class_type'] in ['EmptySD3LatentImage', 'EmptyLatentImage']:
                node['inputs']['width'] = width
                node['inputs']['height'] = height
        return self
    
    def build(self):
        """构建最终工作流"""
        return self.workflow

# 使用示例
workflow = (WorkflowBuilder('workflows/qwen_t2i_distill.json')
    .set_prompt(
        positive="beautiful sunset",
        negative="blurry, low quality"
    )
    .set_sampler(seed=-1, steps=30, cfg=1.5)
    .set_size(1024, 1024)
    .build())

result = submit_workflow(workflow)
```

---

## 📚 参考资料

- [ComfyUI官方文档](https://github.com/comfyanonymous/ComfyUI)
- [API接口文档](http://localhost:8000/docs) - 启动服务后访问
- [调试界面](http://localhost:8000) - 可视化调试工具

---

## ❓ 常见问题

### Q: 如何知道我的工作流中有哪些可修改的参数？

A: 可以通过以下方式：
1. 使用调试界面上传工作流，会自动识别可编辑参数
2. 查看JSON文件，所有 `"inputs"` 中的值类型参数都可以修改
3. 连接类型的参数（数组格式 `["节点ID", 输出索引]`）通常不需要修改

### Q: seed设为-1就能每次随机吗？

A: 是的，seed设为-1或任何负数时，系统会自动生成随机种子。

### Q: 如何加快生成速度？

A: 可以通过以下方式：
- 减少 `steps` 参数（但会影响质量）
- 降低图像分辨率
- 使用更快的采样器（如 `euler_a`）

### Q: 提交任务后如何获取生成的图片？

A: 
1. 通过 `/api/tasks/{task_id}` 查询任务状态
2. 任务完成后，响应中的 `outputs` 包含图片URL
3. 通过URL直接下载图片

---

## 💡 提示

- 使用 `seed=-1` 可以每次生成不同的图片
- 增加 `steps` 可以提高质量，但会增加生成时间
- 调整 `cfg` 值可以控制对提示词的遵循程度
- 负面提示词对图片质量影响很大，建议详细描述不想要的元素

