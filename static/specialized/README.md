# 专用API测试页面

本文件夹包含针对专用工作流API的独立测试页面。

## 📁 文件结构

```
static/specialized/
├── index.html              # 专用API主入口页面
├── text2image.html         # 文生图API测试页面
├── text2image.js           # 文生图页面逻辑
├── wan22_i2v.html          # Wan2.2图生视频API测试页面
├── wan22_i2v.js            # 视频生成页面逻辑
├── super_video.html        # SuperVideo视频放大测试页面
├── super_video.js          # 视频放大页面逻辑
├── infinitetalk_i2v.html   # InfiniteTalk音频驱动视频测试页面
├── infinitetalk_i2v.js     # 音频驱动视频页面逻辑
├── style.css               # 共享样式文件
└── README.md               # 本文件
```

## 🎯 设计目的

这些页面与核心的 `static/index.html`（工作流调试工具）分离，专门用于测试 `core/api/specialized/` 中的专用API：

1. **独立访问**: 每个API都有独立的测试页面
2. **简化界面**: 只显示相关API的参数，更直观
3. **快速测试**: 针对特定功能优化的UI
4. **易于维护**: 代码结构清晰，便于扩展

## 🌐 访问方式

### 从主页访问
在主页侧边栏点击 "🎨 专用API测试" 按钮

### 直接访问
- 主入口: `http://localhost:8000/static/specialized/index.html`
- 文生图: `http://localhost:8000/static/specialized/text2image.html`
- 图生视频: `http://localhost:8000/static/specialized/wan22_i2v.html`
- 视频放大: `http://localhost:8000/static/specialized/super_video.html`
- 音频驱动视频: `http://localhost:8000/static/specialized/infinitetalk_i2v.html`

## 📄 页面说明

### 1. index.html - 主入口页面
- 展示所有可用的专用API
- 以卡片形式呈现，点击进入对应测试页面
- 提供API简介和使用说明

### 2. text2image.html - 文生图测试页面
**对应API**: `/api/text2image`

**功能**:
- 输入提示词和参数
- 实时查看生成状态
- 预览和下载生成的图像

**使用流程**:
1. 输入提示词（必填）
2. 可选：输入负面提示词
3. 调整图像尺寸和采样步数
4. 点击"生成图像"
5. 等待生成完成并查看结果

### 3. wan22_i2v.html - 图生视频测试页面
**对应API**: `/api/wan22_i2v/upload_and_generate`

**功能**:
- 上传起始图片
- 设置视频参数（时长、分辨率、帧率等）
- 实时查看生成进度
- 播放和下载生成的视频

**使用流程**:
1. 点击上传起始图片
2. 输入视频描述提示词
3. 选择视频时长（5-30秒）
4. 调整分辨率和帧率
5. 点击"生成视频"
6. 等待生成完成并播放预览

### 4. super_video.html - 视频放大测试页面
**对应API**: `/api/super_video/upload_and_upscale`

**功能**:
- 上传低分辨率视频
- 选择放大模型
- 实时查看放大进度
- 下载高清放大后的视频

**使用流程**:
1. 点击上传视频文件
2. 选择放大模型（RealESRGAN等）
3. 设置tile_size参数
4. 点击"开始放大"
5. 等待处理完成并下载结果

### 5. infinitetalk_i2v.html - 音频驱动视频测试页面
**对应API**: `/api/infinitetalk-i2v/generate`

**功能**:
- 上传人物图片和音频文件
- 设置视频参数（分辨率、帧率等）
- 实时查看生成进度
- 播放和下载口型同步视频

**使用流程**:
1. 上传人物照片
2. 上传音频文件
3. 输入提示词描述
4. 选择输出分辨率（720x480等）
5. 设置音频裁剪时间
6. 点击"开始生成"
7. 等待生成完成并播放预览

## 🎨 样式指南

### 共享样式 (style.css)
所有页面共享的基础样式，包括：
- 渐变背景
- 表单组件样式
- 按钮样式
- 状态徽章
- 响应式布局
- 动画效果

### 页面特定样式
每个HTML文件都可以包含页面特定的 `<style>` 标签来定制外观。

