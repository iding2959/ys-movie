"""
ComfyUI API中间件服务 - 主应用入口
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import json
import logging

# 导入核心模块
from core import ComfyUIClient, TaskManager, ConnectionManager
from core.api.system import router as system_base_router, setup_system_routes
from core.api.workflow import router as workflow_base_router, setup_workflow_routes
from core.api.task import router as task_base_router, setup_task_routes
from core.api.media import router as media_base_router, setup_media_routes

# 导入专用工作流API
from core.api.specialized.text2image import router as text2image_base_router, setup_text2image_routes
from core.api.specialized.wan22_i2v import router as wan22_i2v_base_router, setup_wan22_i2v_routes
from core.api.specialized.super_video import router as super_video_base_router, setup_super_video_routes
from core.api.specialized.infinitetalk_i2v import router as infinitetalk_i2v_base_router, setup_infinitetalk_i2v_routes

# 导入配置
from config import settings

# 配置日志
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局配置 - 从config.py读取配置
COMFYUI_SERVER = settings.comfyui_server
COMFYUI_PROTOCOL = settings.comfyui_protocol
COMFYUI_WS_PROTOCOL = settings.comfyui_ws_protocol
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
WORKFLOW_DIR = Path("workflows")

# 创建必要的目录
for directory in [UPLOAD_DIR, OUTPUT_DIR, WORKFLOW_DIR]:
  directory.mkdir(exist_ok=True)

# 创建FastAPI应用
app = FastAPI(
  title="ComfyUI API中间件",
  description="提供ComfyUI API的封装和管理",
  version="2.0.0"
)

# 配置CORS
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# 创建管理器实例
task_manager = TaskManager()
connection_manager = ConnectionManager()

# 设置并注册所有路由
system_router = setup_system_routes(COMFYUI_SERVER, COMFYUI_PROTOCOL, COMFYUI_WS_PROTOCOL)
text2image_router = setup_text2image_routes(
  COMFYUI_SERVER,
  task_manager,
  connection_manager,
  WORKFLOW_DIR,
  COMFYUI_PROTOCOL,
  COMFYUI_WS_PROTOCOL
)
workflow_router = setup_workflow_routes(
  COMFYUI_SERVER,
  task_manager,
  connection_manager,
  WORKFLOW_DIR,
  COMFYUI_PROTOCOL,
  COMFYUI_WS_PROTOCOL
)
task_router = setup_task_routes(
  COMFYUI_SERVER,
  task_manager,
  COMFYUI_PROTOCOL,
  COMFYUI_WS_PROTOCOL
)
media_router = setup_media_routes(
  COMFYUI_SERVER,
  task_manager,
  COMFYUI_PROTOCOL,
  COMFYUI_WS_PROTOCOL
)
wan22_i2v_router = setup_wan22_i2v_routes(
  COMFYUI_SERVER,
  task_manager,
  connection_manager,
  COMFYUI_PROTOCOL,
  COMFYUI_WS_PROTOCOL
)
super_video_router = setup_super_video_routes(
  COMFYUI_SERVER,
  task_manager,
  connection_manager,
  WORKFLOW_DIR,
  COMFYUI_PROTOCOL,
  COMFYUI_WS_PROTOCOL
)
infinitetalk_i2v_router = setup_infinitetalk_i2v_routes(
  COMFYUI_SERVER,
  task_manager,
  connection_manager,
  WORKFLOW_DIR,
  COMFYUI_PROTOCOL,
  COMFYUI_WS_PROTOCOL
)

# 注册路由到应用
app.include_router(system_router)
app.include_router(text2image_router)
app.include_router(workflow_router)
app.include_router(task_router)
app.include_router(media_router)
app.include_router(wan22_i2v_router)
app.include_router(super_video_router)
app.include_router(infinitetalk_i2v_router)


@app.get("/", response_class=HTMLResponse)
async def root():
  """根路径，返回首页"""
  try:
    index_file = Path("static/index.html")
    if not index_file.exists():
      return HTMLResponse(
        content="<h1>404 - 未找到index.html</h1>"
                "<p>请确保static/index.html文件存在</p>"
      )
    
    with open(index_file, "r", encoding="utf-8") as f:
      content = f.read()
    return HTMLResponse(content=content)
  except Exception as e:
    logger.error(f"读取index.html失败: {e}")
    return HTMLResponse(content=f"<h1>500 - 服务器错误</h1><p>{str(e)}</p>")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
  """WebSocket连接端点"""
  await connection_manager.connect(websocket)
  try:
    while True:
      # 接收客户端消息
      data = await websocket.receive_text()
      message = json.loads(data)
      
      # 处理不同类型的消息
      if message.get("type") == "ping":
        await connection_manager.send_personal_message(
          json.dumps({"type": "pong"}),
          websocket
        )
      elif message.get("type") == "subscribe":
        # 订阅特定任务的更新
        task_id = message.get("task_id")
        await connection_manager.send_personal_message(
          json.dumps({"type": "subscribed", "task_id": task_id}),
          websocket
        )
      
  except WebSocketDisconnect:
    connection_manager.disconnect(websocket)
  except Exception as e:
    logger.error(f"WebSocket错误: {e}")
    connection_manager.disconnect(websocket)


# 挂载静态文件（需要在最后）
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
  import uvicorn
  logger.info(f"启动ComfyUI API中间件服务")
  logger.info(f"ComfyUI服务器: {COMFYUI_SERVER}")
  logger.info(f"API服务地址: http://{settings.api_host}:{settings.api_port}")
  logger.info(f"工作流目录: {WORKFLOW_DIR.absolute()}")
  logger.info(f"热重载: 已启用")
  
  # 使用字符串引用以支持更好的热重载
  uvicorn.run(
    "main:app",  # 使用字符串引用而不是直接传app对象
    host=settings.api_host,
    port=settings.api_port,
    reload=True,
    reload_dirs=["core"],  # 只监控核心代码目录
    reload_excludes=[
      "**/__pycache__/**",
      "**/outputs/**",
      "**/uploads/**",
      "**/.git/**",
      "**/node_modules/**",
      "**/*.pyc",
      "**/*.log",
      "**/workflows/**",  # 工作流文件变化不触发重载
      "**/docs/**",
      "**/examples/**",
      "**/*.md",
      "**/uv.lock",
      "**/pyproject.toml",
      "**/docker-compose.yml",
      "**/Dockerfile",
      "**/DOCKER.md",
      "**/systemctl.md",
      "**/run.md",
      "**/README.md"
    ],
    log_level="info"
  )
