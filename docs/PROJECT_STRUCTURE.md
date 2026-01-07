# 项目结构说明

ComfyUI API中间件 - 完整项目结构文档

## 📁 目录结构

```
ys-movie/
├── core/                           # 核心代码
│   ├── __init__.py                 # 核心模块导出
│   ├── comfyui_client.py          # ComfyUI客户端封装（含图片上传）
│   ├── managers.py                 # 任务和连接管理器
│   ├── models.py                   # 数据模型定义
│   ├── response.py                 # 统一响应格式
│   ├── utils.py                    # 工具函数
│   └── api/                        # API路由模块
│       ├── __init__.py             # API模块导出
│       ├── system.py               # 系统相关API（健康检查、诊断等）
│       ├── task.py                 # 任务查询API
│       ├── media.py                # 媒体文件API（图片、视频获取和上传）
│       ├── workflow.py             # 通用工作流API
│       └── specialized/            # 专用工作流API
│           ├── __init__.py         # 专用API模块导出
│           ├── README.md           # 专用API使用文档
│           └── super_video.py     # SuperVideo视频放大API
│
├── static/                         # 静态文件（前端页面）
│   ├── index.html                  # 监控面板（工作流调试工具）
│   ├── app.js                      # 监控面板JavaScript
│   ├── style.css                   # 监控面板样式
│   └── specialized/                # 专用API测试页面
│       ├── index.html              # 专用API主入口
│       └── super_video.html        # SuperVideo视频放大测试页面
│
├── workflows/                      # 工作流文件
│   └── flash_vsr.json             # FlashVSR视频放大工作流
│
├── uploads/                        # 上传文件目录
├── outputs/                        # 输出文件目录
│
├── docs/                           # 文档目录
│   ├── API_USAGE.md                # 通用API使用文档
│   ├── POSTMAN_GUIDE.md           # Postman使用指南
│   ├── PROJECT_STRUCTURE.md       # 本文件
│   └── WORKFLOW_ADAPTATION_GUIDE.md # 工作流适配指南
│
├── main.py                         # FastAPI主应用入口
├── config.py                       # 配置文件
├── requirements.txt                # Python依赖
└── README.md                       # 项目说明
```

## 🎯 架构设计

### 1. 分层架构

```
┌─────────────────────────────────────────┐
│          前端层 (Frontend)               │
│  ┌──────────────┬──────────────────┐    │
│  │  通用工具页   │   专用API测试页   │    │
│  │ index.html   │ specialized/     │    │
│  └──────────────┴──────────────────┘    │
└─────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         API路由层 (Routing)              │
│  ┌──────────────┬──────────────────┐    │
│  │  通用API     │   专用API         │    │
│  │ system       │ specialized/     │    │
│  │ task         │ - text2image     │    │
│  │ media        │ - wan22_i2v      │    │
│  │ workflow     │                  │    │
│  └──────────────┴──────────────────┘    │
└─────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       业务逻辑层 (Business Logic)         │
│  ┌──────────────────────────────────┐   │
│  │  ComfyUI客户端                    │   │
│  │  - 工作流提交                     │   │
│  │  - 图片上传                       │   │
│  │  - 任务轮询                       │   │
│  │  - 结果提取                       │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      ComfyUI服务器 (External)            │
│         192.168.48.123:8188             │
└─────────────────────────────────────────┘
```

### 2. API分类

#### 通用API (`core/api/`)
提供基础ComfyUI功能的封装：

- **system.py**: 系统监控
  - `/api/health` - 健康检查
  - `/api/diagnose` - 连接诊断
  - `/api/queue` - 队列信息

- **task.py**: 任务管理
  - `/api/task/{task_id}` - 查询任务状态
  - `/api/tasks` - 任务列表
  - `/api/history` - 历史记录

- **media.py**: 媒体处理
  - `/api/image/{filename}` - 获取图片
  - `/api/video/{filename}` - 获取视频
  - `/api/upload/image` - 上传图片【新增】

- **workflow.py**: 工作流操作
  - `/api/workflow/submit` - 提交工作流
  - `/api/workflow/upload` - 上传工作流
  - `/api/workflows` - 工作流列表

#### 专用API (`core/api/specialized/`)
针对特定场景的高级封装：

- **super_video.py**: SuperVideo视频放大API
  - `/api/super_video/upload_and_upscale` - 上传视频并放大（推荐）
  - `/api/super_video/upscale` - 使用已上传视频放大
  - 支持AI视频超分辨率处理，4倍放大
  - 支持多种放大模型（FlashVSR等）
  - 自动保留原视频的帧率和音频

### 3. 前端结构

#### 主页面 (`static/`)
- **index.html**: 监控面板（通用工作流调试工具）
  - 上传和编辑任意工作流
  - 动态参数提取和修改
  - 实时任务监控
  - 支持LoadImage节点图片上传
  - 访问路径: `/dashboard`

