"""
任务查询相关接口
"""
from fastapi import APIRouter, HTTPException
from core.comfyui_client import ComfyUIClient
from core.managers import TaskManager
from core.response import R
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["任务查询"])


def extract_timestamps_from_history(history_data: dict) -> tuple:
  """
  从ComfyUI历史记录中提取时间戳
  
  Args:
    history_data: ComfyUI历史记录数据
    
  Returns:
    (created_at, completed_at) 元组，格式为ISO时间字符串
  """
  created_at = None
  completed_at = None
  
  try:
    status = history_data.get('status', {})
    messages = status.get('messages', [])
    
    for message in messages:
      if len(message) >= 2:
        event_type = message[0]
        event_data = message[1]
        
        # 获取开始时间
        if event_type == 'execution_start' and 'timestamp' in event_data:
          timestamp_ms = event_data['timestamp']
          created_at = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
        
        # 获取完成时间
        elif event_type == 'execution_success' and 'timestamp' in event_data:
          timestamp_ms = event_data['timestamp']
          completed_at = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
  
  except Exception as e:
    logger.warning(f"提取时间戳失败: {e}")
  
  return created_at, completed_at


def check_task_status_from_history(history_data: dict) -> tuple:
  """
  从ComfyUI历史记录中判断任务的真实状态
  
  Args:
    history_data: ComfyUI历史记录数据
    
  Returns:
    (status, error_message) 元组
    status: "completed" 或 "failed"
    error_message: 如果失败，返回错误信息；否则为 None
  """
  try:
    # 1. 检查 status.messages 中是否有错误消息
    status = history_data.get('status', {})
    messages = status.get('messages', [])
    
    has_execution_start = False
    has_execution_success = False
    error_messages = []
    
    for message in messages:
      if len(message) >= 2:
        event_type = message[0]
        event_data = message[1]
        
        if event_type == 'execution_start':
          has_execution_start = True
        elif event_type == 'execution_success':
          has_execution_success = True
        elif event_type == 'execution_error':
          # 提取错误信息
          error_info = event_data.get('exception_message', '')
          if not error_info:
            error_info = event_data.get('node_type', '') + ' 节点执行失败'
          error_messages.append(error_info)
        elif event_type == 'execution_interrupted':
          error_messages.append('任务被中断')
    
    # 如果有错误消息，任务失败
    if error_messages:
      return "failed", '; '.join(error_messages)
    
    # 如果启动了但没有成功消息，可能失败了
    if has_execution_start and not has_execution_success:
      # 进一步检查是否有输出
      if 'outputs' not in history_data or not history_data['outputs']:
        return "failed", "任务执行未完成且无输出"
    
    # 2. 检查 outputs 字段
    if 'outputs' not in history_data or not history_data['outputs']:
      return "failed", "任务未产生任何输出"
    
    outputs = history_data['outputs']
    
    # 3. 检查输出是否有效
    has_valid_output = False
    for node_id, node_output in outputs.items():
      if node_output and isinstance(node_output, dict):
        # 检查是否有图片、视频等实际输出
        if node_output.get('images') or node_output.get('gifs') or node_output.get('videos') or node_output.get('audio'):
          has_valid_output = True
          break
    
    if not has_valid_output:
      return "failed", "任务执行完成但未生成有效输出"
    
    # 4. 一切正常，任务成功完成
    return "completed", None
    
  except Exception as e:
    logger.warning(f"检查任务状态失败: {e}")
    # 出错时默认返回 completed，避免误判
    return "completed", None


