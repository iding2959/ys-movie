# ComfyUI API 示例代码

本目录包含各种API使用示例，帮助你快速上手。

## 📁 文件说明

- `basic_usage.py` - 基础用法，演示简单的图片生成
- `batch_generate.py` - 批量生成，同时提交多个任务
- `advanced_usage.py` - 高级用法，使用WorkflowBuilder类

## 🚀 运行前准备

### 1. 安装依赖

```bash
pip install requests
```

### 2. 启动API服务

```bash
# 在项目根目录运行
python start.py
```

确保服务运行在 `http://localhost:8000`

### 3. 确保ComfyUI服务运行

确保你的ComfyUI服务正常运行（默认 `192.168.48.123:8188`）

## 📖 使用说明

### basic_usage.py - 基础用法

最简单的使用方式，适合快速测试：

```bash
cd examples
python basic_usage.py
```

**功能：**
- 简单生成一张图片
- 使用固定种子生成（可重现）
- 高质量生成（更多步数）

**示例代码：**
```python
from basic_usage import generate_image

# 生成一张图片
result = generate_image(
    prompt="A beautiful sunset over the ocean",
    negative_prompt="blurry, low quality",
    seed=-1,  # 随机种子
    steps=20,
    width=1024,
    height=1024
)
```

### batch_generate.py - 批量生成

批量提交多个任务并监控执行：

```bash
cd examples
python batch_generate.py
```

**功能：**
- 批量提交多个提示词
- 自动监控所有任务状态
- 显示完成进度和结果

**示例代码：**
```python
from batch_generate import batch_generate, monitor_tasks

# 定义提示词列表
prompts = [
    "A serene mountain landscape",
    "A bustling city at night",
    "A colorful garden"
]

# 批量提交
tasks = batch_generate(
    prompts,
    seed=-1,
    steps=15,
    width=1024,
    height=1024
)

# 监控执行
results = monitor_tasks(tasks)
```

### advanced_usage.py - 高级用法

使用WorkflowBuilder类进行更灵活的工作流构建：

```bash
cd examples
python advanced_usage.py
```

**功能：**
- 链式调用API构建工作流
- 测试不同参数组合
- 直接修改特定节点参数
- 对比实验（固定种子）

**示例代码：**
```python
from advanced_usage import WorkflowBuilder

# 使用链式调用
workflow = (WorkflowBuilder('workflows/qwen_t2i_distill.json')
    .set_prompt(
        positive="beautiful landscape",
        negative="low quality"
    )
    .set_sampler(seed=-1, steps=30, cfg=1.5)
    .set_size(1024, 1024)
    .set_filename_prefix("my_image")
    .build())

# 或者直接提交
task = (WorkflowBuilder('workflows/qwen_t2i_distill.json')
    .set_prompt("beautiful sunset", "blurry")
    .set_sampler(seed=-1, steps=20)
    .submit())
```

## 🎯 常见使用场景

### 场景1：快速测试单张图片

```python
from basic_usage import generate_image

result = generate_image(
    prompt="your prompt here",
    steps=10,  # 快速测试用较少步数
    width=512,
    height=512
)
```

### 场景2：批量生成不同主题

```python
from batch_generate import batch_generate

prompts = [
    "landscape photo",
    "portrait photo",
    "abstract art"
]

tasks = batch_generate(prompts, steps=20)
```

### 场景3：参数对比实验

```python
from advanced_usage import WorkflowBuilder

seed = 123456789  # 固定种子

# 测试不同步数
for steps in [10, 20, 30, 50]:
    (WorkflowBuilder('workflows/qwen_t2i_distill.json')
        .set_prompt("test prompt", "")
        .set_sampler(seed=seed, steps=steps)
        .set_filename_prefix(f"test_steps_{steps}")
        .submit())
```

### 场景4：自定义输出文件名

```python
from advanced_usage import WorkflowBuilder
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

(WorkflowBuilder('workflows/qwen_t2i_distill.json')
    .set_prompt("your prompt", "")
    .set_filename_prefix(f"output_{timestamp}")
    .submit())
```

## 🛠️ 自定义修改

### 修改默认API地址

在每个文件开头修改：

```python
API_BASE = 'http://your-server:port'
```

### 使用不同的工作流模板

```python
# 使用HiDream模型
workflow = WorkflowBuilder('workflows/HiDream-l1.json')

# 或自定义路径
workflow = WorkflowBuilder('/path/to/your/workflow.json')
```

### 添加自定义参数

修改 `WorkflowBuilder` 类，添加新方法：

```python
class WorkflowBuilder:
    def set_custom_param(self, node_id, param_name, value):
        """设置自定义参数"""
        if node_id in self.workflow:
            self.workflow[node_id]['inputs'][param_name] = value
        return self
```

## 📚 更多资源

- [API完整文档](../API_USAGE.md) - 详细的API使用说明
- [在线API文档](http://localhost:8000/docs) - FastAPI自动生成的交互式文档
- [调试界面](http://localhost:8000) - 可视化调试工具

## ❓ 常见问题

### Q: 运行示例时报错 "Connection refused"

A: 确保API服务已启动（`python start.py`）

### Q: 任务一直处于pending状态

A: 检查ComfyUI服务是否正常运行，可以访问 http://192.168.48.123:8188 确认

### Q: 如何加快生成速度？

A: 
- 减少 `steps` 参数
- 降低图像分辨率
- 使用更快的采样器

### Q: 如何获取生成的图片？

A: 
1. 任务完成后，结果中包含图片URL
2. 通过浏览器访问URL直接查看/下载
3. 或使用 `requests.get()` 下载

示例：
```python
import requests

# 假设result['outputs'][0]['url'] = '/api/image/xxx.png?type=output'
image_url = API_BASE + result['outputs'][0]['url']
response = requests.get(image_url)

with open('output.png', 'wb') as f:
    f.write(response.content)
```

## 💡 提示

- 使用 `seed=-1` 每次生成随机结果
- 固定 `seed` 可以重现相同的图片
- 增加 `steps` 可提高质量但会变慢
- 详细的负面提示词可以显著提高图片质量

