"""
配置文件
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
  """应用配置"""
  
  # ComfyUI服务器配置
  comfyui_server: str = "192.168.48.173:8188"
  comfyui_protocol: str = "http"
  comfyui_ws_protocol: str = "ws"
  
  # API服务器配置
  api_host: str = "0.0.0.0"
  api_port: int = 12321
  
  # 文件存储配置
  upload_dir: str = "uploads"
  output_dir: str = "outputs"
  workflow_dir: str = "workflows"
  
  # 任务配置
  default_timeout: int = 600  # 默认超时时间（秒）
  max_tasks: int = 100  # 最大保存任务数
  
  # 安全配置
  cors_origins: list = ["*"]
  api_key: Optional[str] = None
  
  # 日志配置
  log_level: str = "INFO"
  log_file: Optional[str] = "comfyui_api.log"
  
  class Config:
    env_file = ".env"
    env_prefix = "COMFYUI_"

# 创建全局配置实例
settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.output_dir, exist_ok=True)
os.makedirs(settings.workflow_dir, exist_ok=True)
