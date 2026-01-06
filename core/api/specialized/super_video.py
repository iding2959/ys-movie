"""
SuperVideo 视频放大 API
支持视频上传和模型选择的视频超分辨率处理
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from core.comfyui_client import ComfyUIClient
from core.models import TaskResponse
from core.managers import TaskManager, ConnectionManager
from core.response import R, ResponseModel
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from pathlib import Path
import json
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/super_video", tags=["视频放大"])


class SuperVideoRequest(BaseModel):
  """SuperVideo 视频放大请求"""
  task_name: str = Field(..., description="任务名称")
  model_name: str = Field(
    default="RealESRGAN_x4plus.pth",
    description="放大模型：RealESRGAN_x4plus.pth、4x-UltraSharpV2.safetensors 或 FlashVSR"
  )
  video_filename: str = Field(..., description="已上传视频文件名")
  processing_option: Optional[str] = Field(
    default="super_resolution",
    description="处理选项：denoise、super_resolution、portrait_enhancement"
  )


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
    - **model_name**: 放大模型选择
      - `RealESRGAN_x4plus.pth`: 标准RealESRGAN模型，平衡质量和速度
      - `4x-UltraSharpV2.safetensors`: Ultra Sharp V2模型，更锐利的细节
      - `FlashVSR`: FlashVSR超快速视频超分辨率模型，采用扩散模型技术
    - **video_filename**: 已上传的视频文件名（通过 /upload 接口获取）
    - **processing_option**: 处理选项（可选，默认为super_resolution）
      - `denoise`: 降噪处理
      - `super_resolution`: 超分辨率/去模糊
      - `portrait_enhancement`: 人物增强（使用GFPGAN Face Enhancer）
    
    ## 使用流程
    1. 先调用 `/upload` 接口上传视频文件
    2. 获取返回的 filename
    3. 使用该 filename 调用此接口提交任务
    
    ## 返回信息
    返回任务ID，可通过WebSocket或任务查询接口获取处理结果
    """
    try:
      # 根据处理选项和模型名称选择工作流
      if data.processing_option == "portrait_enhancement":
        # 人物增强工作流
        workflow_file = workflow_dir / "faceEnch.json"
        workflow_type_name = "人物增强"
      elif data.model_name == "FlashVSR":
        # FlashVSR 工作流
        workflow_file = workflow_dir / "FlashVSR.json"
        workflow_type_name = "FlashVSR"
      else:
        # 默认超分辨率工作流
        workflow_file = workflow_dir / "SuperVideo.json"
        workflow_type_name = "超分辨率"
      
      if not workflow_file.exists():
        raise HTTPException(
          status_code=404,
          detail=f"工作流文件不存在，请确保 workflows/{workflow_file.name} 存在"
        )
      
      with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
      
      # 使用任务名称作为文件名前缀
      safe_task_name = "".join(c for c in data.task_name if c.isalnum() or c in (' ', '-', '_')).strip()
      
      # 根据不同工作流更新参数
      if data.processing_option == "portrait_enhancement":
        # faceEnch.json 工作流参数设置
        # 节点16: VHS_LoadVideoFFmpeg - 加载视频
        if "16" in workflow and "inputs" in workflow["16"]:
          workflow["16"]["inputs"]["video"] = data.video_filename
        
        # 节点5: VHS_VideoCombine - 设置输出文件名前缀
        if "5" in workflow and "inputs" in workflow["5"]:
          workflow["5"]["inputs"]["filename_prefix"] = f"FaceEnhanced_{safe_task_name}"
      elif data.model_name == "FlashVSR":
        # FlashVSR工作流参数设置
        # 节点12: VHS_LoadVideo - 加载视频
        if "12" in workflow and "inputs" in workflow["12"]:
          workflow["12"]["inputs"]["video"] = data.video_filename
        
        # 节点14: VHS_VideoCombine - 设置输出文件名前缀
        if "14" in workflow and "inputs" in workflow["14"]:
          workflow["14"]["inputs"]["filename_prefix"] = f"FlashVSR_{safe_task_name}"
      else:
        # SuperVideo工作流参数设置（RealESRGAN/UltraSharp）
        # 节点1: VHS_LoadVideo - 加载视频
        if "1" in workflow and "inputs" in workflow["1"]:
          workflow["1"]["inputs"]["video"] = data.video_filename
        
        # 节点3: UpscaleModelLoader - 加载放大模型
        if "3" in workflow and "inputs" in workflow["3"]:
          workflow["3"]["inputs"]["model_name"] = data.model_name
        
        # 节点5: VHS_VideoCombine - 设置输出文件名前缀
        if "5" in workflow and "inputs" in workflow["5"]:
          workflow["5"]["inputs"]["filename_prefix"] = f"SuperVideo_{safe_task_name}"
      
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
      workflow_type_key = (
        "portrait_enhancement" if data.processing_option == "portrait_enhancement"
        else "flash_vsr" if data.model_name == "FlashVSR"
        else "super_video"
      )
      task_manager.add_task(prompt_id, {
        "task_id": prompt_id,
        "prompt_id": prompt_id,
        "workflow_type": workflow_type_key,
        "task_name": data.task_name,
        "params": {
          "task_name": data.task_name,
          "model_name": data.model_name,
          "video_filename": data.video_filename,
          "processing_option": data.processing_option,
          "workflow": workflow_type_name
        }
      })
      
      # 在后台等待任务完成（视频处理可能需要较长时间）
      background_tasks.add_task(wait_for_completion, prompt_id, 1800)
      
      logger.info(f"📝 {workflow_type_name}任务已提交: {prompt_id}")
      logger.info(f"   任务名称: {data.task_name}")
      logger.info(f"   视频文件: {data.video_filename}")
      logger.info(f"   处理选项: {data.processing_option}")
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

