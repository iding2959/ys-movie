# Wan2.2 图生视频 API 文档

## 概述

Wan2.2图生视频API (`/api/wan22_i2v`) 提供了强大的图像到视频生成功能，支持根据指定时长自动拼接多个5秒视频片段。

## 核心特性

- ✅ **智能时长控制**: 支持5-30秒视频生成，以5秒为单位自动拼接
- ✅ **自动节点管理**: 根据时长自动生成和连接workflow节点
- ✅ **图片上传**: 一键上传起始图片并生成视频
- ✅ **参数可调**: 分辨率、帧率、采样步数等完全可控
- ✅ **颜色匹配**: 自动保持视频片段间的颜色一致性

## API端点

### 1. 上传图片并生成视频 (推荐)

**端点**: `POST /api/wan22_i2v/upload_and_generate`

**请求格式**: `multipart/form-data`

**参数**:
```
image: file (必需) - 起始图片文件
prompt: string (必需) - 视频描述提示词
negative_prompt: string (可选) - 负面提示词，默认为空
duration: int (可选) - 视频时长（秒），5-30，必须是5的倍数，默认5
width: int (可选) - 视频宽度，默认480
height: int (可选) - 视频高度，默认832
frame_rate: int (可选) - 帧率，默认16
steps: int (可选) - 采样步数，默认4
seed: int (可选) - 随机种子，-1为随机，默认-1
```

**使用示例 (curl)**:
```bash
curl -X POST "http://localhost:8000/api/wan22_i2v/upload_and_generate" \
  -F "image=@/path/to/your/image.png" \
  -F "prompt=A beautiful girl walking in the garden" \
  -F "duration=10" \
  -F "width=480" \
  -F "height=832" \
  -F "frame_rate=16" \
  -F "steps=4" \
  -F "seed=-1"
```

**使用示例 (Python)**:
```python
import requests

url = "http://localhost:8000/api/wan22_i2v/upload_and_generate"

with open("image.png", "rb") as f:
    files = {"image": f}
    data = {
        "prompt": "A beautiful girl walking in the garden",
        "negative_prompt": "",
        "duration": 10,  # 10秒 = 2个5秒片段
        "width": 480,
        "height": 832,
        "frame_rate": 16,
        "steps": 4,
        "seed": -1
    }
    
    response = requests.post(url, files=files, data=data)
    result = response.json()
    
    print(f"任务ID: {result['data']['task_id']}")
    print(f"视频时长: {result['data']['duration']}秒")
    print(f"片段数: {result['data']['segments']}")
```

**响应示例**:
```json
{
  "code": 200,
  "message": "视频生成任务已提交（10秒）",
  "data": {
    "task_id": "abc123-def456",
    "status": "submitted",
    "duration": 10,
    "segments": 2,
    "image": "uploaded_image.png"
  },
  "timestamp": "2025-01-01T12:00:00"
}
```

### 2. 使用已上传图片生成视频

**端点**: `POST /api/wan22_i2v/generate`

**请求格式**: `application/json`

**请求体**:
```json
{
  "image_filename": "image.png",
  "prompt": "A beautiful girl walking in the garden",
  "negative_prompt": "",
  "duration": 15,
  "width": 480,
  "height": 832,
  "frame_rate": 16,
  "steps": 4,
  "seed": -1
}
```

**使用示例 (Python)**:
```python
import requests

url = "http://localhost:8000/api/wan22_i2v/generate"

data = {
    "image_filename": "image.png",  # 必须是已上传到input文件夹的图片
    "prompt": "A beautiful girl walking in the garden",
    "negative_prompt": "",
    "duration": 15,  # 15秒 = 3个5秒片段
    "width": 480,
    "height": 832,
    "frame_rate": 16,
    "steps": 4,
    "seed": 123456789
}

response = requests.post(url, json=data)
result = response.json()

print(f"任务ID: {result['data']['task_id']}")
print(f"视频时长: {result['data']['duration']}秒")
```

## 时长与片段关系

系统会根据指定的时长自动计算需要生成的5秒片段数量：

| 时长（秒） | 片段数 | 说明 |
|-----------|--------|------|
| 5 | 1 | 单个片段，无需拼接 |
| 10 | 2 | 2个片段拼接 |
| 15 | 3 | 3个片段拼接 |
| 20 | 4 | 4个片段拼接 |
| 25 | 5 | 5个片段拼接 |
| 30 | 6 | 6个片段拼接 |

## 工作原理

### 单片段生成 (5秒)
```
起始图片 → VAE编码 → 视频生成 → VAE解码 → 输出视频
```

### 多片段拼接 (10秒以上)
```
片段1: 起始图片 → 生成5秒 → 提取末尾10帧
                    ↓
片段2: 末尾10帧 → 生成5秒 → 提取末尾10帧
                    ↓
片段3: 末尾10帧 → 生成5秒 → ...
                    ↓
                 拼接所有片段
                    ↓
                颜色匹配 → 输出视频
```

## 技术细节

### 自动种子生成
每个片段会自动生成独立的种子值以确保视觉多样性：
```python
segment_seeds = [base_seed + i * 1000000 for i in range(num_segments)]
```

### 节点ID规划
- 基础节点: 固定ID (16, 26, 32, 44, 57, 58, 120等)
- 第1个片段: 70:xx 系列节点
- 第2个片段: 76:xx 系列节点
- 第3个片段: 82:xx 系列节点
- 依此类推，每个片段增加6

### 帧重叠策略
- 每个片段生成81帧 (约5秒 @ 16fps)
- 提取最后10帧作为下一片段的起始帧
- 实际有效帧数: 第1片段81帧 + 其他片段各71帧

## 查询任务状态

使用通用任务API查询生成状态：

