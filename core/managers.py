"""
管理器类：任务管理器和 WebSocket 连接管理器
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import WebSocket


class TaskManager:
  """
  任务管理器
  负责管理所有提交的任务状态和结果
  """
  
  def __init__(self):
    self.tasks: Dict[str, Dict[str, Any]] = {}
    
  def add_task(self, task_id: str, task_info: Dict[str, Any]):
    """
    添加任务
    
    Args:
      task_id: 任务ID
      task_info: 任务信息字典
    """
    self.tasks[task_id] = {
      **task_info,
      "created_at": datetime.now().isoformat(),
      "status": "pending"
    }
    
  def update_task(self, task_id: str, updates: Dict[str, Any]):
    """
    更新任务状态
    
    Args:
      task_id: 任务ID
      updates: 要更新的字段
    """
    if task_id in self.tasks:
      self.tasks[task_id].update(updates)
      
  def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
    """
    获取任务信息
    
    Args:
      task_id: 任务ID
      
    Returns:
      任务信息字典，不存在则返回 None
    """
    return self.tasks.get(task_id)
    
  def list_tasks(self) -> List[Dict[str, Any]]:
    """
    列出所有任务
    
    Returns:
      任务列表
    """
    return list(self.tasks.values())


class ConnectionManager:
  """
  WebSocket 连接管理器
  负责管理所有活跃的 WebSocket 连接
  """
  
  def __init__(self):
    self.active_connections: List[WebSocket] = []
    
  async def connect(self, websocket: WebSocket):
    """
    接受新的 WebSocket 连接
    
    Args:
      websocket: WebSocket 连接对象
    """
    await websocket.accept()
    self.active_connections.append(websocket)
    
  def disconnect(self, websocket: WebSocket):
    """
    断开 WebSocket 连接
    
    Args:
      websocket: WebSocket 连接对象
    """
    if websocket in self.active_connections:
      self.active_connections.remove(websocket)
    
  async def send_personal_message(self, message: str, websocket: WebSocket):
    """
    发送个人消息
    
    Args:
      message: 消息内容
      websocket: 目标 WebSocket 连接
    """
    await websocket.send_text(message)
    
  async def broadcast(self, message: str):
    """
    广播消息到所有连接
    
    Args:
      message: 消息内容
    """
    for connection in self.active_connections:
      await connection.send_text(message)

