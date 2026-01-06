"""
专用工作流API模块
包含针对特定工作流的封装API
"""

from .text2image import router as text2image_router, setup_text2image_routes
from .wan22_i2v import router as wan22_i2v_router, setup_wan22_i2v_routes
from .super_video import router as super_video_router, setup_super_video_routes
from .infinitetalk_i2v import router as infinitetalk_i2v_router, setup_infinitetalk_i2v_routes

__all__ = [
  'text2image_router',
  'setup_text2image_routes',
  'wan22_i2v_router',
  'setup_wan22_i2v_routes',
  'super_video_router',
  'setup_super_video_routes',
  'infinitetalk_i2v_router',
  'setup_infinitetalk_i2v_routes'
]

