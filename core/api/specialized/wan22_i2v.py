"""
Wan2.2 图生视频 API
根据时长自动拼接或删除节点生成视频
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from core.comfyui_client import ComfyUIClient
from core.models import TaskResponse
from core.managers import TaskManager, ConnectionManager
from core.response import R, ResponseModel
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import json
import logging
import copy
import random

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wan22_i2v", tags=["Wan2.2视频生成"])


class Wan22I2VRequest(BaseModel):
  """
  Wan2.2 图生视频请求
  
  提示词参数说明:
    prompt: 单个字符串，适用于短视频或所有片段使用相同提示词
      示例: "一个女孩在海边散步，阳光明媚"
    
    或使用提示词列表（推荐），为每个5秒片段提供独立提示词:
      示例1 (10秒): ["第一段：女孩走向海边", "第二段：女孩在海边欣赏日落"]
      示例2 (15秒): ["开始：女孩出发", "中间：走在路上", "结尾：到达海边"]
      示例3 (20秒): ["片段1描述", "片段2描述", "片段3描述", "片段4描述"]
  
  注意: 使用列表时，提示词数量必须等于 duration/5
  """
  prompt: Union[str, List[str]] = Field(
    ..., 
    description="视频描述提示词。可以是单个字符串或每个5秒片段对应的提示词列表。建议为每个5秒片段提供对应提示词以获得更好效果"
  )
  negative_prompt: str = Field(default="", description="负面提示词")
  duration: int = Field(default=5, ge=5, le=30, description="视频时长（秒），5-30秒，步长为5秒")
  width: int = Field(default=480, ge=256, le=1920, description="视频宽度")
  height: int = Field(default=832, ge=256, le=1920, description="视频高度")
  frame_rate: int = Field(default=16, ge=8, le=30, description="帧率")
  steps: int = Field(default=4, ge=1, le=20, description="采样步数")
  seed: int = Field(default=-1, description="随机种子，-1为随机")
  image_filename: Optional[str] = Field(None, description="起始图片文件名（已上传到input文件夹）")
  
  @model_validator(mode='after')
  def validate_prompt_and_duration(self):
    """验证提示词与时长的匹配"""
    num_segments = self.duration // 5
    
    if isinstance(self.prompt, str):
      # 单个提示词，如果时长超过5秒，发出警告
      if num_segments > 1:
        logger.warning(
          f"⚠️ 仅提供了1个提示词，但视频时长为{self.duration}秒（{num_segments}个片段）。"
          f"建议为每个5秒片段提供对应的提示词以获得更好的输出效果"
        )
    elif isinstance(self.prompt, list):
      # 提示词列表，检查数量是否匹配
      if len(self.prompt) != num_segments:
        raise ValueError(
          f"提示词数量({len(self.prompt)})与视频片段数量({num_segments})不匹配。"
          f"{self.duration}秒视频需要{num_segments}个提示词"
        )
    else:
      raise ValueError("prompt必须是字符串或字符串列表")
    
    return self


def setup_wan22_i2v_routes(
  comfyui_server: str,
  task_manager: TaskManager,
  connection_manager: ConnectionManager,
  protocol: str = "http",
  ws_protocol: str = "ws"
):
  """
  设置Wan2.2视频生成路由
  
  Args:
    comfyui_server: ComfyUI 服务器地址
    task_manager: 任务管理器实例
    connection_manager: WebSocket 连接管理器实例
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
      
      logger.info(f"开始等待Wan2.2视频任务完成: {prompt_id}")
      
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
      
    except Exception as e:
      logger.error(f"执行Wan2.2视频任务 {prompt_id} 失败: {e}")
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
  
  @router.post("/analyze_image", response_model=ResponseModel)
  async def analyze_image(image: UploadFile = File(...)):
    """
    分析上传的图片，返回建议的视频尺寸
    保持图片比例，长边对齐到832或用户指定值
    """
    try:
      image_data = await image.read()
      
      # 生成安全的文件名（避免中文编码问题）
      from pathlib import Path
      import uuid
      from datetime import datetime
      file_ext = Path(image.filename).suffix.lower()
      safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
      
      # 上传到ComfyUI
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        upload_result = await client.async_upload_image(
          image_data=image_data,
          filename=safe_filename,
          overwrite=True
        )
      
      uploaded_filename = upload_result.get('name', safe_filename)
      
      # 使用PIL读取图片尺寸
      try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(image_data))
        orig_width, orig_height = img.size
        
        # 计算最佳视频尺寸
        # 保持比例，长边832，必须对齐到32的倍数（Wan2.2模型要求）
        if orig_width >= orig_height:
          # 横屏
          target_width = 832
          target_height = int(round(orig_height * 832 / orig_width))
        else:
          # 竖屏
          target_height = 832
          target_width = int(round(orig_width * 832 / orig_height))
        
        # 对齐到32的倍数（模型要求，避免张量维度不匹配）
        target_width = max(256, min(1920, (target_width // 32) * 32))
        target_height = max(256, min(1920, (target_height // 32) * 32))
        
        # 32的倍数自动满足偶数要求，但再次确保
        if target_width % 2 == 1:
          target_width = ((target_width // 32) + 1) * 32
        if target_height % 2 == 1:
          target_height = ((target_height // 32) + 1) * 32
        
        aspect_ratio = orig_width / orig_height
        
      except Exception as e:
        logger.warning(f"无法解析图片尺寸: {e}，使用默认值")
        orig_width, orig_height = 480, 832
        target_width, target_height = 480, 832
        aspect_ratio = 480 / 832
      
      return R.success(
        data={
          "filename": uploaded_filename,
          "original_width": orig_width,
          "original_height": orig_height,
          "suggested_width": target_width,
          "suggested_height": target_height,
          "aspect_ratio": round(aspect_ratio, 4)
        },
        message="图片分析完成"
      )
      
    except Exception as e:
      logger.error(f"分析图片失败: {e}")
      return R.server_error(message=f"分析图片失败: {str(e)}")
  
  @router.post("/upload_and_generate", response_model=ResponseModel)
  async def upload_and_generate(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    prompts: Optional[str] = Form(None, description="提示词列表（JSON字符串），优先级高于prompt"),
    negative_prompt: str = Form(default=""),
    duration: int = Form(default=5, ge=5, le=30),
    width: Optional[int] = Form(None, ge=256, le=1920),
    height: Optional[int] = Form(None, ge=256, le=1920),
    frame_rate: int = Form(default=16, ge=8, le=30),
    steps: int = Form(default=4, ge=1, le=20),
    seed: int = Form(default=-1),
    auto_size: bool = Form(default=True, description="自动计算最佳尺寸")
  ):
    """
    上传图片并生成视频（一步到位）
    
    参数说明:
      image: 起始图片文件
      prompt: 单个视频描述提示词（适用于短视频或所有片段使用相同提示词）
      prompts: 提示词列表（JSON字符串格式），为每个5秒片段提供对应提示词，建议使用以获得更好效果
      negative_prompt: 负面提示词
      duration: 视频时长（秒），5-30秒，步长为5秒
      width: 视频宽度（可选，不填或auto_size=True时自动计算）
      height: 视频高度（可选，不填或auto_size=True时自动计算）
      frame_rate: 帧率
      steps: 采样步数
      seed: 随机种子，-1为随机
      auto_size: 是否自动计算最佳尺寸（默认True），开启后会忽略width/height参数
    
    提示词参数说明:
      - prompt 和 prompts 参数二选一，不能同时提供
      - prompt: 单个字符串，所有片段使用相同提示词
        示例: "一个女孩在海边散步，阳光明媚"
      
      - prompts: JSON数组字符串，为每个5秒片段提供独立提示词（推荐）
        示例1 (10秒视频): '["第一段：女孩走向海边", "第二段：女孩在海边欣赏日落"]'
        示例2 (15秒视频): '["开始：女孩出发", "中间：走在路上", "结尾：到达海边"]'
        示例3 (20秒视频): '["片段1描述", "片段2描述", "片段3描述", "片段4描述"]'
    
    视频尺寸说明:
      - 不传width/height或auto_size=True: 自动根据图片比例计算最佳尺寸（推荐）
      - 传入width/height且auto_size=False: 使用指定尺寸
      - 尺寸会自动对齐到32的倍数（模型要求）
    
    注意事项:
      - 视频时长必须是5的倍数（5秒、10秒、15秒等）
      - 使用prompts时，提示词数量必须等于 duration/5
      - 例如15秒视频需要3个提示词，20秒视频需要4个提示词
    """
    try:
      # 验证提示词参数：必须提供其中一个，且不能同时提供
      if not prompt and not prompts:
        return R.client_error(message="必须提供prompt或prompts参数之一")
      
      if prompt and prompts:
        return R.client_error(message="prompt和prompts参数只能提供其中一个，不能同时使用")
      
      # 解析提示词
      num_segments = duration // 5
      
      if prompts:
        # 使用prompts参数（JSON数组）
        try:
          prompt_list = json.loads(prompts)
          if not isinstance(prompt_list, list):
            return R.client_error(message="prompts必须是JSON数组格式")
          if len(prompt_list) != num_segments:
            return R.client_error(
              message=f"提示词数量({len(prompt_list)})与视频片段数量({num_segments})不匹配。"
                     f"{duration}秒视频需要{num_segments}个提示词"
            )
          prompt_value = prompt_list
        except json.JSONDecodeError as e:
          return R.client_error(message=f"prompts参数必须是有效的JSON字符串: {str(e)}")
      else:
        # 使用prompt参数（单个字符串）
        prompt_value = prompt
        if num_segments > 1:
          logger.warning(
            f"⚠️ 仅提供了1个提示词，但视频时长为{duration}秒（{num_segments}个片段）。"
            f"建议使用prompts参数为每个5秒片段提供对应的提示词以获得更好的输出效果"
          )
      
      # 1. 上传图片
      image_data = await image.read()
      
      # 生成安全的文件名（避免中文编码问题）
      from pathlib import Path
      import uuid
      from datetime import datetime
      file_ext = Path(image.filename).suffix.lower()
      safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
      
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        upload_result = await client.async_upload_image(
          image_data=image_data,
          filename=safe_filename,
          overwrite=True
        )
      
      uploaded_filename = upload_result.get('name', safe_filename)
      logger.info(f"图片上传成功: {image.filename} -> {uploaded_filename}")
      
      # 1.5 自动计算最佳尺寸（如果启用或未提供尺寸）
      final_width = width
      final_height = height
      
      if auto_size or width is None or height is None:
        try:
          from PIL import Image
          from io import BytesIO
          img = Image.open(BytesIO(image_data))
          orig_width, orig_height = img.size
          
          # 计算最佳视频尺寸（保持比例，长边832，对齐到32的倍数）
          if orig_width >= orig_height:
            # 横屏
            target_width = 832
            target_height = int(round(orig_height * 832 / orig_width))
          else:
            # 竖屏
            target_height = 832
            target_width = int(round(orig_width * 832 / orig_height))
          
          # 对齐到32的倍数（模型要求）
          final_width = max(256, min(1920, (target_width // 32) * 32))
          final_height = max(256, min(1920, (target_height // 32) * 32))
          
          # 确保是偶数
          if final_width % 2 == 1:
            final_width = ((final_width // 32) + 1) * 32
          if final_height % 2 == 1:
            final_height = ((final_height // 32) + 1) * 32
          
          logger.info(f"📐 自动计算视频尺寸: {orig_width}x{orig_height} -> {final_width}x{final_height}")
          
        except Exception as e:
          logger.warning(f"无法解析图片尺寸: {e}，使用默认值")
          final_width = width if width else 480
          final_height = height if height else 832
      
      # 2. 生成workflow
      workflow = generate_wan22_workflow(
        image_filename=uploaded_filename,
        prompt=prompt_value,
        negative_prompt=negative_prompt,
        duration=duration,
        width=final_width,
        height=final_height,
        frame_rate=frame_rate,
        steps=steps,
        seed=seed
      )
      
      # 3. 提交到ComfyUI
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        response = await client.async_queue_prompt(workflow)
        
      if not response or 'prompt_id' not in response:
        error_detail = response.get('error', '未知错误') if response else '无响应'
        node_errors = response.get('node_errors', {}) if response else {}
        
        error_msg = f"ComfyUI提交失败: {error_detail}"
        if node_errors:
          error_msg += f", 节点错误: {json.dumps(node_errors, ensure_ascii=False)}"
        
        raise HTTPException(
          status_code=500,
          detail=error_msg
        )
      
      prompt_id = response['prompt_id']
      
      # 4. 添加任务到管理器
      num_segments = duration // 5
      task_manager.add_task(prompt_id, {
        "task_id": prompt_id,
        "prompt_id": prompt_id,
        "workflow_type": "wan22_i2v",
        "params": {
          "prompt": prompt_value,
          "duration": duration,
          "width": final_width,
          "height": final_height,
          "image": uploaded_filename
        }
      })
      
      # 5. 在后台等待任务完成
      timeout = max(600, duration * 30)  # 根据时长动态设置超时
      background_tasks.add_task(wait_for_completion, prompt_id, timeout)
      
      logger.info(f"📹 Wan2.2视频任务已提交: {prompt_id}, 时长: {duration}秒, 尺寸: {final_width}x{final_height}")
      
      response_data = {
        "task_id": prompt_id,
        "status": "submitted",
        "duration": duration,
        "segments": num_segments,
        "image": uploaded_filename,
        "prompt_count": 1 if isinstance(prompt_value, str) else len(prompt_value),
        "width": final_width,
        "height": final_height,
        "auto_size": auto_size
      }
      
      message = f"视频生成任务已提交（{duration}秒, {final_width}x{final_height}）"
      if isinstance(prompt_value, str) and num_segments > 1:
        warning_msg = f"仅提供了1个提示词，但视频有{num_segments}个片段。建议为每个5秒片段提供对应的提示词以获得更好的输出效果"
        response_data["warning"] = warning_msg
        message += f"，{warning_msg}"
      
      return R.success(
        data=response_data,
        message=message
      )
      
    except Exception as e:
      logger.error(f"上传图片并生成视频失败: {e}")
      return R.server_error(message=f"操作失败: {str(e)}")
  
  @router.post("/generate", response_model=ResponseModel)
  async def generate_video(
    data: Wan22I2VRequest,
    background_tasks: BackgroundTasks
  ):
    """
    使用已上传的图片生成视频
    
    参数:
      data: Wan2.2视频生成请求参数
      
    注意:
      - 如果视频时长超过5秒，建议为每个5秒片段提供对应的提示词列表
      - 仅提供一个提示词时，所有片段将使用相同提示词，可能影响输出效果
    """
    try:
      if not data.image_filename:
        return R.client_error(message="必须提供image_filename参数")
      
      # 检查提示词情况并给出警告
      num_segments = data.duration // 5
      prompt_warning = None
      if isinstance(data.prompt, str) and num_segments > 1:
        prompt_warning = f"仅提供了1个提示词，但视频有{num_segments}个片段。建议为每个5秒片段提供对应的提示词以获得更好的输出效果"
      
      # 生成workflow
      workflow = generate_wan22_workflow(
        image_filename=data.image_filename,
        prompt=data.prompt,
        negative_prompt=data.negative_prompt,
        duration=data.duration,
        width=data.width,
        height=data.height,
        frame_rate=data.frame_rate,
        steps=data.steps,
        seed=data.seed
      )
      
      # 提交到ComfyUI
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        response = await client.async_queue_prompt(workflow)
        
      if not response or 'prompt_id' not in response:
        error_detail = response.get('error', '未知错误') if response else '无响应'
        node_errors = response.get('node_errors', {}) if response else {}
        
        error_msg = f"ComfyUI提交失败: {error_detail}"
        if node_errors:
          error_msg += f", 节点错误: {json.dumps(node_errors, ensure_ascii=False)}"
        
        raise HTTPException(
          status_code=500,
          detail=error_msg
        )
      
      prompt_id = response['prompt_id']
      
      # 添加任务到管理器
      task_manager.add_task(prompt_id, {
        "task_id": prompt_id,
        "prompt_id": prompt_id,
        "workflow_type": "wan22_i2v",
        "params": data.dict()
      })
      
      # 在后台等待任务完成
      timeout = max(600, data.duration * 30)
      background_tasks.add_task(wait_for_completion, prompt_id, timeout)
      
      logger.info(f"📹 Wan2.2视频任务已提交: {prompt_id}, 时长: {data.duration}秒")
      
      response_data = {
        "task_id": prompt_id,
        "status": "submitted",
        "duration": data.duration,
        "segments": num_segments,
        "prompt_count": 1 if isinstance(data.prompt, str) else len(data.prompt)
      }
      
      message = f"视频生成任务已提交（{data.duration}秒）"
      if prompt_warning:
        response_data["warning"] = prompt_warning
        message += f"，{prompt_warning}"
      
      return R.success(
        data=response_data,
        message=message
      )
      
    except Exception as e:
      logger.error(f"生成视频失败: {e}")
      return R.server_error(message=f"生成视频失败: {str(e)}")
  
  return router


def generate_wan22_workflow(
  image_filename: str,
  prompt: Union[str, List[str]],
  negative_prompt: str = "",
  duration: int = 5,
  width: int = 480,
  height: int = 832,
  frame_rate: int = 16,
  steps: int = 4,
  seed: int = -1
) -> Dict[str, Any]:
  """
  根据参数生成Wan2.2视频workflow
  
  Args:
    image_filename: 起始图片文件名
    prompt: 提示词（字符串或每个5秒片段对应的提示词列表）
    negative_prompt: 负面提示词
    duration: 视频时长（秒）
    width: 宽度
    height: 高度
    frame_rate: 帧率
    steps: 采样步数
    seed: 随机种子
    
  Returns:
    完整的workflow字典
  """
  # 计算需要多少个5秒片段
  num_segments = duration // 5
  
  # 标准化提示词：转换为列表
  if isinstance(prompt, str):
    prompts = [prompt] * num_segments
  else:
    prompts = prompt
  
  # 验证提示词数量
  if len(prompts) != num_segments:
    raise ValueError(f"提示词数量({len(prompts)})与片段数量({num_segments})不匹配")
  # 计算每个片段应生成的帧数（确保总时长精确）
  # 在16FPS下，强制每个5秒片段输出81帧，避免容器/合成时长偏短
  segment_length = 81 if frame_rate == 16 else int(round(5 * frame_rate))
  # 片段之间用于连续性的参考帧数量（用于作为下一段的起始条件，不参与裁剪）
  # 过渡参考帧：增大到约1秒内或至少8帧，最多24帧，提升衔接稳定性
  overlap_frames = max(8, min(24, int(round(frame_rate))))
  
  if seed == -1:
    seed = random.randint(0, 18446744073709551615)
  
  # 基础节点（所有workflow共用）
  workflow = {
    "16": {
      "inputs": {"image": image_filename},
      "class_type": "LoadImage",
      "_meta": {"title": "Start Frame"}
    },
    "26": {
      "inputs": {"ckpt_name": "wan2.2-rapid-mega-aio-v12.safetensors"},
      "class_type": "CheckpointLoaderSimple",
      "_meta": {"title": "Load Checkpoint"}
    },
    "32": {
      "inputs": {"shift": 8, "model": ["26", 0]},
      "class_type": "ModelSamplingSD3",
      "_meta": {"title": "ModelSampling"}
    },
    "44": {
      "inputs": {"value": frame_rate},
      "class_type": "Float",
      "_meta": {"title": "Frame Rate"}
    },
    "57": {
      "inputs": {
        "mode": "Manual",
        "width": width,
        "height": height,
        "auto_detect": True,
        "rescale_mode": "resolution",
        "rescale_value": 2.27866357593825,
        "input_image": ["16", 0]
      },
      "class_type": "ResolutionMaster",
      "_meta": {"title": "Resolution Master"}
    },
    "58": {
      "inputs": {
        "width": ["57", 0],
        "height": ["57", 1],
        "upscale_method": "nearest-exact",
        "keep_proportion": "stretch",
        "pad_color": "0, 0, 0",
        "crop_position": "center",
        "divisible_by": 2,
        "device": "cpu",
        "image": ["16", 0]
      },
      "class_type": "ImageResizeKJv2",
      "_meta": {"title": "Resize Image"}
    },
    "120": {
      "inputs": {"value": steps},
      "class_type": "PrimitiveInt",
      "_meta": {"title": "steps"}
    }
  }
  
  # 为每个片段生成唯一的种子
  segment_seeds = [seed + i * 1000000 for i in range(num_segments)]
  
  # 根据片段数量生成对应的节点
  if num_segments == 1:
    # 单个5秒片段
    workflow.update(
      generate_single_segment(
        index=0,
        seed=segment_seeds[0],
        prompt=prompts[0],
        negative_prompt=negative_prompt,
        segment_length=segment_length,
        overlap_frames=overlap_frames,
        prefix="70"
      )
    )
    # 最终输出节点
    workflow["39"] = {
      "inputs": {
        "frame_rate": ["44", 0],
        "loop_count": 0,
        "filename_prefix": "wan2.2_video",
        "format": "video/h264-mp4",
        "pix_fmt": "yuv420p",
        "crf": 19,
        "save_metadata": True,
        "trim_to_audio": False,
        "pingpong": False,
        "save_output": True,
        "images": ["70:11", 0]
      },
      "class_type": "VHS_VideoCombine",
      "_meta": {"title": "Video Output"}
    }
  else:
    # 多个片段需要拼接
    # 第一个片段
    workflow.update(
      generate_single_segment(
        index=0,
        seed=segment_seeds[0],
        prompt=prompts[0],
        negative_prompt=negative_prompt,
        segment_length=segment_length,
        overlap_frames=overlap_frames,
        prefix="70"
      )
    )
    
    # 中间片段
    for i in range(1, num_segments):
      prev_prefix = f"{70 + (i-1)*6}" if i == 1 else f"{70 + (i-1)*6}"
      curr_prefix = f"{70 + i*6}"
      workflow.update(
        generate_linked_segment(
          index=i,
          seed=segment_seeds[i],
          prompt=prompts[i],
          negative_prompt=negative_prompt,
          prev_prefix=prev_prefix,
          curr_prefix=curr_prefix,
          segment_length=segment_length,
          overlap_frames=overlap_frames
        )
      )
    
    # 最终拼接和输出
    workflow.update(generate_final_merge(num_segments=num_segments, overlap_frames=overlap_frames, segment_length=segment_length))
  
  return workflow


def generate_single_segment(
  index: int,
  seed: int,
  prompt: str,
  negative_prompt: str,
  segment_length: int,
  overlap_frames: int,
  prefix: str = "70"
) -> Dict[str, Any]:
  """生成单个5秒片段的节点（长度与fps精确匹配）"""
  # 对于第0段，按 segment_length；对于后续段，额外多生成 overlap_frames 以便裁剪
  effective_length = segment_length if index == 0 else segment_length + overlap_frames
  # 后续段降低 empty_frame_level 以增强与前段的连续性
  start_empty_level = 0.5 if index == 0 else 0.2
  return {
    f"{prefix}:34": {
      "inputs": {
        "num_frames": effective_length,
        "empty_frame_level": start_empty_level,
        "start_index": 0,
        "end_index": -1,
        "start_image": ["58", 0] if index == 0 else [f"{int(prefix)-6}:91", 0]
      },
      "class_type": "WanVideoVACEStartToEndFrame",
      "_meta": {"title": f"VACE Frame {index}"}
    },
    f"{prefix}:10": {
      "inputs": {
        "text": negative_prompt,
        "clip": ["26", 1]
      },
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Negative Prompt"}
    },
    f"{prefix}:70": {
      "inputs": {"text": prompt},
      "class_type": "CR Text",
      "_meta": {"title": f"Prompt {index}"}
    },
    f"{prefix}:9": {
      "inputs": {
        "text": [f"{prefix}:70", 0],
        "clip": ["26", 1]
      },
      "class_type": "CLIPTextEncode",
      "_meta": {"title": "Positive Prompt"}
    },
    f"{prefix}:28": {
      "inputs": {
        "width": ["58", 1],
        "height": ["58", 2],
        "length": effective_length,
        "batch_size": 1,
        "strength": 1,
        "positive": [f"{prefix}:9", 0],
        "negative": [f"{prefix}:10", 0],
        "vae": ["26", 2],
        "control_video": [f"{prefix}:34", 0],
        "control_masks": [f"{prefix}:34", 1]
      },
      "class_type": "WanVaceToVideo",
      "_meta": {"title": "VaceToVideo"}
    },
    f"{prefix}:8": {
      "inputs": {
        "seed": seed,
        "steps": ["120", 0],
        "cfg": 1,
        "sampler_name": "ipndm",
        "scheduler": "sgm_uniform",
        "denoise": 1,
        "model": ["32", 0],
        "positive": [f"{prefix}:28", 0],
        "negative": [f"{prefix}:28", 1],
        "latent_image": [f"{prefix}:28", 2]
      },
      "class_type": "KSampler",
      "_meta": {"title": "Sampler"}
    },
    f"{prefix}:11": {
      "inputs": {
        "samples": [f"{prefix}:8", 0],
        "vae": ["26", 2]
      },
      "class_type": "VAEDecode",
      "_meta": {"title": "VAE Decode"}
    },
    f"{prefix}:91": {
      "inputs": {
        "start_index": max(0, (segment_length if index == 0 else effective_length) - overlap_frames),
        "num_frames": overlap_frames,
        "images": [f"{prefix}:11", 0]
      },
      "class_type": "GetImageRangeFromBatch",
      "_meta": {"title": "Get End Frames"}
    }
  }


def generate_linked_segment(
  index: int,
  seed: int,
  prompt: str,
  negative_prompt: str,
  prev_prefix: str,
  curr_prefix: str,
  segment_length: int,
  overlap_frames: int
) -> Dict[str, Any]:
  """生成链接到前一个片段的节点（无额外裁剪）"""
  segment = generate_single_segment(
    index=index,
    seed=seed,
    prompt=prompt,
    negative_prompt=negative_prompt,
    segment_length=segment_length,
    overlap_frames=overlap_frames,
    prefix=curr_prefix
  )
  # 修改start_image链接到前一个片段末尾若干帧
  segment[f"{curr_prefix}:34"]["inputs"]["start_image"] = [f"{prev_prefix}:91", 0]
  return segment


def generate_final_merge(num_segments: int, overlap_frames: int, segment_length: int) -> Dict[str, Any]:
  """生成最终合并节点（对后续段裁掉首 overlap_frames 帧再拼接）"""
  nodes = {}
  
  # 逐步合并所有片段
  for i in range(1, num_segments):
    prefix = 70 + i * 6
    prev_prefix = 70 + (i - 1) * 6
    
    # 为当前段创建裁剪节点：去掉首 overlap_frames 帧，保留精准 segment_length 帧
    nodes[f"{prefix}:92"] = {
      "inputs": {
        "batch_index": overlap_frames,
        "length": segment_length,
        "image": [f"{prefix}:11", 0]
      },
      "class_type": "ImageFromBatch",
      "_meta": {"title": f"Trim Start {i}"}
    }
    
    if i == 1:
      # 第一次合并：合并第0和第1片段（第1段已裁剪首重叠帧）
      nodes[f"{prefix}:88"] = {
        "inputs": {
          "inputcount": 2,
          "Update inputs": None,
          "image_1": ["70:11", 0],
          "image_2": [f"{prefix}:92", 0]
        },
        "class_type": "ImageBatchMulti",
        "_meta": {"title": "Merge 0-1"}
      }
    else:
      # 后续合并：合并之前的结果和已裁剪的当前片段
      nodes[f"{prefix}:88"] = {
        "inputs": {
          "inputcount": 2,
          "Update inputs": None,
          "image_1": [f"{prev_prefix}:88", 0],
          "image_2": [f"{prefix}:92", 0]
        },
        "class_type": "ImageBatchMulti",
        "_meta": {"title": f"Merge 0-{i}"}
      }
  
  # 最终输出节点
  last_prefix = 70 + (num_segments - 1) * 6
  final_input = [f"{last_prefix}:88", 0] if num_segments > 1 else ["70:11", 0]
  
  # 可选：颜色匹配
  nodes["100"] = {
    "inputs": {
      "method": "mkl",
      "strength": 1,
      "multithread": True,
      "image_ref": ["16", 0],
      "image_target": final_input
    },
    "class_type": "ColorMatch",
    "_meta": {"title": "Color Match"}
  }
  
  # 视频合成
  nodes["39"] = {
    "inputs": {
      "frame_rate": ["44", 0],
      "loop_count": 0,
      "filename_prefix": "wan2.2_video",
      "format": "video/h264-mp4",
      "pix_fmt": "yuv420p",
      "crf": 19,
      "save_metadata": True,
      "trim_to_audio": False,
      "pingpong": False,
      "save_output": True,
      "images": ["100", 0]
    },
    "class_type": "VHS_VideoCombine",
    "_meta": {"title": "Video Output"}
  }
  
  return nodes

