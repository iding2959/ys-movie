"""
专用工作流API模块
当前仅保留「SuperVideo 视频放大」相关API
"""

from .super_video import router as super_video_router, setup_super_video_routes

__all__ = [
  'super_video_router',
  'setup_super_video_routes'
]