def setup_task_routes(comfyui_server: str, task_manager: TaskManager,
                     protocol: str = "http", ws_protocol: str = "ws"):
  """
  设置任务查询路由
  
  Args:
    comfyui_server: ComfyUI 服务器地址
    task_manager: 任务管理器实例
    protocol: HTTP协议
    ws_protocol: WebSocket协议
  """
  
  @router.get("/task/{task_id}")
  async def get_task_status(task_id: str):
    """获取任务状态（统一使用prompt_id）"""
    # 1. 先从本地任务管理器查询
    task = task_manager.get_task(task_id)
    
    if task:
      return R.success(
        data={
          "task_id": task_id,
          "status": task.get("status"),
          "created_at": task.get("created_at"),
          "completed_at": task.get("completed_at"),
          "result": task.get("result")
        },
        message="获取任务状态成功"
      )
    
    # 2. 查询 ComfyUI 队列（正在运行和排队中的任务）
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        queue_data = await client.async_get_queue()
        
      # 检查是否在运行队列中
      if queue_data.get('queue_running'):
        for queue_item in queue_data['queue_running']:
          prompt_id = queue_item[1] if len(queue_item) > 1 else None
          if prompt_id == task_id:
            return R.success(
              data={
                "task_id": task_id,
                "status": "running",
                "created_at": datetime.now().isoformat(),
                "source": "queue",
                "message": "任务正在执行中"
              },
              message="任务正在执行中"
            )
      
      # 检查是否在等待队列中
      if queue_data.get('queue_pending'):
        for queue_item in queue_data['queue_pending']:
          prompt_id = queue_item[1] if len(queue_item) > 1 else None
          if prompt_id == task_id:
            return R.success(
              data={
                "task_id": task_id,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "source": "queue",
                "message": "任务正在排队中"
              },
              message="任务正在排队中"
            )
    except Exception as e:
      logger.warning(f"查询队列失败: {e}")
    
    # 3. 查询 ComfyUI 历史记录（已完成的任务）
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        history = await client.async_get_history(task_id)
        
      if history and task_id in history:
        # 从历史记录构造任务信息
        history_data = history[task_id]
        
        async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
          outputs = client.extract_outputs(history_data)
        
        # 检查任务真实状态
        task_status, error_msg = check_task_status_from_history(history_data)
        
        # 提取时间戳
        created_at, completed_at = extract_timestamps_from_history(history_data)
        
        # 构建响应数据
        response_data = {
          "task_id": task_id,
          "status": task_status,
          "created_at": created_at,
          "completed_at": completed_at if task_status == "completed" else None,
          "source": "history",
          "result": {
            "prompt_id": task_id,
            "status": task_status,
            "outputs": outputs,
            "raw_result": history_data
          }
        }
        
        # 如果任务失败，添加错误信息
        if task_status == "failed":
          response_data["error"] = error_msg or "任务执行失败"
          response_data["failed_at"] = created_at
          response_data["result"]["error"] = error_msg
        
        return R.success(
          data=response_data,
          message="获取任务状态成功"
        )
    except Exception as e:
      logger.error(f"查询历史记录失败: {e}")
    
    # 如果都没找到，返回404
    return R.not_found(message="任务不存在")
  
  @router.get("/tasks")
  async def list_tasks(limit: int = 200, include_history: bool = True):
    """
    列出所有任务（合并本地任务、队列任务和历史记录）
    
    参数:
      limit: 返回的历史记录数量限制（默认200，最大500）
      include_history: 是否包含ComfyUI历史记录
    """
    # 限制最大值，防止性能问题
    limit = min(limit, 500)
    # 获取本地任务
    local_tasks = task_manager.list_tasks()
    local_task_ids = {task['task_id'] for task in local_tasks}
    
    tasks = local_tasks.copy()
    
    # 1. 获取 ComfyUI 队列中的任务（正在运行和等待中的）
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        queue_data = await client.async_get_queue()
        
      # 处理正在运行的任务
      if queue_data.get('queue_running'):
        for queue_item in queue_data['queue_running']:
          prompt_id = queue_item[1] if len(queue_item) > 1 else None
          if prompt_id and prompt_id not in local_task_ids:
            tasks.append({
              "task_id": prompt_id,
              "prompt_id": prompt_id,
              "status": "running",
              "workflow_type": "unknown",
              "created_at": datetime.now().isoformat(),
              "source": "queue"
            })
            local_task_ids.add(prompt_id)
      
      # 处理等待中的任务
      if queue_data.get('queue_pending'):
        for queue_item in queue_data['queue_pending']:
          prompt_id = queue_item[1] if len(queue_item) > 1 else None
          if prompt_id and prompt_id not in local_task_ids:
            tasks.append({
              "task_id": prompt_id,
              "prompt_id": prompt_id,
              "status": "pending",
              "workflow_type": "unknown",
              "created_at": datetime.now().isoformat(),
              "source": "queue"
            })
            local_task_ids.add(prompt_id)
    except Exception as e:
      logger.error(f"获取队列信息失败: {e}")
    
    # 2. 如果需要，从ComfyUI获取历史记录
    if include_history:
      try:
        async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
          history = await client.async_get_history()
          
        # 限制返回数量
        history_items = list(history.items())[:limit]
        
        # 将历史记录转换为任务格式，但排除本地已有的
        for prompt_id, history_data in history_items:
          if prompt_id not in local_task_ids:
            async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
              outputs = client.extract_outputs(history_data)
            
            # 检查任务真实状态
            task_status, error_msg = check_task_status_from_history(history_data)
            
            # 判断任务类型
            has_images = any(
              output.get('images') 
              for output in outputs.values()
              if isinstance(output, dict)
            )
            has_videos = any(
              output.get('gifs')
              for output in outputs.values()
              if isinstance(output, dict)
            )
            
            task_type = "video" if has_videos else "image" if has_images else "unknown"
            
            # 提取时间戳
            created_at, completed_at = extract_timestamps_from_history(history_data)
            
            # 构建任务数据
            task_data = {
              "task_id": prompt_id,
              "prompt_id": prompt_id,
              "status": task_status,
              "workflow_type": task_type,
              "created_at": created_at,
              "completed_at": completed_at if task_status == "completed" else None,
              "source": "history"  # 标记为历史记录
            }
            
            # 如果失败，添加错误信息
            if task_status == "failed" and error_msg:
              task_data["error"] = error_msg
              task_data["failed_at"] = created_at  # 使用创建时间作为失败时间
            
            tasks.append(task_data)
      except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
    
    return R.success(
      data={
        "total": len(tasks),
        "tasks": tasks
      },
      message="获取任务列表成功"
    )
  
  @router.get("/history")
  async def get_history(limit: int = 200):
    """
    获取历史记录列表
    
    参数:
      limit: 返回的历史记录数量限制（默认200，最大500）
    """
    # 限制最大值
    limit = min(limit, 500)
    
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        history = await client.async_get_history()
        
      # 限制返回数量
      items = list(history.items())[:limit]
      return R.success(
        data={
          "total": len(history),
          "limit": limit,
          "history": dict(items)
        },
        message="获取历史记录成功"
      )
    except Exception as e:
      return R.server_error(message=f"获取历史记录失败: {str(e)}")
  
  @router.get("/history/{prompt_id}")
  async def get_history_by_id(prompt_id: str):
    """获取指定prompt_id的历史记录"""
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        history = await client.async_get_history(prompt_id)
        
      if not history or prompt_id not in history:
        return R.not_found(message=f"未找到历史记录: {prompt_id}")
      
      return R.success(
        data={
          "prompt_id": prompt_id,
          "history": history[prompt_id]
        },
        message="获取历史记录成功"
      )
    except Exception as e:
      logger.error(f"获取历史记录失败: {e}")
      return R.server_error(message=f"获取历史记录失败: {str(e)}")
  
  return router

