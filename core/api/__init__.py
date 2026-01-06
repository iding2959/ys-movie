"""
API 路由模块 - 通用API
专用工作流API已移至 specialized/ 文件夹
"""
from .system import router as system_router
from .workflow import router as workflow_router
from .task import router as task_router
from .media import router as media_router

__all__ = [
  'system_router',
  'workflow_router',
  'task_router',
  'media_router',
]

