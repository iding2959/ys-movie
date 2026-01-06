"""
音频驱动视频生成（InfiniteTalk I2V）相关接口
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from core.comfyui_client import ComfyUIClient
from core.models import TaskResponse
from core.managers import TaskManager, ConnectionManager
from core.response import R, ResponseModel
from pathlib import Path
from PIL import Image
import json
import logging
import random
import traceback
import base64
import io
import shutil
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["音频驱动视频"])


def setup_infinitetalk_i2v_routes(
  comfyui_server: str,
  task_manager: TaskManager,
  connection_manager: ConnectionManager,
  workflow_dir: Path,
  protocol: str = "http",
  ws_protocol: str = "ws"
):
  """
  设置音频驱动视频生成路由
  
  Args:
    comfyui_server: ComfyUI 服务器地址
    task_manager: 任务管理器实例
    connection_manager: WebSocket 连接管理器实例
    workflow_dir: 工作流文件目录
    protocol: HTTP协议
    ws_protocol: WebSocket协议
  """
  
  async def wait_for_completion(prompt_id: str, timeout: int):
    """等待任务完成（后台任务）"""
    from datetime import datetime
    
    try:
      # 更新状态为执行中
      task_manager.update_task(prompt_id, {"status": "running"})
      
      # 广播状态更新
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "running"
      }))
      
      logger.info(f"开始等待任务完成: {prompt_id}")
      
      # 等待任务完成
      try:
        async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
          result = await client.async_wait_for_completion(prompt_id, timeout)
          logger.info(f"任务 {prompt_id} 执行成功")
          
          # 提取输出
          outputs = client.extract_outputs(result)
          
          final_result = {
            "prompt_id": prompt_id,
            "status": "completed",
            "outputs": outputs,
            "raw_result": result
          }
          
      except Exception as e:
        logger.error(f"ComfyUI执行失败: {str(e)}")
        logger.error(f"错误详情: {traceback.format_exc()}")
        raise
      
      # 更新任务结果
      task_manager.update_task(prompt_id, {
        "status": "completed",
        "result": final_result,
        "completed_at": datetime.now().isoformat()
      })
      
      logger.info(f"任务 {prompt_id} 结果已保存")
      
      # 广播完成消息
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "completed",
        "result": final_result
      }))
      
    except Exception as e:
      logger.error(f"执行任务 {prompt_id} 失败: {e}")
      logger.error(f"完整错误堆栈: {traceback.format_exc()}")
      
      # 更新任务状态为失败
      error_msg = str(e)
      task_manager.update_task(prompt_id, {
        "status": "failed",
        "error": error_msg
      })
      
      # 广播失败消息
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "failed",
        "error": error_msg
      }))

  def resize_image_to_target(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """
    调整图片到目标尺寸，保持宽高比并裁剪
    
    Args:
      image: PIL Image对象
      target_width: 目标宽度
      target_height: 目标高度
    
    Returns:
      调整后的PIL Image对象
    """
    # 计算目标宽高比
    target_ratio = target_width / target_height
    img_ratio = image.width / image.height
    
    # 根据宽高比调整
    if img_ratio > target_ratio:
      # 图片更宽，按高度缩放
      new_height = target_height
      new_width = int(target_height * img_ratio)
    else:
      # 图片更高，按宽度缩放
      new_width = target_width
      new_height = int(target_width / img_ratio)
    
    # 缩放图片
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # 居中裁剪
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    
    image = image.crop((left, top, right, bottom))
    
    return image

  @router.post("/infinitetalk-i2v/generate", response_model=ResponseModel[TaskResponse])
  async def generate_video_from_audio(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(..., description="输入图片"),
    audio: UploadFile = File(..., description="输入音频"),
    prompt: str = Form(default="A person passionately speaking. A close-up shot captures expressive performance.", description="正向提示词"),
    negative_prompt: str = Form(default="bright tones, overexposed, static, blurred details", description="负向提示词"),
    steps: Optional[int] = Form(default=4, description="推理步数（可选，默认4）"),
    cfg: Optional[float] = Form(default=1.0, description="CFG引导强度（可选，默认1.0）"),
    shift: Optional[float] = Form(default=11.0, description="时间偏移（可选，默认11.0）"),
    seed: Optional[int] = Form(default=None, description="随机种子（可选，留空则随机生成）"),
    width: Optional[int] = Form(default=720, description="输出宽度（可选，默认720）"),
    height: Optional[int] = Form(default=480, description="输出高度（可选，默认480）"),
    fps: Optional[int] = Form(default=25, description="帧率（可选，默认25）"),
    audio_start_time: Optional[str] = Form(default=None, description="音频起始时间（可选，默认0:00）"),
    audio_end_time: Optional[str] = Form(default=None, description="音频结束时间（可选，默认为音频实际时长）"),
    timeout: Optional[int] = Form(default=600, description="超时时间（可选，默认600秒）")
  ):
    """
    音频驱动视频生成接口
    
    上传图片和音频，生成口型同步的视频
    支持的图片格式：PNG, JPG, JPEG
    支持的音频格式：MP3, WAV, M4A
    
    所有参数除了image和audio外都是可选的，会使用最优默认值
    """
    try:
      logger.info("收到音频驱动视频生成请求")
      
      # 验证文件类型
      if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="必须上传图片文件")
      
      if not audio.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="必须上传音频文件")
      
      # 处理可选参数，确保都有合理的默认值
      steps = steps if steps and steps > 0 else 4
      cfg = cfg if cfg and cfg >= 0 else 1.0
      shift = shift if shift and shift >= 0 else 11.0
      fps = fps if fps and fps > 0 else 25
      width = width if width and width > 0 else 720
      height = height if height and height > 0 else 480
      timeout = timeout if timeout and timeout > 0 else 600
      
      logger.info(f"处理后的参数: steps={steps}, cfg={cfg}, shift={shift}, fps={fps}, "
                 f"width={width}, height={height}, timeout={timeout}")
      
      # 验证尺寸参数
      valid_sizes = [(480, 720), (720, 480), (832, 480), (480, 832)]
      if (width, height) not in valid_sizes:
        logger.warning(f"请求的尺寸 {width}x{height} 不在推荐列表中，将使用最接近的尺寸")
        # 自动选择最接近的尺寸
        if width >= height:
          width, height = 720, 480
        else:
          width, height = 480, 720
      
      # 处理图片
      image_content = await image.read()
      img = Image.open(io.BytesIO(image_content))
      
      # 转换为RGB模式
      if img.mode != 'RGB':
        img = img.convert('RGB')
      
      # 调整图片尺寸
      img = resize_image_to_target(img, width, height)
      logger.info(f"图片已调整到 {width}x{height}")
      
      # 保存处理后的图片到临时文件
      with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
        img.save(tmp_img.name, 'PNG')
        temp_image_path = tmp_img.name
      
      # 保存音频到临时文件
      audio_content = await audio.read()
      audio_ext = Path(audio.filename).suffix or '.mp3'
      with tempfile.NamedTemporaryFile(suffix=audio_ext, delete=False) as tmp_audio:
        tmp_audio.write(audio_content)
        temp_audio_path = tmp_audio.name
      
      # 处理时间参数（空字符串、None、无效值都视为未设置）
      # 清理和验证 audio_start_time
      if not audio_start_time or not isinstance(audio_start_time, str) or ':' not in audio_start_time:
        audio_start_time = None
      
      # 清理和验证 audio_end_time
      if not audio_end_time or not isinstance(audio_end_time, str) or ':' not in audio_end_time:
        audio_end_time = None
      
      # 自动检测音频时长（如果未指定结束时间）
      if audio_end_time is None:
        try:
          # 尝试使用 wave 库检测 WAV 文件时长
          if audio_ext.lower() == '.wav':
            import wave
            with wave.open(temp_audio_path, 'rb') as wav_file:
              frames = wav_file.getnframes()
              rate = wav_file.getframerate()
              duration = frames / float(rate)
              minutes = int(duration // 60)
              seconds = int(duration % 60)
              audio_end_time = f"{minutes}:{seconds:02d}"
              logger.info(f"自动检测到音频时长: {audio_end_time} ({duration:.2f}秒)")
          else:
            # 对于其他格式，尝试使用 mutagen（如果可用）
            try:
              from mutagen import File as MutagenFile
              audio_info = MutagenFile(temp_audio_path)
              if audio_info and hasattr(audio_info.info, 'length'):
                duration = audio_info.info.length
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                audio_end_time = f"{minutes}:{seconds:02d}"
                logger.info(f"自动检测到音频时长: {audio_end_time} ({duration:.2f}秒)")
              else:
                # 无法检测，使用默认值
                audio_end_time = "10:00"
                logger.warning(f"无法检测音频时长，使用默认值: {audio_end_time}")
            except ImportError:
              # mutagen 未安装，使用默认值
              audio_end_time = "10:00"
              logger.warning(f"mutagen库未安装，无法检测{audio_ext}音频时长，使用默认值: {audio_end_time}")
        except Exception as e:
          # 检测失败，使用默认值
          audio_end_time = "10:00"
          logger.warning(f"检测音频时长失败: {e}，使用默认值: {audio_end_time}")
      
      # 设置默认起始时间
      if audio_start_time is None:
        audio_start_time = "0:00"
      
      logger.info(f"最终音频时间参数: start={audio_start_time}, end={audio_end_time}")
      
      # 加载工作流模板
      workflow_file = workflow_dir / "infinitetalkI2V.json"
      if not workflow_file.exists():
        raise HTTPException(status_code=404, detail=f"工作流文件不存在: {workflow_file}")
      
      with open(workflow_file, "r", encoding="utf-8") as f:
        workflow = json.load(f)
      
      # 生成随机种子
      if seed is None:
        seed = random.randint(0, 2**32 - 1)
      
      # 上传文件到ComfyUI
      logger.info("上传文件到ComfyUI服务器")
      
      # 上传图片
      with open(temp_image_path, 'rb') as f:
        image_data = f.read()
      image_filename = f"infinitetalk_input_{seed}.png"
      
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        upload_result = await client.async_upload_image(
          image_data=image_data,
          filename=image_filename,
          overwrite=True
        )
        uploaded_image = upload_result.get('name', image_filename)
      
      # 上传音频（使用自定义方法，因为ComfyUI的upload/image端点可以处理任意文件）
      with open(temp_audio_path, 'rb') as f:
        audio_data = f.read()
      audio_filename = f"infinitetalk_audio_{seed}{audio_ext}"
      
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        # 使用upload/image端点上传音频（ComfyUI的LoadAudio会从input文件夹读取）
        import aiohttp
        session = client._get_session()
        form = aiohttp.FormData()
        # 根据文件扩展名设置正确的content_type
        content_type_map = {
          '.mp3': 'audio/mpeg',
          '.wav': 'audio/wav',
          '.m4a': 'audio/mp4',
          '.aac': 'audio/aac',
          '.ogg': 'audio/ogg'
        }
        audio_content_type = content_type_map.get(audio_ext.lower(), 'audio/mpeg')
        form.add_field('image', audio_data, filename=audio_filename, content_type=audio_content_type)
        form.add_field('overwrite', 'true')
        
        async with session.post(f"{client.api_url}/upload/image", data=form) as response:
          if response.status != 200:
            error_text = await response.text()
            raise Exception(f"上传音频失败: {error_text}")
          upload_result = await response.json()
          uploaded_audio = upload_result.get('name', audio_filename)
      
      logger.info(f"文件上传成功 - 图片: {uploaded_image}, 音频: {uploaded_audio}")
      
      # 清理临时文件
      try:
        Path(temp_image_path).unlink()
        Path(temp_audio_path).unlink()
      except Exception as e:
        logger.warning(f"清理临时文件失败: {e}")
      
      # 修改工作流参数（API格式使用节点ID和inputs字典）
      # 节点203: LoadImage
      if "203" in workflow and "inputs" in workflow["203"]:
        workflow["203"]["inputs"]["image"] = uploaded_image
      
      # 节点125: LoadAudio
      if "125" in workflow and "inputs" in workflow["125"]:
        workflow["125"]["inputs"]["audio"] = uploaded_audio
      
      # 节点159: AudioCrop - 设置音频裁剪时间
      if "159" in workflow and "inputs" in workflow["159"]:
        workflow["159"]["inputs"]["start_time"] = audio_start_time
        workflow["159"]["inputs"]["end_time"] = audio_end_time
      
      # 节点171: ImageResizeKJv2 - 设置图片尺寸
      if "171" in workflow and "inputs" in workflow["171"]:
        workflow["171"]["inputs"]["width"] = width
        workflow["171"]["inputs"]["height"] = height
      
      # 节点192: WanVideoImageToVideoMultiTalk - 设置视频尺寸
      if "192" in workflow and "inputs" in workflow["192"]:
        workflow["192"]["inputs"]["width"] = width
        workflow["192"]["inputs"]["height"] = height
      
      # 节点194: MultiTalkWav2VecEmbeds - 设置FPS
      if "194" in workflow and "inputs" in workflow["194"]:
        workflow["194"]["inputs"]["fps"] = fps
      
      # 节点204: WanVideoSampler - 设置生成参数
      if "204" in workflow and "inputs" in workflow["204"]:
        workflow["204"]["inputs"]["steps"] = steps
        workflow["204"]["inputs"]["cfg"] = cfg
        workflow["204"]["inputs"]["shift"] = shift
        workflow["204"]["inputs"]["seed"] = seed
      
      # 节点135: WanVideoTextEncode - 设置提示词
      if "135" in workflow and "inputs" in workflow["135"]:
        workflow["135"]["inputs"]["positive_prompt"] = prompt
        workflow["135"]["inputs"]["negative_prompt"] = negative_prompt
      
      logger.info(f"工作流参数已更新: size={width}x{height}, steps={steps}, cfg={cfg}, seed={seed}")
      
      # 提交工作流
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
      logger.info(f"工作流已提交，prompt_id: {prompt_id}")
      
      # 创建任务记录
      task_manager.add_task(prompt_id, {
        "task_id": prompt_id,
        "prompt_id": prompt_id,
        "workflow_type": "infinitetalk_i2v",
        "params": {
          "image": uploaded_image,
          "audio": uploaded_audio,
          "prompt": prompt,
          "negative_prompt": negative_prompt,
          "width": width,
          "height": height,
          "steps": steps,
          "cfg": cfg,
          "shift": shift,
          "seed": seed,
          "fps": fps,
          "audio_start_time": audio_start_time,
          "audio_end_time": audio_end_time
        }
      })
      
      # 添加后台任务等待完成
      background_tasks.add_task(wait_for_completion, prompt_id, timeout)
      
      return R.success(
        data=TaskResponse(
          task_id=prompt_id,
          status="pending",
          message="视频生成任务已提交，请等待处理"
        ),
        message="任务提交成功"
      )
      
    except HTTPException:
      raise
    except Exception as e:
      logger.error(f"生成视频失败: {e}")
      logger.error(f"完整错误堆栈: {traceback.format_exc()}")
      raise HTTPException(status_code=500, detail=f"生成视频失败: {str(e)}")

  return router

