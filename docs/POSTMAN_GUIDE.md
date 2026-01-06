# Postman 使用指南

本文档详细说明如何使用Postman测试ComfyUI API。

## 📋 目录

- [快速开始](#快速开始)
- [提交工作流](#提交工作流)
- [查询任务状态](#查询任务状态)
- [修改工作流参数](#修改工作流参数)
- [导入Postman集合](#导入postman集合)

---

## 🚀 快速开始

### 1. 确保服务运行

```bash
python start.py
```

服务地址：`http://localhost:8000`

### 2. 打开Postman

创建新的Request或Collection

---

## 📤 提交工作流

### 方法1：直接发送JSON文件内容（推荐）

#### 步骤1：创建新请求

在Postman中：
1. 点击 **New** → **HTTP Request**
2. 方法选择：**POST**
3. URL：`http://localhost:8000/api/workflow/submit`

#### 步骤2：配置Headers

点击 **Headers** 标签，添加：

```
Key: Content-Type
Value: application/json
```

#### 步骤3：配置Body

1. 点击 **Body** 标签
2. 选择 **raw**
3. 右侧下拉菜单选择 **JSON**
4. 在文本框中粘贴工作流JSON

**⚠️ 重要：正确的请求体格式**

API期望的格式是：
```json
{
  "workflow": { 你的工作流JSON },
  "params": {},      // 可选
  "timeout": 600     // 可选，默认600秒
}
```

**示例1：完整的qwen_t2i_distill工作流**

```json
{
  "workflow": {
    "3": {
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
    },
    "class_type": "KSampler"
  },
  "6": {
    "inputs": {
      "text": "A beautiful sunset over the ocean, vibrant colors",
      "clip": ["38", 0]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": {
      "text": "blurry, low quality, distorted",
      "clip": ["38", 0]
    },
    "class_type": "CLIPTextEncode"
  },
  "8": {
    "inputs": {
      "samples": ["3", 0],
      "vae": ["39", 0]
    },
    "class_type": "VAEDecode"
  },
  "37": {
    "inputs": {
      "unet_name": "qwen_image_distill_full_fp8_e4m3fn.safetensors",
      "weight_dtype": "default"
    },
    "class_type": "UNETLoader"
  },
  "38": {
    "inputs": {
      "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
      "type": "qwen_image",
      "device": "default"
    },
    "class_type": "CLIPLoader"
  },
  "39": {
    "inputs": {
      "vae_name": "qwen_image_vae.safetensors"
    },
    "class_type": "VAELoader"
  },
  "60": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": ["8", 0]
    },
    "class_type": "SaveImage"
  },
  "66": {
    "inputs": {
      "shift": 3.0,
      "model": ["37", 0]
    },
    "class_type": "ModelSamplingAuraFlow"
  },
  "72": {
    "inputs": {
      "width": 1024,
      "height": 1024,
      "batch_size": 1
    },
    "class_type": "EmptySD3LatentImage"
    }
  },
  "params": {},
  "timeout": 600
}
```

#### 步骤4：发送请求

点击 **Send** 按钮

#### 步骤5：查看响应

成功响应示例：
```json
{
  "task_id": "ca5bbc73-b893-4944-9a58-ecb75855e4e2",
  "status": "queued",
  "message": "任务已提交"
}
```

---

### 方法2：从文件加载（更方便）

#### 在Postman中加载JSON文件：

1. 打开 **Body** 标签
2. 选择 **raw** 和 **JSON**
3. 点击文本框
4. 使用文本编辑器打开 `workflows/qwen_t2i_distill.json`
5. 复制全部内容
6. 粘贴到Postman的Body中

#### 或使用Postman的文件导入功能：

虽然Postman不直接支持在Body中导入文件，但你可以：

1. 用记事本/VSCode打开 `workflows/qwen_t2i_distill.json`
2. 全选复制（Ctrl+A, Ctrl+C）
3. 切换到Postman，粘贴到Body中
4. 修改需要的参数
5. 发送

---

## 🔍 查询任务状态

### 创建新请求

1. 方法：**GET**
2. URL：`http://localhost:8000/api/task/{task_id}`

⚠️ 注意：路径是 `/api/task/` （单数），不是 `/api/tasks/`

将 `{task_id}` 替换为实际的任务ID

**示例：**
```
GET http://localhost:8000/api/task/ca5bbc73-b893-4944-9a58-ecb75855e4e2
```

### 响应示例

**任务进行中：**
```json
{
  "task_id": "ca5bbc73-b893-4944-9a58-ecb75855e4e2",
  "status": "running",
  "created_at": "2025-10-16T15:30:00"
}
```

**任务完成：**
```json
{
  "task_id": "ca5bbc73-b893-4944-9a58-ecb75855e4e2",
  "status": "completed",
  "created_at": "2025-10-16T15:30:00",
  "completed_at": "2025-10-16T15:31:00",
  "outputs": [
    {
      "type": "image",
      "url": "/api/image/image_001.png?type=output"
    }
  ]
}
```

---

## ✏️ 修改工作流参数

### 常见参数修改位置

#### 1. 修改提示词

在Body的JSON中找到节点6和7：

```json
"6": {
  "inputs": {
    "text": "你的正面提示词（在这里修改）",
    "clip": ["38", 0]
  },
  "class_type": "CLIPTextEncode"
},
"7": {
  "inputs": {
    "text": "你的负面提示词（在这里修改）",
    "clip": ["38", 0]
  },
  "class_type": "CLIPTextEncode"
}
```

#### 2. 修改采样参数

找到节点3（KSampler）：

```json
"3": {
  "inputs": {
    "seed": -1,              // 改为-1自动随机，或固定数字
    "steps": 20,             // 采样步数（10-50）
    "cfg": 1,                // CFG引导强度
    "sampler_name": "dpmpp_sde_gpu",  // 采样器
    "scheduler": "simple",    // 调度器
    "denoise": 1             // 降噪强度
  }
}
```

#### 3. 修改图像尺寸

找到节点72：

```json
"72": {
  "inputs": {
    "width": 1024,    // 宽度（改为512, 768, 1024, 1328等）
    "height": 1024,   // 高度
    "batch_size": 1   // 批量大小
  },
  "class_type": "EmptySD3LatentImage"
}
```

#### 4. 修改输出文件名

找到节点60：

```json
"60": {
  "inputs": {
    "filename_prefix": "my_image",  // 修改文件名前缀
    "images": ["8", 0]
  },
  "class_type": "SaveImage"
}
```

### 完整修改示例

修改后的JSON：

```json
{
  "3": {
    "inputs": {
      "seed": 123456789,
      "steps": 30,
      "cfg": 1.5,
      "sampler_name": "dpmpp_sde_gpu",
      "scheduler": "simple",
      "denoise": 1,
      "model": ["66", 0],
      "positive": ["6", 0],
      "negative": ["7", 0],
      "latent_image": ["72", 0]
    },
    "class_type": "KSampler"
  },
  "6": {
    "inputs": {
      "text": "Portrait of a young woman, professional photography, natural lighting",
      "clip": ["38", 0]
    },
    "class_type": "CLIPTextEncode"
  },
  "7": {
    "inputs": {
      "text": "blurry, low quality, cartoon, illustration, ugly",
      "clip": ["38", 0]
    },
    "class_type": "CLIPTextEncode"
  },
  "72": {
    "inputs": {
      "width": 1328,
      "height": 1328,
      "batch_size": 1
    },
    "class_type": "EmptySD3LatentImage"
  },
  "60": {
    "inputs": {
      "filename_prefix": "portrait_test",
      "images": ["8", 0]
    },
    "class_type": "SaveImage"
  }
}
```

---

## 📦 导入Postman集合

### 创建Postman Collection

我为你准备了一个预配置的Collection，包含所有常用请求。

#### Collection JSON文件内容

保存以下内容为 `ComfyUI_API.postman_collection.json`：

```json
{
  "info": {
    "name": "ComfyUI API",
    "description": "ComfyUI API中间件接口集合",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "提交工作流",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"3\": {\n    \"inputs\": {\n      \"seed\": -1,\n      \"steps\": 20,\n      \"cfg\": 1,\n      \"sampler_name\": \"dpmpp_sde_gpu\",\n      \"scheduler\": \"simple\",\n      \"denoise\": 1,\n      \"model\": [\"66\", 0],\n      \"positive\": [\"6\", 0],\n      \"negative\": [\"7\", 0],\n      \"latent_image\": [\"72\", 0]\n    },\n    \"class_type\": \"KSampler\"\n  },\n  \"6\": {\n    \"inputs\": {\n      \"text\": \"A beautiful sunset\",\n      \"clip\": [\"38\", 0]\n    },\n    \"class_type\": \"CLIPTextEncode\"\n  },\n  \"7\": {\n    \"inputs\": {\n      \"text\": \"blurry, low quality\",\n      \"clip\": [\"38\", 0]\n    },\n    \"class_type\": \"CLIPTextEncode\"\n  },\n  \"8\": {\n    \"inputs\": {\n      \"samples\": [\"3\", 0],\n      \"vae\": [\"39\", 0]\n    },\n    \"class_type\": \"VAEDecode\"\n  },\n  \"37\": {\n    \"inputs\": {\n      \"unet_name\": \"qwen_image_distill_full_fp8_e4m3fn.safetensors\",\n      \"weight_dtype\": \"default\"\n    },\n    \"class_type\": \"UNETLoader\"\n  },\n  \"38\": {\n    \"inputs\": {\n      \"clip_name\": \"qwen_2.5_vl_7b_fp8_scaled.safetensors\",\n      \"type\": \"qwen_image\",\n      \"device\": \"default\"\n    },\n    \"class_type\": \"CLIPLoader\"\n  },\n  \"39\": {\n    \"inputs\": {\n      \"vae_name\": \"qwen_image_vae.safetensors\"\n    },\n    \"class_type\": \"VAELoader\"\n  },\n  \"60\": {\n    \"inputs\": {\n      \"filename_prefix\": \"ComfyUI\",\n      \"images\": [\"8\", 0]\n    },\n    \"class_type\": \"SaveImage\"\n  },\n  \"66\": {\n    \"inputs\": {\n      \"shift\": 3.0,\n      \"model\": [\"37\", 0]\n    },\n    \"class_type\": \"ModelSamplingAuraFlow\"\n  },\n  \"72\": {\n    \"inputs\": {\n      \"width\": 1024,\n      \"height\": 1024,\n      \"batch_size\": 1\n    },\n    \"class_type\": \"EmptySD3LatentImage\"\n  }\n}"
        },
        "url": {
          "raw": "http://localhost:8000/api/workflow/submit",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "workflow", "submit"]
        }
      }
    },
    {
      "name": "查询任务状态",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/api/tasks/:task_id",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "tasks", ":task_id"],
          "variable": [
            {
              "key": "task_id",
              "value": "your-task-id-here"
            }
          ]
        }
      }
    },
    {
      "name": "查询所有任务",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/api/tasks",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "tasks"]
        }
      }
    },
    {
      "name": "查询队列状态",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/api/queue",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "queue"]
        }
      }
    },
    {
      "name": "健康检查",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/api/health",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "health"]
        }
      }
    },
    {
      "name": "系统诊断",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "http://localhost:8000/api/diagnose",
          "protocol": "http",
          "host": ["localhost"],
          "port": "8000",
          "path": ["api", "diagnose"]
        }
      }
    }
  ]
}
```

#### 导入步骤

1. 复制上面的JSON内容
2. 保存为文件（例如：`ComfyUI_API.postman_collection.json`）
3. 在Postman中点击 **Import**
4. 选择刚才保存的JSON文件
5. 导入完成！

---

## 🎯 使用场景示例

### 场景1：测试不同提示词

1. 打开 "提交工作流" 请求
2. 在Body中修改节点6的text字段
3. 点击Send
4. 复制响应中的task_id
5. 打开 "查询任务状态" 请求
6. 替换URL中的task_id
7. 重复点击Send查看进度

### 场景2：批量测试不同参数

使用Postman的 **Environment** 功能：

1. 创建Environment（例如：ComfyUI-Dev）
2. 添加变量：
   - `base_url`: `http://localhost:8000`
   - `prompt`: `A beautiful sunset`
   - `steps`: `20`
   - `seed`: `-1`

3. 在请求中使用变量：
```json
"6": {
  "inputs": {
    "text": "{{prompt}}",
    "clip": ["38", 0]
  }
}
```

4. 修改Environment中的变量值即可快速测试

### 场景3：保存多个工作流模板

为不同的工作流创建多个请求：

- "提交工作流 - Qwen"
- "提交工作流 - HiDream"
- "提交工作流 - 自定义"

每个保存不同的工作流JSON

---

## 💡 实用技巧

### 技巧1：使用Postman变量

在URL中使用环境变量：
```
{{base_url}}/api/tasks/{{task_id}}
```

### 技巧2：保存响应

在响应下方点击 **Save Response**，保存为示例

### 技巧3：使用Tests自动提取task_id

在请求的 **Tests** 标签添加：

```javascript
// 自动保存task_id到环境变量
if (pm.response.code === 200) {
    var jsonData = pm.response.json();
    if (jsonData.task_id) {
        pm.environment.set("task_id", jsonData.task_id);
        console.log("Task ID saved:", jsonData.task_id);
    }
}
```

这样提交任务后，task_id会自动保存，查询时直接使用`{{task_id}}`

### 技巧4：使用Pre-request Script动态生成seed

在 **Pre-request Script** 标签添加：

```javascript
// 生成随机seed
var randomSeed = Math.floor(Math.random() * 1000000000000000);
pm.environment.set("random_seed", randomSeed);
```

然后在Body中使用：
```json
"seed": {{random_seed}}
```

---

## ❓ 常见问题

### Q: 为什么显示 "Could not send request"？

A: 
1. 确认API服务已启动（`python start.py`）
2. 检查URL是否正确
3. 检查端口是否被占用

### Q: 返回422错误 (Unprocessable Entity)？

A: **这是最常见的错误！** 请求体格式不正确。

**错误原因：** 直接发送了工作流JSON，没有包装在`workflow`字段中。

**错误的格式❌：**
```json
{
  "3": { ... },
  "6": { ... }
}
```

**正确的格式✅：**
```json
{
  "workflow": {
    "3": { ... },
    "6": { ... }
  },
  "params": {},
  "timeout": 600
}
```

**快速修复：**
1. 在Postman的Body中，在整个工作流JSON外面添加 `"workflow": { ... }`
2. 在结尾添加 `"params": {}, "timeout": 600`
3. 确保JSON格式正确（注意花括号匹配）

### Q: 返回400错误？

A: 
1. 检查JSON格式是否正确（可以用JSON校验工具）
2. 确保所有必需的节点都存在
3. 查看响应的error字段获取详细错误信息

### Q: 如何查看生成的图片？

A: 
1. 提交任务并获得task_id
2. 查询任务状态直到status为"completed"
3. 响应中的outputs包含图片URL
4. 在浏览器中访问：`http://localhost:8000{图片URL}`

### Q: 如何批量测试？

A: 使用Postman的 **Collection Runner**：
1. 准备多组数据文件（CSV或JSON）
2. 在Collection中使用变量
3. 运行Collection Runner并导入数据文件

---

## 📚 参考资料

- [API完整文档](./API_USAGE.md)
- [在线API文档](http://localhost:8000/docs) - 启动服务后访问
- [Postman官方文档](https://learning.postman.com/)

---

## 🎉 快速测试清单

- [ ] 导入Postman Collection
- [ ] 测试健康检查接口
- [ ] 提交一个简单的工作流
- [ ] 查询任务状态
- [ ] 修改提示词重新提交
- [ ] 测试不同参数组合
- [ ] 设置Environment变量
- [ ] 添加自动化Tests脚本

全部完成后，你就掌握了Postman的基本使用！🚀

