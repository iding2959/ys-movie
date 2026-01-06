"""
ComfyUI API客户端封装
提供与ComfyUI服务器交互的通用接口

使用方式:
  # 同步调用
  client = ComfyUIClient("127.0.0.1:8188")
  result = client.submit_and_wait(workflow)
  
  # 异步调用(推荐 - 自动管理资源)
  async with ComfyUIClient("127.0.0.1:8188") as client:
      result = await client.async_submit_and_wait(workflow)
  
  # 批量异步操作(复用 session，性能更好)
  async with ComfyUIClient() as client:
      tasks = [
          client.async_queue_prompt(workflow1),
          client.async_queue_prompt(workflow2),
      ]
      results = await asyncio.gather(*tasks)

最佳实践:
  - 异步操作时使用 async context manager，可复用 HTTP session
  - 避免在循环中创建多个 client 实例
  - 长时间运行的应用建议使用 async with 模式
"""
import json
import websocket
import uuid
import urllib.request
import urllib.parse
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import base64

logger = logging.getLogger(__name__)


class ComfyUIClient:
  """
  ComfyUI API客户端
  
  支持同步和异步两种使用方式:
  1. 同步: client = ComfyUIClient(); client.queue_prompt(...)
  2. 异步(推荐): async with ComfyUIClient() as client: await client.async_queue_prompt(...)
  
  使用 async context manager 可以复用 HTTP session，提升性能
  """
  
  def __init__(self, server_address: str = "127.0.0.1:8188", 
               protocol: str = "http", ws_protocol: str = "ws"):
    """
    初始化ComfyUI客户端
    
    Args:
      server_address: ComfyUI服务器地址
      protocol: HTTP协议 (http 或 https)
      ws_protocol: WebSocket协议 (ws 或 wss)
    """
    self.server_address = server_address
    self.protocol = protocol
    self.ws_protocol = ws_protocol
    self.client_id = str(uuid.uuid4())
    self.ws = None
    self._session: Optional[aiohttp.ClientSession] = None
    self._owns_session = False
    
  @property
  def api_url(self) -> str:
    """获取API基础URL"""
    return f"{self.protocol}://{self.server_address}"
    
  @property
  def ws_url(self) -> str:
    """获取WebSocket URL"""
    return f"{self.ws_protocol}://{self.server_address}/ws?clientId={self.client_id}"
  
  async def __aenter__(self):
    """
    异步上下文管理器入口
    创建并复用 aiohttp session 以提升性能
    """
    if self._session is None:
      self._session = aiohttp.ClientSession()
      self._owns_session = True
    return self
  
  async def __aexit__(self, exc_type, exc_val, exc_tb):
    """
    异步上下文管理器出口
    正确关闭 session 并等待连接清理
    """
    if self._owns_session and self._session:
      await self._session.close()
      # Graceful shutdown: 等待底层连接完全关闭
      await asyncio.sleep(0.25)
      self._session = None
      self._owns_session = False
    
    # 清理 WebSocket 连接
    if self.ws:
      try:
        self.ws.close()
      except Exception as e:
        logger.warning(f"关闭WebSocket连接时出错: {e}")
      finally:
        self.ws = None
    
    return False
  
  def _get_session(self) -> aiohttp.ClientSession:
    """
    获取或创建 aiohttp session
    内部方法，用于异步操作
    """
    if self._session is None:
      # 如果没有通过 context manager 使用，创建临时 session
      # 注意：这种方式不会被自动清理，仅用于向后兼容
      self._session = aiohttp.ClientSession()
      self._owns_session = True
      logger.warning(
        "建议使用 'async with ComfyUIClient() as client' 模式以正确管理资源"
      )
    return self._session
    
  def connect_websocket(self) -> websocket.WebSocket:
    """
    连接WebSocket（同步方式）
    注意：建议仅在同步方法中使用
    """
    if self.ws is None:
      self.ws = websocket.WebSocket()
      self.ws.connect(self.ws_url)
    return self.ws
    
  def disconnect_websocket(self):
    """断开WebSocket连接"""
    if self.ws:
      try:
        self.ws.close()
      except Exception as e:
        logger.warning(f"关闭WebSocket连接时出错: {e}")
      finally:
        self.ws = None
      
  def queue_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
    """
    提交工作流到队列
    
    Args:
      prompt: 工作流JSON数据
      
    Returns:
      包含prompt_id的响应
    """
    p = {"prompt": prompt, "client_id": self.client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"{self.api_url}/prompt", data=data)
    req.add_header('Content-Type', 'application/json')
    
    try:
      response = urllib.request.urlopen(req)
      return json.loads(response.read())
    except Exception as e:
      logger.error(f"提交任务失败: {e}")
      raise
      
  async def async_queue_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
    """
    异步提交工作流到队列
    
    Args:
      prompt: 工作流JSON数据
      
    Returns:
      包含prompt_id的响应
    """
    session = self._get_session()
    p = {"prompt": prompt, "client_id": self.client_id}
    
    async with session.post(
      f"{self.api_url}/prompt",
      json=p
    ) as response:
      return await response.json()
      
  def get_history(self, prompt_id: str = None) -> Dict[str, Any]:
    """
    获取历史记录
    
    Args:
      prompt_id: 可选的任务ID，不提供则返回所有历史
      
    Returns:
      历史记录数据
    """
    if prompt_id:
      url = f"{self.api_url}/history/{prompt_id}"
    else:
      url = f"{self.api_url}/history"
      
    try:
      with urllib.request.urlopen(url) as response:
        return json.loads(response.read())
    except Exception as e:
      logger.error(f"获取历史失败: {e}")
      raise
      
  async def async_get_history(self, prompt_id: str = None) -> Dict[str, Any]:
    """
    异步获取历史记录
    
    Args:
      prompt_id: 可选的任务ID，不提供则返回所有历史
      
    Returns:
      历史记录数据
    """
    session = self._get_session()
    
    if prompt_id:
      url = f"{self.api_url}/history/{prompt_id}"
    else:
      url = f"{self.api_url}/history"
      
    async with session.get(url) as response:
      return await response.json()
      
  def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
    """
    获取图片数据
    
    Args:
      filename: 文件名
      subfolder: 子文件夹
      folder_type: 文件夹类型 (output/input/temp)
      
    Returns:
      图片二进制数据
    """
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    
    try:
      with urllib.request.urlopen(f"{self.api_url}/view?{url_values}") as response:
        return response.read()
    except Exception as e:
      logger.error(f"获取图片失败: {e}")
      raise
      
  async def async_get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
    """
    异步获取图片数据
    
    Args:
      filename: 文件名
      subfolder: 子文件夹
      folder_type: 文件夹类型 (output/input/temp)
      
    Returns:
      图片二进制数据
    """
    session = self._get_session()
    params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    
    async with session.get(f"{self.api_url}/view", params=params) as response:
      return await response.read()
  
  async def async_upload_image(self, image_data: bytes, filename: str, 
                               subfolder: str = "", overwrite: bool = False) -> Dict[str, Any]:
    """
    异步上传图片到ComfyUI服务器
    
    默认上传到ComfyUI的input文件夹，LoadImage节点会从此文件夹读取图片
    
    Args:
      image_data: 图片二进制数据
      filename: 文件名
      subfolder: 子文件夹（可选，相对于input文件夹）
      overwrite: 是否覆盖已存在的文件
      
    Returns:
      上传结果，包含文件名和路径信息
      返回格式示例: {"name": "filename.png", "subfolder": "", "type": "input"}
    """
    session = self._get_session()
    
    # 创建multipart/form-data请求
    form = aiohttp.FormData()
    form.add_field('image', image_data, filename=filename, 
                   content_type='image/png')
    
    if subfolder:
      form.add_field('subfolder', subfolder)
    
    if overwrite:
      form.add_field('overwrite', 'true')
    
    async with session.post(f"{self.api_url}/upload/image", data=form) as response:
      if response.status != 200:
        error_text = await response.text()
        raise Exception(f"上传图片失败: {error_text}")
      return await response.json()
  
  async def async_upload_video(self, video_data: bytes, filename: str, 
                               subfolder: str = "", overwrite: bool = False) -> Dict[str, Any]:
    """
    异步上传视频到ComfyUI服务器
    
    上传到ComfyUI的input文件夹，VHS_LoadVideo节点会从此文件夹读取视频
    
    Args:
      video_data: 视频二进制数据
      filename: 文件名
      subfolder: 子文件夹（可选，相对于input文件夹）
      overwrite: 是否覆盖已存在的文件
      
    Returns:
      上传结果，包含文件名和路径信息
    """
    session = self._get_session()
    
    # 创建multipart/form-data请求
    form = aiohttp.FormData()
    form.add_field('image', video_data, filename=filename, 
                   content_type='video/mp4')
    
    if subfolder:
      form.add_field('subfolder', subfolder)
    
    if overwrite:
      form.add_field('overwrite', 'true')
    
    async with session.post(f"{self.api_url}/upload/image", data=form) as response:
      if response.status != 200:
        error_text = await response.text()
        raise Exception(f"上传视频失败: {error_text}")
      return await response.json()
      
  def get_queue(self) -> Dict[str, Any]:
    """获取当前队列状态"""
    try:
      with urllib.request.urlopen(f"{self.api_url}/queue") as response:
        return json.loads(response.read())
    except Exception as e:
      logger.error(f"获取队列状态失败: {e}")
      raise
      
  async def async_get_queue(self) -> Dict[str, Any]:
    """异步获取队列状态"""
    session = self._get_session()
    
    async with session.get(f"{self.api_url}/queue") as response:
      return await response.json()
      
  def get_system_stats(self) -> Dict[str, Any]:
    """获取系统状态"""
    try:
      with urllib.request.urlopen(f"{self.api_url}/system_stats") as response:
        return json.loads(response.read())
    except Exception as e:
      logger.error(f"获取系统状态失败: {e}")
      raise
      
  async def async_get_system_stats(self) -> Dict[str, Any]:
    """异步获取系统状态"""
    session = self._get_session()
    
    async with session.get(f"{self.api_url}/system_stats") as response:
      return await response.json()
      
  def get_object_info(self) -> Dict[str, Any]:
    """获取所有节点信息"""
    try:
      with urllib.request.urlopen(f"{self.api_url}/object_info") as response:
        return json.loads(response.read())
    except Exception as e:
      logger.error(f"获取节点信息失败: {e}")
      raise
      
  async def async_get_object_info(self) -> Dict[str, Any]:
    """异步获取节点信息"""
    session = self._get_session()
    
    async with session.get(f"{self.api_url}/object_info") as response:
      return await response.json()
      
  def interrupt(self, prompt_id: str = None) -> bool:
    """
    中断任务执行
    
    Args:
      prompt_id: 可选的任务ID，不提供则中断所有任务
      
    Returns:
      是否成功
    """
    data = {}
    if prompt_id:
      data["prompt_id"] = prompt_id
      
    req = urllib.request.Request(
      f"{self.api_url}/interrupt",
      data=json.dumps(data).encode('utf-8')
    )
    req.add_header('Content-Type', 'application/json')
    
    try:
      response = urllib.request.urlopen(req)
      return response.status == 200
    except Exception as e:
      logger.error(f"中断任务失败: {e}")
      return False
      
  def clear_queue(self) -> bool:
    """清空队列"""
    data = {"clear": True}
    req = urllib.request.Request(
      f"{self.api_url}/queue",
      data=json.dumps(data).encode('utf-8')
    )
    req.add_header('Content-Type', 'application/json')
    
    try:
      response = urllib.request.urlopen(req)
      return response.status == 200
    except Exception as e:
      logger.error(f"清空队列失败: {e}")
      return False
      
  def wait_for_completion(self, prompt_id: str, timeout: int = 600) -> Dict[str, Any]:
    """
    等待任务完成（增强版）
    
    支持的WebSocket消息类型：
    - execution_start: 任务开始执行
    - execution_error: 执行错误（立即抛出异常）
    - execution_success: 任务成功完成
    - execution_interrupted: 任务被中断
    - executing: 节点执行状态（兼容旧逻辑）
    - progress: 进度更新
    - executed: 节点执行完成
    - execution_cached: 使用缓存结果
    - status: 系统状态更新
    
    Args:
      prompt_id: 任务ID
      timeout: 超时时间（秒）
      
    Returns:
      完成的任务结果
      
    Raises:
      TimeoutError: 任务执行超时
      RuntimeError: 任务执行失败
      InterruptedError: 任务被中断
    """
    ws = self.connect_websocket()
    start_time = datetime.now()
    
    logger.info(f"开始监听任务 {prompt_id} 的执行状态")
    
    while True:
      # 超时检查
      if (datetime.now() - start_time).seconds > timeout:
        raise TimeoutError(f"任务 {prompt_id} 执行超时（{timeout}秒）")
        
      try:
        out = ws.recv()
        if isinstance(out, str):
          message = json.loads(out)
          msg_type = message.get('type')
          data = message.get('data', {})
          
          # 只处理与当前任务相关的消息
          msg_prompt_id = data.get('prompt_id')
          
          # 处理不同类型的消息
          if msg_type == 'execution_start':
            if msg_prompt_id == prompt_id:
              logger.info(f"✓ 任务 {prompt_id} 开始执行")
          
          elif msg_type == 'execution_error':
            if msg_prompt_id == prompt_id:
              # 立即抛出异常，包含详细错误信息
              error_msg = data.get('exception_message', '未知错误')
              node_id = data.get('node_id', '未知节点')
              node_type = data.get('node_type', '未知类型')
              exception_type = data.get('exception_type', 'Exception')
              
              logger.error(f"✗ 任务 {prompt_id} 执行失败")
              logger.error(f"  节点: {node_id} ({node_type})")
              logger.error(f"  错误: {error_msg}")
              
              raise RuntimeError(
                f"任务执行失败 - 节点: {node_id} ({node_type}), "
                f"错误类型: {exception_type}, 错误信息: {error_msg}"
              )
          
          elif msg_type == 'execution_success':
            if msg_prompt_id == prompt_id:
              logger.info(f"✓ 任务 {prompt_id} 成功完成")
              break
          
          elif msg_type == 'execution_interrupted':
            if msg_prompt_id == prompt_id:
              node_id = data.get('node_id', '未知节点')
              node_type = data.get('node_type', '未知类型')
              logger.warning(f"✗ 任务 {prompt_id} 被中断在节点 {node_id}")
              raise InterruptedError(
                f"任务 {prompt_id} 被中断 - 节点: {node_id} ({node_type})"
              )
          
          elif msg_type == 'execution_cached':
            if msg_prompt_id == prompt_id:
              nodes = data.get('nodes', [])
              logger.info(f"⚡ 任务 {prompt_id} 使用了缓存结果 ({len(nodes)} 个节点)")
          
          elif msg_type == 'executing':
            # 保留原有逻辑（向后兼容）
            node = data.get('node')
            if msg_prompt_id == prompt_id:
              if node is None:
                # 任务执行完成的旧式信号
                logger.info(f"✓ 任务 {prompt_id} 完成（通过executing消息）")
                break
              else:
                logger.debug(f"→ 正在执行节点: {node}")
          
          elif msg_type == 'progress':
            if msg_prompt_id == prompt_id:
              value = data.get('value', 0)
              max_value = data.get('max', 100)
              node = data.get('node')
              percentage = int(value / max_value * 100) if max_value > 0 else 0
              logger.info(f"⟳ 任务进度: {value}/{max_value} ({percentage}%) - 节点: {node}")
          
          elif msg_type == 'executed':
            node = data.get('node')
            if msg_prompt_id == prompt_id and node:
              output = data.get('output', {})
              logger.debug(f"✓ 节点 {node} 执行完成，输出: {list(output.keys())}")
          
          elif msg_type == 'status':
            # 系统状态更新，通常不针对特定任务
            exec_info = data.get('status', {}).get('exec_info', {})
            queue_remaining = exec_info.get('queue_remaining', 0)
            logger.debug(f"系统状态: 队列剩余 {queue_remaining} 个任务")
      
      except json.JSONDecodeError:
        logger.warning("接收到无效的JSON消息")
        continue
      except Exception as e:
        # 重新抛出预期的异常
        if isinstance(e, (TimeoutError, RuntimeError, InterruptedError)):
          raise
        # 其他异常只记录警告，继续监听
        logger.warning(f"WebSocket接收消息时出错: {e}")
        continue
        
    # 获取执行结果
    history = self.get_history(prompt_id)
    if prompt_id in history:
      return history[prompt_id]
    else:
      raise ValueError(f"未找到任务 {prompt_id} 的执行结果")
      
  async def async_wait_for_completion(self, prompt_id: str, timeout: int = 600) -> Dict[str, Any]:
    """异步等待任务完成"""
    start_time = datetime.now()
    
    while True:
      if (datetime.now() - start_time).seconds > timeout:
        raise TimeoutError(f"任务 {prompt_id} 执行超时")
        
      # 检查历史记录
      history = await self.async_get_history(prompt_id)
      if prompt_id in history and history[prompt_id].get('outputs'):
        return history[prompt_id]
        
      # 短暂等待后重试
      await asyncio.sleep(1)
      
  def extract_outputs(self, history_data: Dict[str, Any]) -> Dict[str, List[Any]]:
    """
    从历史数据中提取输出结果
    
    Args:
      history_data: 历史记录数据
      
    Returns:
      包含各类输出的字典
    """
    outputs = {
      "images": [],
      "videos": [],
      "texts": [],
      "other": []
    }
    
    if 'outputs' not in history_data:
      return outputs
      
    for node_id, node_output in history_data['outputs'].items():
      # 提取图片
      if 'images' in node_output:
        for image in node_output['images']:
          outputs["images"].append({
            "node_id": node_id,
            "filename": image['filename'],
            "subfolder": image.get('subfolder', ''),
            "type": image.get('type', 'output')
          })
          
      # 提取视频
      if 'videos' in node_output:
        for video in node_output['videos']:
          outputs["videos"].append({
            "node_id": node_id,
            "filename": video['filename'],
            "subfolder": video.get('subfolder', ''),
            "type": video.get('type', 'output')
          })
          
      # 提取文本
      if 'text' in node_output:
        outputs["texts"].append({
          "node_id": node_id,
          "content": node_output['text']
        })
        
      # 其他输出
      for key in node_output:
        if key not in ['images', 'videos', 'text']:
          outputs["other"].append({
            "node_id": node_id,
            "type": key,
            "data": node_output[key]
          })
          
    return outputs
    
  def submit_and_wait(self, workflow: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
    """
    提交工作流并等待完成
    
    Args:
      workflow: 工作流JSON数据
      timeout: 超时时间
      
    Returns:
      执行结果
    """
    # 提交任务
    response = self.queue_prompt(workflow)
    prompt_id = response['prompt_id']
    
    # 等待完成
    result = self.wait_for_completion(prompt_id, timeout)
    
    # 提取输出
    outputs = self.extract_outputs(result)
    
    return {
      "prompt_id": prompt_id,
      "status": "completed",
      "outputs": outputs,
      "raw_result": result
    }
    
  async def async_submit_and_wait(self, workflow: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
    """异步提交工作流并等待完成"""
    try:
      # 提交任务
      response = await self.async_queue_prompt(workflow)
      
      # 验证响应结构
      if not response or 'prompt_id' not in response:
        logger.error(f"无效的ComfyUI响应: {response}")
        raise ValueError(f"ComfyUI响应中缺少prompt_id字段: {response}")
      
      prompt_id = response['prompt_id']
      logger.info(f"任务已提交，prompt_id: {prompt_id}")
      
      # 等待完成
      result = await self.async_wait_for_completion(prompt_id, timeout)
      
      # 提取输出
      outputs = self.extract_outputs(result)
      
      return {
        "prompt_id": prompt_id,
        "status": "completed",
        "outputs": outputs,
        "raw_result": result
      }
    except Exception as e:
      logger.error(f"async_submit_and_wait执行出错: {e}")
      raise
