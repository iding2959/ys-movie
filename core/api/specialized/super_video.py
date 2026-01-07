"""
SuperVideo 视频放大 API
支持视频上传和模型选择的视频超分辨率处理
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from core.comfyui_client import ComfyUIClient
from core.models import TaskResponse
from core.managers import TaskManager, ConnectionManager
from core.response import R, ResponseModel
from core.utils import generate_seed
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from pathlib import Path
import subprocess
import json
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/super_video", tags=["视频放大"])


class SuperVideoRequest(BaseModel):
  """SuperVideo 视频放大请求"""
  task_name: str = Field(..., description="任务名称")
  model_name: str = Field(
    default="FlashVSR-v1.1",
    description="放大模型，当前仅支持 FlashVSR-v1.1"
  )
  video_filename: str = Field(..., description="已上传视频文件名")
  workflow_key: Optional[str] = Field(
    default="flash_vsr",
    description="工作流选择：flash_vsr（当前），预留 seedvr2"
  )


def apply_workflow_updates(workflow: dict, updates: list):
  """
  应用工作流的节点参数更新
  
  Args:
    workflow: 工作流配置字典
    updates: 更新列表，元素为 (node_id, path, value)
  """
  for node_id, path, value in updates:
    node = workflow.get(node_id)
    if not node:
      continue
    
    target = node
    for index, key in enumerate(path):
      if key not in target:
        target = None
        break
      
      if index == len(path) - 1:
        target[key] = value
      else:
        target = target[key]
    
    if target is None:
      logger.warning(f"节点 {node_id} 缺少路径 {'.'.join(path)}，已跳过更新")


def resolve_video_path(video_filename: str) -> Optional[Path]:
  """
  解析视频在本地的可能路径（用于读取分辨率）
  """
  candidates = [
    Path("uploads") / video_filename,
    Path("input") / video_filename,
    Path("inputs") / video_filename
  ]
  for path in candidates:
    if path.exists():
      return path
  return None


def get_video_height(video_path: Path) -> Optional[int]:
  """
  使用ffprobe获取视频高度，失败时返回None
  """
  try:
    result = subprocess.run(
      [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=height",
        "-of",
        "json",
        str(video_path)
      ],
      check=True,
      capture_output=True,
      text=True
    )
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    if streams:
      return streams[0].get("height")
  except Exception as e:
    logger.warning(f"获取视频分辨率失败: {e}")
  return None


def calculate_seedvr2_scale(video_filename: str) -> float:
  """
  根据视频高度决定缩放比例：
  - 高度>480：缩放到480p
  - 否则：保持1.0
  """
  video_path = resolve_video_path(video_filename)
  if not video_path:
    logger.warning("未找到视频本地文件，默认不缩放")
    return 1.0
  
  height = get_video_height(video_path)
  if not height:
    logger.warning("无法获取视频高度，默认不缩放")
    return 1.0
  
  if height > 480:
    return round(480 / height, 4)
  return 1.0


def get_model_prefix(model_name: str) -> str:
  """
  根据模型名称获取文件前缀
  
  Args:
    model_name: 模型名称
  
  Returns:
    文件前缀（如 "FlashVSR" 或 "SeedVR2"）
  """
  model_name_lower = model_name.lower()
  if "seedvr2" in model_name_lower or "seedvr" in model_name_lower:
    return "SeedVR2"
  elif "flashvsr" in model_name_lower or "flash" in model_name_lower:
    return "FlashVSR"
  else:
    # 默认使用 FlashVSR
    return "FlashVSR"


def resolve_workflow_config(
  data: SuperVideoRequest,
  workflow_dir: Path,
  safe_task_name: str
):
  """
  根据请求参数解析工作流配置，便于后续扩展（如 seedvr2）
  
  Args:
    data: 用户请求数据
    workflow_dir: 工作流目录
    safe_task_name: 安全的任务名称前缀
  
  Returns:
    包含文件路径、类型名称、任务类型键和更新列表的配置
  """
  def flash_vsr_updates(req: SuperVideoRequest):
    seed = generate_seed()
    # 根据模型名称动态获取前缀
    prefix = get_model_prefix(req.model_name)
    return [
      ("4", ["inputs", "video"], req.video_filename),
      ("6", ["inputs", "filename_prefix"], f"{prefix}_{safe_task_name}"),
      ("1", ["inputs", "seed"], seed)
    ]
  
  def seedvr2_updates(req: SuperVideoRequest):
    seed = generate_seed()
    scale_by = calculate_seedvr2_scale(req.video_filename)
    # 根据模型名称动态获取前缀
    prefix = get_model_prefix(req.model_name)
    return [
      ("19", ["inputs", "video"], req.video_filename),
      ("9", ["inputs", "scale_by"], scale_by),
      ("14", ["inputs", "seed"], seed),
      ("10", ["inputs", "filename_prefix"], f"{prefix}_{safe_task_name}")
    ]
  
  workflow_profiles = {
    "flash_vsr": {
      "file": "FlashVSR1.1.json",
      "type_name": "FlashVSR v1.1",
      "workflow_type": "flash_vsr",
      "update_builder": flash_vsr_updates
    },
    "seedvr2": {
      "file": "SeedVR2.json",
      "type_name": "SeedVR2",
      "workflow_type": "seedvr2",
      "update_builder": seedvr2_updates
    },
  }
  
  profile = workflow_profiles.get(data.workflow_key or "flash_vsr")
  if not profile:
    raise HTTPException(
      status_code=400,
      detail=f"不支持的工作流: {data.workflow_key}"
    )
  return {
    "file_path": workflow_dir / profile["file"],
    "type_name": profile["type_name"],
    "workflow_type": profile["workflow_type"],
    "updates": profile["update_builder"](data)
  }



def setup_super_video_routes(
  comfyui_server: str,
  task_manager: TaskManager,
  connection_manager: ConnectionManager,
  workflow_dir: Path,
  protocol: str = "http",
  ws_protocol: str = "ws"
):
  """
  设置SuperVideo路由
  
  Args:
    comfyui_server: ComfyUI 服务器地址
    task_manager: 任务管理器实例
    connection_manager: WebSocket 连接管理器实例
    workflow_dir: 工作流文件目录
  """
  
  async def wait_for_completion(prompt_id: str, timeout: int):
    """等待任务完成（后台任务）"""
    try:
      task_manager.update_task(prompt_id, {"status": "running"})
      
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "running"
      }))
      
      logger.info(f"开始等待SuperVideo任务完成: {prompt_id}")
      
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        result = await client.async_wait_for_completion(prompt_id, timeout)
        outputs = client.extract_outputs(result)
        
        final_result = {
          "prompt_id": prompt_id,
          "status": "completed",
          "outputs": outputs,
          "raw_result": result
        }
      
      task_manager.update_task(prompt_id, {
        "status": "completed",
        "result": final_result,
        "completed_at": datetime.now().isoformat()
      })
      
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "completed",
        "result": final_result
      }))
      
      logger.info(f"SuperVideo任务 {prompt_id} 完成")
      
    except Exception as e:
      logger.error(f"SuperVideo任务 {prompt_id} 失败: {e}")
      logger.error(f"错误堆栈: {traceback.format_exc()}")
      
      error_msg = str(e)
      task_manager.update_task(prompt_id, {
        "status": "failed",
        "error": error_msg,
        "failed_at": datetime.now().isoformat()
      })
      
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "failed",
        "error": error_msg
      }))
  
  @router.post("/submit", response_model=ResponseModel)
  async def submit_super_video(
    data: SuperVideoRequest,
    background_tasks: BackgroundTasks
  ):
    """
    提交SuperVideo视频处理任务
    
    ## 功能说明
    对上传的视频进行处理，支持多种处理选项
    
    ## 参数说明
    - **task_name**: 任务名称（必填）
    - **model_name**: 放大模型选择（当前支持 FlashVSR-v1.1）
    - **video_filename**: 已上传的视频文件名（通过 /upload 接口获取）
    - **workflow_key**: 工作流选择
      - `flash_vsr`（默认）
      - `seedvr2`（根据视频高度>480自动缩放到480p，否则保持1.0）
    
    ## 使用流程
    1. 先调用 `/upload` 接口上传视频文件
    2. 获取返回的 filename
    3. 使用该 filename 调用此接口提交任务
    
    ## 返回信息
    返回任务ID，可通过WebSocket或任务查询接口获取处理结果
    """
    try:
      # 使用统一配置解析，便于扩展新的工作流（如 seedvr2）
      safe_task_name = "".join(
        c for c in data.task_name if c.isalnum() or c in (' ', '-', '_')
      ).strip()
      workflow_config = resolve_workflow_config(data, workflow_dir, safe_task_name)
      workflow_file = workflow_config["file_path"]
      workflow_type_name = workflow_config["type_name"]
      
      if not workflow_file.exists():
        raise HTTPException(
          status_code=404,
          detail=f"工作流文件不存在，请确保 workflows/{workflow_file.name} 存在"
        )
      
      with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
      
      # 根据配置批量更新节点参数
      apply_workflow_updates(workflow, workflow_config["updates"])
      
      # 提交到ComfyUI
      logger.info(f"准备提交工作流到ComfyUI: {workflow_file.name}")
      logger.debug(f"工作流内容: {json.dumps(workflow, indent=2, ensure_ascii=False)}")
      
      try:
        async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
          response = await client.async_queue_prompt(workflow)
        
        logger.info(f"ComfyUI响应: {response}")
        
        if not response:
          raise HTTPException(
            status_code=500,
            detail="ComfyUI提交失败，响应为空"
          )
        
        if 'prompt_id' not in response:
          error_detail = response.get('error', '未知错误')
          node_errors = response.get('node_errors', {})
          
          error_msg = f"ComfyUI提交失败: {error_detail}"
          if node_errors:
            error_msg += f", 节点错误: {json.dumps(node_errors, ensure_ascii=False)}"
          
          logger.error(f"ComfyUI提交失败，响应内容: {response}")
          raise HTTPException(
            status_code=500,
            detail=error_msg
          )
        
        prompt_id = response['prompt_id']
      except HTTPException:
        raise
      except Exception as e:
        logger.error(f"ComfyUI提交异常: {e}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        raise HTTPException(
          status_code=500,
          detail=f"ComfyUI提交异常: {str(e)}"
        )
      
      # 添加任务到管理器
      workflow_type_key = workflow_config["workflow_type"]
      task_manager.add_task(prompt_id, {
        "task_id": prompt_id,
        "prompt_id": prompt_id,
        "workflow_type": workflow_type_key,
        "task_name": data.task_name,
        "params": {
          "task_name": data.task_name,
          "model_name": data.model_name,
          "video_filename": data.video_filename,
          "workflow": workflow_type_name
        }
      })
      
      # 在后台等待任务完成（视频处理可能需要较长时间）
      background_tasks.add_task(wait_for_completion, prompt_id, 1800)
      
      logger.info(f"📝 {workflow_type_name}任务已提交: {prompt_id}")
      logger.info(f"   任务名称: {data.task_name}")
      logger.info(f"   视频文件: {data.video_filename}")
      logger.info(f"   放大模型: {data.model_name}")
      logger.info(f"   工作流类型: {workflow_type_name}")
      
      return R.success(
        data={
          "task_id": prompt_id,
          "status": "submitted",
          "task_name": data.task_name,
          "model_name": data.model_name,
          "video_filename": data.video_filename
        },
        message=f"任务已提交: {data.task_name}"
      )
      
    except Exception as e:
      logger.error(f"SuperVideo任务提交失败: {e}")
      logger.error(f"错误堆栈: {traceback.format_exc()}")
      return R.server_error(message=f"任务提交失败: {str(e)}")
  
  return router