### 颜色主题
- **文生图**: 紫色渐变 (#667eea → #764ba2)
- **图生视频**: 粉红渐变 (#f093fb → #f5576c)
- **视频放大**: 绿色渐变 (#11998e → #38ef7d)
- **音频驱动视频**: 暖色渐变 (#fa709a → #fee140)

## 🔧 如何添加新的测试页面

### 步骤1: 创建HTML文件
在 `static/specialized/` 中创建新文件，例如 `my_api.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>我的API测试</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="container">
    <a href="index.html">← 返回列表</a>
    <h1>我的API测试</h1>
    
    <div class="form-container">
      <!-- 你的表单 -->
    </div>
    
    <div class="result-container" id="resultContainer">
      <!-- 结果显示区域 -->
    </div>
  </div>
  
  <script src="my_api.js"></script>
</body>
</html>
```

### 步骤2: 创建JS文件
创建 `my_api.js` 处理逻辑：

```javascript
document.getElementById('myForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  // 收集表单数据
  const formData = { /* ... */ };
  
  // 提交到API
  const response = await fetch('/api/my_api', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(formData)
  });
  
  const result = await response.json();
  // 开始轮询状态
  pollTaskStatus(result.data.task_id);
});

async function pollTaskStatus(taskId) {
  // 实现状态轮询逻辑
}
```

### 步骤3: 更新主入口页面
在 `index.html` 中添加新卡片：

```html
<div class="api-card" onclick="location.href='my_api.html'">
  <h2>📦 我的API</h2>
  <p>API描述</p>
  <div>
    <span class="tag">标签1</span>
    <span class="tag">标签2</span>
  </div>
</div>
```

## 📊 状态徽章说明

页面使用不同颜色的徽章显示任务状态：

| 状态 | 颜色 | 说明 |
|------|------|------|
| 已提交 | 黄色 | 任务已提交到队列 |
| 生成中 | 绿色 | 正在生成中 |
| 完成 | 深绿 | 生成完成 |
| 失败 | 红色 | 生成失败 |

## 🔄 轮询机制

所有页面都实现了自动状态轮询：

```javascript
async function pollTaskStatus(taskId) {
  const poll = setInterval(async () => {
    const response = await fetch(`/api/task/${taskId}`);
    const result = await response.json();
    
    if (result.data.status === 'completed') {
      clearInterval(poll);
      // 显示结果
    }
  }, 1000); // 每秒查询一次
}
```

## 🎯 最佳实践

### 1. 用户体验
- 提供清晰的加载提示
- 显示预估生成时间
- 实时更新进度信息
- 支持结果预览和下载

### 2. 错误处理
- 友好的错误提示
- 失败后允许重试
- 记录详细错误信息

### 3. 性能优化
- 使用合理的轮询间隔
- 设置超时限制
- 避免过度请求

### 4. 响应式设计
- 支持移动设备访问
- 适配不同屏幕尺寸
- 确保触摸操作友好

## 📱 移动端适配

页面已包含响应式设计，在移动设备上：
- 表单自动单列布局
- 按钮更大更易点击
- 字体大小适配小屏幕
- 支持触摸滑动

## 🔗 相关文档

- [专用API代码文档](../../core/api/specialized/README.md)
- [Wan2.2 API完整文档](../../WAN22_I2V_API.md)
- [通用API文档](../../API_USAGE.md)

## 📝 更新日志

### 2025-11-12
- ✨ 添加InfiniteTalk音频驱动视频测试页面
- ✨ 实现文件拖拽上传功能
- ✨ 优化移动端体验

### 2025-10-28
- ✨ 创建specialized文件夹
- ✨ 添加文生图测试页面
- ✨ 添加Wan2.2图生视频测试页面
- ✨ 添加SuperVideo视频放大测试页面
- ✨ 实现共享样式系统
- ✨ 在主页添加入口链接

## 🤝 贡献指南

添加新测试页面时，请确保：

1. 遵循现有的UI/UX设计模式
2. 使用统一的颜色主题
3. 实现完整的状态轮询
4. 提供清晰的使用说明
5. 测试移动端适配
6. 更新本README

---

**最后更新**: 2025-11-12
**维护者**: ComfyAPI Team