#### 专用测试页面 (`static/specialized/`)
- **index.html**: 专用API入口
  - 展示所有可用专用API
  - 卡片式导航

- **super_video.html**: SuperVideo视频放大测试
  - 视频上传界面
  - 模型选择器
  - 进度跟踪
  - 视频播放预览
  - 访问路径: `/` (根路径)

## 🔄 请求流程示例

### SuperVideo视频放大流程

```
用户 → super_video.html (根路径 /)
       ↓
    上传视频 + 选择模型
       ↓
    super_video.js
       ↓ POST /api/super_video/upload_and_upscale
    specialized/super_video.py
       ↓
    1. 上传视频到ComfyUI input文件夹
    2. 加载flash_vsr工作流
    3. 修改工作流参数（视频文件名、模型等）
    4. 提交workflow到ComfyUI
       ↓
    返回task_id
       ↓
    轮询 /api/task/{task_id}
       ↓
    显示放大后的视频
```

### 通用工作流流程

```
用户 → index.html (监控面板 /dashboard)
       ↓
    上传工作流文件或选择已有工作流
       ↓
    修改参数（提示词、尺寸等）
       ↓
    app.js
       ↓ POST /api/workflow/submit
    api/workflow.py
       ↓
    提交workflow到ComfyUI
       ↓
    返回task_id
       ↓
    WebSocket实时推送状态
       ↓
    显示生成结果
```

## 📊 数据流

### 图片上传数据流【新增】

```
前端文件选择
    ↓
FormData对象
    ↓
POST /api/upload/image
    ↓
media.py: upload_image()
    ↓
comfyui_client.py: async_upload_image()
    ↓
ComfyUI服务器 /upload/image
    ↓
保存到ComfyUI/input/文件夹
    ↓
返回文件名
    ↓
前端更新workflow中的image参数
    ↓
提交完整workflow
```

## 🎨 设计原则

### 1. 关注点分离
- **通用功能** → `core/api/`
- **专用功能** → `core/api/specialized/`
- **基础工具** → `static/`
- **专用测试** → `static/specialized/`

### 2. 代码复用
- 共享ComfyUI客户端
- 统一响应格式
- 复用任务管理器
- 共享样式系统

### 3. 易于扩展
- 模块化设计
- 清晰的接口定义
- 详细的文档说明
- 一致的代码风格

### 4. 用户友好
- 直观的UI设计
- 实时状态反馈
- 清晰的错误提示
- 完整的使用文档

## 🚀 快速开始

### 启动服务
```bash
python start.py
```

### 访问页面
- SuperVideo界面: http://localhost:8000 (根路径)
- 监控面板: http://localhost:8000/dashboard
- 专用API测试: http://localhost:8000/static/specialized/

### API文档
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📝 开发指南

### 添加新的专用API

1. **后端开发**
   ```bash
   # 在 core/api/specialized/ 创建新文件
   vim core/api/specialized/my_new_api.py
   
   # 更新 __init__.py
   vim core/api/specialized/__init__.py
   
   # 在 main.py 注册路由
   vim main.py
   ```

2. **前端开发**
   ```bash
   # 在 static/specialized/ 创建测试页面
   vim static/specialized/my_new_api.html
   vim static/specialized/my_new_api.js
   
   # 更新入口页面
   vim static/specialized/index.html
   ```

3. **文档更新**
   - 更新 `core/api/specialized/README.md`
   - 更新 `static/specialized/README.md`
   - 添加API使用示例

## 🔧 技术栈

### 后端
- **FastAPI**: 现代Python Web框架
- **aiohttp**: 异步HTTP客户端
- **Pydantic**: 数据验证
- **websocket-client**: WebSocket支持

### 前端
- **原生JavaScript**: 无框架依赖
- **HTML5 + CSS3**: 现代Web标准
- **FormData API**: 文件上传
- **Fetch API**: HTTP请求

### ComfyUI集成
- **API格式workflow**: JSON格式
- **图片上传**: multipart/form-data
- **任务轮询**: 定期HTTP请求
- **媒体获取**: 直接URL访问

## 📈 性能优化

- 异步I/O操作
- HTTP会话复用
- 合理的轮询间隔
- 结果缓存机制
- 静态文件CDN（可选）

## 🔒 安全考虑

- CORS配置
- 文件类型验证
- 文件大小限制
- 路径注入防护
- 错误信息脱敏

## 📚 相关文档

- [API使用文档](./API_USAGE.md)
- [Postman使用指南](./POSTMAN_GUIDE.md)
- [工作流适配指南](./WORKFLOW_ADAPTATION_GUIDE.md)
- [专用API文档](../core/api/specialized/README.md)

---

**最后更新**: 2025-01-XX  
**版本**: v2.0.0  
**维护者**: ComfyAPI Team