```bash
GET /api/task/{task_id}
```

```python
import requests
import time

task_id = "abc123-def456"
url = f"http://localhost:8000/api/task/{task_id}"

while True:
    response = requests.get(url)
    result = response.json()
    
    status = result['data']['status']
    print(f"状态: {status}")
    
    if status == "completed":
        outputs = result['data']['result']['outputs']
        videos = outputs.get('images', [])  # 视频在images数组中
        for video in videos:
            video_url = f"/api/video/{video['filename']}"
            print(f"视频地址: {video_url}")
        break
    elif status == "failed":
        print(f"生成失败: {result['data'].get('error')}")
        break
    
    time.sleep(2)
```

## 最佳实践

### 1. 推荐参数组合

**快速生成** (质量一般):
```json
{
  "steps": 4,
  "frame_rate": 12,
  "duration": 5
}
```

**平衡模式** (推荐):
```json
{
  "steps": 6,
  "frame_rate": 16,
  "duration": 10
}
```

**高质量** (耗时较长):
```json
{
  "steps": 8,
  "frame_rate": 24,
  "duration": 15
}
```

### 2. 提示词建议

✅ **好的提示词**:
```
"A young woman with flowing hair walks through a sunlit garden, 
her white dress gently moving in the breeze. Camera follows smoothly, 
capturing natural movements and expressions."
```

❌ **不好的提示词**:
```
"woman, garden, walking"  # 太简单
"超级复杂的场景转换特效..."  # 超出模型能力
```

### 3. 分辨率建议

| 用途 | 分辨率 | 说明 |
|------|--------|------|
| 快速预览 | 384×640 | 生成速度快 |
| 标准输出 | 480×832 | 推荐，平衡质量和速度 |
| 高清输出 | 720×1280 | 需要更多显存和时间 |

### 4. 超时设置

系统会根据视频时长自动设置超时时间：
```python
timeout = max(600, duration * 30)  # 至少10分钟
```

## 常见问题

### Q: 为什么只支持5的倍数时长？
A: 因为每个基础片段是5秒，系统通过拼接5秒片段来实现不同时长。

### Q: 最长能生成多长的视频？
A: 当前限制是30秒（6个片段）。更长的视频建议分段生成后在后期软件中拼接。

### Q: 生成速度如何？
A: 取决于GPU性能和参数设置：
- RTX 4090: 约30-60秒/5秒片段
- RTX 3090: 约60-120秒/5秒片段

### Q: 如何保证片段间过渡自然？
A: 系统自动提取上一片段的末尾帧作为下一片段的起始帧，并应用颜色匹配，确保视觉连贯性。

### Q: 可以修改中间某个片段的提示词吗？
A: 当前版本所有片段使用相同提示词。未来版本会支持每个片段独立设置提示词。

## 错误处理

### 常见错误码

| 错误码 | 说明 | 解决方法 |
|--------|------|---------|
| 400 | 参数错误 | 检查参数格式和范围 |
| 404 | 图片文件不存在 | 确认文件已上传到input文件夹 |
| 500 | ComfyUI服务错误 | 检查ComfyUI服务是否正常运行 |
| 504 | 任务超时 | 增加超时时间或减少视频时长 |

### 错误响应示例

```json
{
  "code": 400,
  "message": "参数错误: duration必须是5的倍数",
  "data": null,
  "timestamp": "2025-01-01T12:00:00"
}
```

## 示例代码

完整的Python客户端示例：

```python
import requests
import time
from pathlib import Path

class Wan22I2VClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def generate_video(self, image_path, prompt, duration=10, **kwargs):
        """上传图片并生成视频"""
        url = f"{self.base_url}/api/wan22_i2v/upload_and_generate"
        
        with open(image_path, "rb") as f:
            files = {"image": f}
            data = {
                "prompt": prompt,
                "duration": duration,
                **kwargs
            }
            
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            return result['data']['task_id']
    
    def wait_for_completion(self, task_id, check_interval=2):
        """等待任务完成并返回结果"""
        url = f"{self.base_url}/api/task/{task_id}"
        
        while True:
            response = requests.get(url)
            result = response.json()
            
            status = result['data']['status']
            
            if status == "completed":
                return result['data']['result']
            elif status == "failed":
                raise Exception(f"任务失败: {result['data'].get('error')}")
            
            print(f"任务进行中... (状态: {status})")
            time.sleep(check_interval)
    
    def download_video(self, video_info, save_path):
        """下载生成的视频"""
        filename = video_info['filename']
        subfolder = video_info.get('subfolder', '')
        video_type = video_info.get('type', 'output')
        
        url = f"{self.base_url}/api/video/{filename}"
        params = {"subfolder": subfolder, "type": video_type}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        with open(save_path, "wb") as f:
            f.write(response.content)
        
        print(f"视频已保存到: {save_path}")

# 使用示例
if __name__ == "__main__":
    client = Wan22I2VClient()
    
    # 生成15秒视频
    task_id = client.generate_video(
        image_path="input.png",
        prompt="A beautiful woman walking in a garden",
        duration=15,
        width=480,
        height=832,
        frame_rate=16,
        steps=6
    )
    
    print(f"任务已提交: {task_id}")
    
    # 等待完成
    result = client.wait_for_completion(task_id)
    
    # 下载视频
    videos = result['outputs'].get('images', [])
    for i, video in enumerate(videos):
        if video['filename'].endswith('.mp4'):
            client.download_video(video, f"output_{i}.mp4")
```

## 更新日志

### v1.0.0 (2025-01-01)
- ✨ 初始版本发布
- ✅ 支持5-30秒视频生成
- ✅ 智能片段拼接
- ✅ 自动颜色匹配
- ✅ 一键上传生成

