"""
媒体文件（图片/视频）获取相关接口
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from core.comfyui_client import ComfyUIClient
from core.managers import TaskManager
from core.response import R
from core.api.task import check_task_status_from_history
import io
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["媒体文件"])


def setup_media_routes(comfyui_server: str, task_manager: TaskManager,
                      protocol: str = "http", ws_protocol: str = "ws"):
  """
  设置媒体文件路由
  
  Args:
    comfyui_server: ComfyUI 服务器地址
    task_manager: 任务管理器实例
    protocol: HTTP协议
    ws_protocol: WebSocket协议
  """
  
  async def _get_task_with_history(task_id: str):
    """获取任务信息（先查本地，再查历史）"""
    task = task_manager.get_task(task_id)
    
    if not task:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        history = await client.async_get_history(task_id)
        
      if history and task_id in history:
        history_data = history[task_id]
        
        async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
          outputs = client.extract_outputs(history_data)
        
        # 检查任务真实状态
        task_status, error_msg = check_task_status_from_history(history_data)
        
        task = {
          "task_id": task_id,
          "status": task_status,
          "result": {
            "prompt_id": task_id,
            "status": task_status,
            "outputs": outputs,
            "raw_result": history_data
          }
        }
        
        # 如果失败，添加错误信息
        if task_status == "failed" and error_msg:
          task["error"] = error_msg
      else:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return task
  
  @router.get("/image/{filename}")
  async def get_image(filename: str, subfolder: str = "", type: str = "output"):
    """获取生成的图片（通用接口）"""
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        image_data = await client.async_get_image(filename, subfolder, type)
      return StreamingResponse(io.BytesIO(image_data), media_type="image/png")
    except Exception as e:
      logger.error(f"获取图片失败: {filename}, 错误: {str(e)}")
      # 对于文件流接口，如果失败返回JSON格式错误
      return R.not_found(message=f"图片不存在: {str(e)}")
  
  @router.get("/task/{task_id}/image")
  async def get_task_image(task_id: str, index: int = 0):
    """
    根据任务ID直接获取输出图片
    
    参数:
      task_id: 任务ID（prompt_id）
      index: 图片索引（默认0）
    """
    try:
      try:
        task = await _get_task_with_history(task_id)
      except HTTPException as e:
        return R.not_found(message=str(e.detail))
      
      if task['status'] != 'completed':
        return R.bad_request(
          message=f"任务未完成，当前状态: {task['status']}"
        )
      
      # 提取图片信息
      result = task.get('result', {})
      outputs_data = result.get('outputs') or \
        (result.get('result', {}).get('outputs') if result.get('result') else None)
      
      if not outputs_data:
        return R.not_found(message="任务结果中没有outputs数据")
      
      images = outputs_data.get('images', [])
      if not images:
        return R.not_found(message="任务没有生成图片")
      
      if index < 0 or index >= len(images):
        return R.bad_request(
          message=f"图片索引超出范围，共有 {len(images)} 张图片"
        )
      
      img_info = images[index]
      filename = img_info.get('filename')
      subfolder = img_info.get('subfolder', '')
      img_type = img_info.get('type', 'output')
      
      if not filename:
        return R.not_found(message="图片信息中缺少filename字段")
      
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        image_data = await client.async_get_image(filename, subfolder, img_type)
      
      return StreamingResponse(
        io.BytesIO(image_data),
        media_type="image/png",
        headers={
          "Content-Disposition": f"inline; filename={filename}",
          "X-Image-Index": str(index),
          "X-Total-Images": str(len(images))
        }
      )
      
    except Exception as e:
      logger.error(f"获取任务图片失败: {e}")
      logger.error(f"错误堆栈: {traceback.format_exc()}")
      return R.server_error(message=f"获取任务图片失败: {str(e)}")
  
  @router.get("/task/{task_id}/images")
  async def get_task_images_info(task_id: str):
    """获取任务的所有图片信息（不返回图片数据，只返回元数据）"""
    try:
      try:
        task = await _get_task_with_history(task_id)
      except HTTPException as e:
        if e.status_code == 404:
          return R.not_found(message=str(e.detail))
        else:
          return R.server_error(message=str(e.detail))
      
      if task['status'] != 'completed':
        return R.bad_request(
          message=f"任务未完成，当前状态: {task['status']}"
        )
      
      result = task.get('result', {})
      outputs_data = result.get('outputs') or \
        (result.get('result', {}).get('outputs') if result.get('result') else None)
      
      if not outputs_data:
        return R.not_found(message="任务结果中没有outputs数据")
      
      images = outputs_data.get('images', [])
      if not images:
        return R.success(
          data={
            "task_id": task_id,
            "total": 0,
            "images": []
          },
          message="该任务没有生成图片"
        )
      
      images_info = []
      for idx, img_info in enumerate(images):
        filename = img_info.get('filename', '')
        subfolder = img_info.get('subfolder', '')
        img_type = img_info.get('type', 'output')
        
        info = {
          "index": idx,
          "filename": filename,
          "subfolder": subfolder,
          "type": img_type,
          "url": f"/api/task/{task_id}/image?index={idx}",
          "direct_url": f"/api/image/{filename}?type={img_type}" + 
                       (f"&subfolder={subfolder}" if subfolder else "")
        }
        images_info.append(info)
      
      return R.success(
        data={
          "task_id": task_id,
          "total": len(images),
          "images": images_info
        },
        message="获取任务图片列表成功"
      )
      
    except Exception as e:
      logger.error(f"获取任务图片信息失败: {e}")
      return R.server_error(message=f"获取任务图片信息失败: {str(e)}")
  
  @router.get("/video/{filename}")
  async def get_video(filename: str, subfolder: str = "", type: str = "output"):
    """
    获取生成的视频（通用接口）
    
    Args:
      filename: 视频文件名
      subfolder: 子文件夹路径（可选）
      type: 文件类型 (output/input/temp)
    """
    try:
      logger.info(f"获取视频: filename={filename}, subfolder='{subfolder}', type={type}")
      
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        video_data = await client.async_get_image(filename, subfolder, type)
      
      # 根据文件扩展名确定MIME类型
      if filename.endswith('.mp4'):
        media_type = "video/mp4"
      elif filename.endswith('.webm'):
        media_type = "video/webm"
      elif filename.endswith('.gif'):
        media_type = "image/gif"
      else:
        media_type = "video/mp4"
      
      logger.info(f"视频获取成功: {filename}, 大小: {len(video_data)} bytes, MIME: {media_type}")
      
      return StreamingResponse(
        io.BytesIO(video_data),
        media_type=media_type,
        headers={
          "Content-Disposition": f"inline; filename={filename}",
          "Accept-Ranges": "bytes",
          "Content-Length": str(len(video_data)),
          "Cache-Control": "public, max-age=3600"
        }
      )
    except Exception as e:
      logger.error(f"获取视频失败: filename={filename}, subfolder='{subfolder}', type={type}")
      logger.error(f"错误详情: {str(e)}")
      logger.error(f"错误堆栈: {traceback.format_exc()}")
      # 对于流式响应接口，失败时应该抛出HTTPException
      raise HTTPException(status_code=404, detail=f"视频不存在或无法访问: {str(e)}")
  
  @router.get("/task/{task_id}/video")
  async def get_task_video(task_id: str, index: int = 0, final_only: bool = True):
    """
    根据任务ID直接获取输出视频
    
    参数:
      task_id: 任务ID
      index: 视频索引（默认0）
      final_only: 是否只返回最终视频（默认True）
    """
    try:
      try:
        task = await _get_task_with_history(task_id)
      except HTTPException as e:
        return R.not_found(message=str(e.detail))
      
      if task['status'] != 'completed':
        return R.bad_request(
          message=f"任务未完成，当前状态: {task['status']}"
        )
      
      result = task.get('result', {})
      outputs_data = result.get('outputs') or \
        (result.get('result', {}).get('outputs') if result.get('result') else None)
      
      if not outputs_data:
        return R.not_found(message="任务结果中没有outputs数据")
      
      # 提取视频
      all_videos, final_videos = _extract_videos(outputs_data)
      
      videos = final_videos if (final_only and final_videos) else all_videos
      
      if not videos:
        if final_only and all_videos:
          videos = all_videos
        else:
          return R.not_found(message="任务没有生成视频")
      
      if index < 0 or index >= len(videos):
        return R.bad_request(
          message=f"视频索引超出范围，共有 {len(videos)} 个视频"
        )
      
      video_info = videos[index]
      filename = video_info.get('filename')
      subfolder = video_info.get('subfolder', '')
      video_type = video_info.get('type', 'output')
      format_type = video_info.get('format', 'video/h264-mp4')
      
      if not filename:
        return R.not_found(message="视频信息中缺少filename字段")
      
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        video_data = await client.async_get_image(filename, subfolder, video_type)
      
      return StreamingResponse(
        io.BytesIO(video_data),
        media_type=format_type,
        headers={
          "Content-Disposition": f"inline; filename={filename}",
          "X-Video-Index": str(index),
          "X-Total-Videos": str(len(videos)),
          "X-Node-ID": video_info.get('node_id', ''),
          "X-Frame-Rate": str(video_info.get('frame_rate', 0))
        }
      )
      
    except Exception as e:
      logger.error(f"获取任务视频失败: {e}")
      logger.error(f"错误堆栈: {traceback.format_exc()}")
      return R.server_error(message=f"获取任务视频失败: {str(e)}")
  
  @router.get("/task/{task_id}/videos")
  async def get_task_videos_info(task_id: str, include_segments: bool = False):
    """
    获取任务的所有视频信息
    
    参数:
      task_id: 任务ID
      include_segments: 是否包含分段视频
    """
    try:
      try:
        task = await _get_task_with_history(task_id)
      except HTTPException as e:
        if e.status_code == 404:
          return R.not_found(message=str(e.detail))
        else:
          return R.server_error(message=str(e.detail))
      
      if task['status'] != 'completed':
        return R.bad_request(
          message=f"任务未完成，当前状态: {task['status']}"
        )
      
      result = task.get('result', {})
      outputs_data = result.get('outputs') or \
        (result.get('result', {}).get('outputs') if result.get('result') else None)
      
      if not outputs_data:
        return R.not_found(message="任务结果中没有outputs数据")
      
      all_videos, final_videos = _extract_videos(outputs_data)
      segment_videos = [v for v in all_videos if not v.get('subfolder')]
      
      if not all_videos:
        return R.success(
          data={
            "task_id": task_id,
            "total": 0,
            "final_videos": [],
            "segment_videos": [],
            "videos": []
          },
          message="该任务没有生成视频"
        )
      
      final_videos_info = _build_video_info_list(final_videos, task_id, 0)
      segment_videos_info = _build_video_info_list(
        segment_videos,
        task_id,
        len(final_videos)
      )
      
      if include_segments:
        all_videos_info = final_videos_info + segment_videos_info
      else:
        all_videos_info = final_videos_info if final_videos else segment_videos_info
      
      result = {
        "task_id": task_id,
        "total": len(all_videos_info),
        "final_videos": final_videos_info,
        "videos": all_videos_info
      }
      
      if include_segments:
        result["segment_videos"] = segment_videos_info
      
      return R.success(data=result, message="获取任务视频列表成功")
      
    except Exception as e:
      logger.error(f"获取任务视频信息失败: {e}")
      return R.server_error(message=f"获取任务视频信息失败: {str(e)}")
  
  @router.post("/upload/image")
  async def upload_image(file: UploadFile = File(...), 
                        subfolder: str = "", 
                        overwrite: bool = False):
    """
    上传图片到ComfyUI服务器的input文件夹
    
    图片会被保存到ComfyUI的input目录，LoadImage节点可以直接使用上传的文件名
    
    参数:
      file: 上传的图片文件
      subfolder: 子文件夹（可选，相对于input文件夹）
      overwrite: 是否覆盖已存在的文件
      
    返回:
      包含文件名、路径等信息的响应
    """
    try:
      # 验证文件类型
      allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif']
      if file.content_type not in allowed_types:
        return R.client_error(
          message=f"不支持的文件类型: {file.content_type}，仅支持: {', '.join(allowed_types)}"
        )
      
      # 读取文件数据
      image_data = await file.read()
      
      # 生成安全的文件名（避免中文编码问题）
      # 使用时间戳+UUID+原扩展名
      from pathlib import Path
      import uuid
      from datetime import datetime
      file_ext = Path(file.filename).suffix.lower()
      safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
      
      logger.info(f"开始上传图片: {file.filename} -> {safe_filename} ({len(image_data)} bytes)")
      
      # 上传到ComfyUI服务器（使用安全文件名）
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        result = await client.async_upload_image(
          image_data=image_data,
          filename=safe_filename,
          subfolder=subfolder,
          overwrite=overwrite
        )
      
      uploaded_filename = result.get('name', safe_filename)
      logger.info(f"图片上传成功: {uploaded_filename}")
      
      return R.success(
        data={
          "filename": uploaded_filename,
          "subfolder": result.get('subfolder', subfolder),
          "type": result.get('type', 'input'),
          "size": len(image_data),
          "original_filename": file.filename,
          "safe_filename": safe_filename
        },
        message="图片上传成功"
      )
      
    except Exception as e:
      logger.error(f"上传图片失败: {e}")
      logger.error(traceback.format_exc())
      return R.server_error(message=f"上传图片失败: {str(e)}")
  
  @router.post("/upload/video")
  async def upload_video(file: UploadFile = File(...), 
                        subfolder: str = "", 
                        overwrite: bool = True):
    """
    上传视频到ComfyUI服务器的input文件夹
    
    视频会被保存到ComfyUI的input目录，VHS_LoadVideo节点可以直接使用上传的文件名
    
    参数:
      file: 上传的视频文件
      subfolder: 子文件夹（可选，相对于input文件夹）
      overwrite: 是否覆盖已存在的文件（默认true）
      
    返回:
      包含文件名、路径等信息的响应
    """
    try:
      # 验证文件类型
      from pathlib import Path
      import uuid
      from datetime import datetime
      
      allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
      file_ext = Path(file.filename).suffix.lower()
      
      if file_ext not in allowed_extensions:
        return R.client_error(
          message=f"不支持的文件格式：{file_ext}，支持的格式：{', '.join(allowed_extensions)}"
        )
      
      # 读取文件数据
      video_data = await file.read()
      
      # 生成安全的文件名（避免中文编码问题）
      # 使用时间戳+UUID+原扩展名
      safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_ext}"
      
      logger.info(f"开始上传视频: {file.filename} -> {safe_filename} ({len(video_data)} bytes)")
      
      # 上传到ComfyUI服务器（使用安全文件名）
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        result = await client.async_upload_video(
          video_data=video_data,
          filename=safe_filename,
          subfolder=subfolder,
          overwrite=overwrite
        )
      
      uploaded_filename = result.get('name', safe_filename)
      logger.info(f"视频上传成功: {uploaded_filename}")
      
      return R.success(
        data={
          "filename": uploaded_filename,
          "subfolder": result.get('subfolder', subfolder),
          "type": result.get('type', 'input'),
          "size": len(video_data),
          "original_filename": file.filename,
          "safe_filename": safe_filename
        },
        message="视频上传成功"
      )
      
    except Exception as e:
      logger.error(f"上传视频失败: {e}")
      logger.error(traceback.format_exc())
      return R.server_error(message=f"上传视频失败: {str(e)}")
  
  return router


def _extract_videos(outputs_data: dict) -> tuple:
  """
  从 outputs 数据中提取视频
  
  Returns:
    (all_videos, final_videos) 元组
  """
  all_videos = []
  final_videos = []
  
  # 视频文件扩展名列表
  video_extensions = ('.mp4', '.webm', '.gif', '.avi', '.mov', '.mkv', '.m4v', '.flv')
  
  # 收集 other 数组中标记为 animated 的节点ID
  animated_nodes = set()
  if 'other' in outputs_data and isinstance(outputs_data['other'], list):
    for item in outputs_data['other']:
      if isinstance(item, dict):
        # 检查 type == 'animated' 的项
        if item.get('type') == 'animated':
          node_id = item.get('node_id', '')
          if node_id:
            animated_nodes.add(node_id)
        # 检查 type == 'gifs' 的项（保留原有逻辑）
        elif item.get('type') == 'gifs' and 'data' in item:
          node_id = item.get('node_id', '')
          for video_data in item['data']:
            video_item = {'node_id': node_id, **video_data}
            all_videos.append(video_item)
            if video_data.get('subfolder'):
              final_videos.append(video_item)
  
  # 检查 images 数组中的视频文件（通过扩展名或 animated 标记识别）
  if 'images' in outputs_data and isinstance(outputs_data['images'], list):
    for img_data in outputs_data['images']:
      if isinstance(img_data, dict):
        filename = img_data.get('filename', '').lower()
        node_id = img_data.get('node_id', '')
        
        # 判断是否为视频文件：文件扩展名是视频格式 或 节点被标记为 animated
        is_video = any(filename.endswith(ext) for ext in video_extensions)
        is_animated = node_id in animated_nodes
        
        if is_video or is_animated:
          video_item = {
            'node_id': node_id,
            'filename': img_data.get('filename'),
            'subfolder': img_data.get('subfolder', ''),
            'type': img_data.get('type', 'output')
          }
          all_videos.append(video_item)
          # 有 subfolder 的视为最终视频
          if video_item['subfolder']:
            final_videos.append(video_item)
  
  # 检查各节点的gifs字段（保留原有逻辑）
  for node_id, output in outputs_data.items():
    if isinstance(output, dict) and 'gifs' in output:
      gifs = output['gifs']
      if isinstance(gifs, list):
        for gif_data in gifs:
          video_item = {'node_id': node_id, **gif_data}
          all_videos.append(video_item)
          if gif_data.get('subfolder'):
            final_videos.append(video_item)
  
  return all_videos, final_videos


def _build_video_info_list(videos_list: list, task_id: str, base_index: int) -> list:
  """构建视频信息列表"""
  info_list = []
  for idx, video_info in enumerate(videos_list):
    filename = video_info.get('filename', '')
    subfolder = video_info.get('subfolder', '')
    video_type = video_info.get('type', 'output')
    
    info = {
      "index": base_index + idx,
      "node_id": video_info.get('node_id', ''),
      "filename": filename,
      "subfolder": subfolder,
      "type": video_type,
      "format": video_info.get('format', 'video/h264-mp4'),
      "frame_rate": video_info.get('frame_rate', 0),
      "is_final": bool(subfolder),
      "url": f"/api/task/{task_id}/video?index={base_index + idx}&final_only=false",
      "direct_url": f"/api/video/{filename}?type={video_type}" + 
                   (f"&subfolder={subfolder}" if subfolder else "")
    }
    info_list.append(info)
  return info_list

