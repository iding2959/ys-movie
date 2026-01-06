"""
文生图相关接口
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from core.comfyui_client import ComfyUIClient
from core.models import SimpleText2ImageRequest, TaskResponse
from core.managers import TaskManager, ConnectionManager
from core.response import R, ResponseModel
from pathlib import Path
import json
import logging
import random
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["文生图"])


def setup_text2image_routes(
  comfyui_server: str,
  task_manager: TaskManager,
  connection_manager: ConnectionManager,
  workflow_dir: Path,
  protocol: str = "http",
  ws_protocol: str = "ws"
):
  """
  设置文生图路由
  
  Args:
    comfyui_server: ComfyUI 服务器地址
    task_manager: 任务管理器实例
    connection_manager: WebSocket 连接管理器实例
    protocol: HTTP协议
    ws_protocol: WebSocket协议
    workflow_dir: 工作流文件目录
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
        "error": error_msg,
        "failed_at": datetime.now().isoformat()
      })
      
      # 广播失败消息
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "failed",
        "error": error_msg
      }))
  
  @router.post("/text2image", response_model=ResponseModel)
  async def simple_text2image(
    data: SimpleText2ImageRequest,
    background_tasks: BackgroundTasks
  ):
    """
    简化的文生图接口（Qwen Image Distill）
    
    ## 功能说明
    基于 Qwen Image Distill 模型的文生图接口，支持1K/2K双流程智能切换
    
    ## 参数说明
    
    ### 必填参数
    - **prompt**: 正向提示词
    
    ### 尺寸设置（二选一）
    
    **📌 重要说明：** 如果设置了aspect_ratio预设值（非custom），width和height参数会被自动忽略
    
    **方式1：使用比例预设（推荐）✨**
    - **aspect_ratio**: 选择预设比例，自动设置宽高
    - ⚠️ 此时无需（也不应）指定width/height，即使指定了也会被忽略
      
      可选值：
      - **标准比例**
        - `1280x720` - 标准1K横屏 (1280×720, 1K直出)
        - `720x1280` - 标准1K竖屏 (720×1280, 2K放大)
        - `2560x1440` - 标准2K横屏 (2560×1440, 2K放大)
        - `1440x2560` - 标准2K竖屏 (1440×2560, 2K放大)
      
      - **超宽屏 21:9**
        - `1512x648` - 21:9-1K横屏 (1512×648, 1K直出)
        - `2560x1080` - 21:9-2K横屏 (2560×1080, 2K放大)
        - `464x1080` - 9:21-1K竖屏 (464×1080, 1K直出)
        - `1080x2560` - 9:21-2K竖屏 (1080×2560, 2K放大)
      
      - **全高清 16:9**
        - `1536x864` - 16:9-1K横屏 (1536×864, 1K直出)
        - `1920x1080` - 16:9-2K横屏 (1920×1080, 2K放大)
        - `608x1080` - 9:16-1K竖屏 (608×1080, 1K直出)
        - `1080x1920` - 9:16-2K竖屏 (1080×1920, 2K放大)
      
      - **传统比例 4:3**
        - `1024x768` - 4:3横屏 (1024×768, 1K直出)
        - `768x1024` - 3:4竖屏 (768×1024, 1K直出)
        - `2048x1536` - 4:3-2K横屏 (2048×1536, 2K放大)
        - `1536x2048` - 3:4-2K竖屏 (1536×2048, 2K放大)
      
      - **方形 1:1**
        - `1080x1080` - 1:1方形 (1080×1080, 1K直出)
        - `2160x2160` - 1:1-2K方形 (2160×2160, 2K放大)
    
    **方式2：自定义尺寸**
    - 设置 `aspect_ratio` = `"custom"` 并指定 `width` 和 `height`
    - **width**: 图像宽度（像素），范围：256-2560
    - **height**: 图像高度（像素），范围：256-2560
    
    ### 其他可选参数
    - **negative_prompt**: 负向提示词（已有默认值）
    - **steps**: 采样步数（默认10，范围：1-100）
    - **seed**: 随机种子（默认-1表示随机）
    
    ## 流程说明
    - **1K直出流程**（宽度≤1536且高度≤1080）：直接生成目标尺寸，速度快
    - **2K放大流程**（超过阈值）：先生成基础图再4x放大+resize，质量更高
    
    ## 使用示例
    
    **示例1：使用预设比例（最简单，推荐）✨**
    ```json
    {
      "prompt": "A beautiful landscape with mountains",
      "aspect_ratio": "1920x1080"
    }
    ```
    ✅ 自动使用1920×1080尺寸（16:9-2K横屏）
    
    **示例2：自定义尺寸**
    ```json
    {
      "prompt": "A beautiful landscape with mountains",
      "aspect_ratio": "custom",
      "width": 1600,
      "height": 900
    }
    ```
    ✅ 使用自定义的1600×900尺寸
    
    **示例3：完整参数**
    ```json
    {
      "prompt": "A beautiful landscape with mountains at sunset",
      "negative_prompt": "blurry, low quality",
      "aspect_ratio": "2560x1440",
      "steps": 15,
      "seed": 12345
    }
    ```
    ✅ 使用标准2K横屏，指定步数和种子
    
    **⚠️ 错误示例（不推荐）**
    ```json
    {
      "prompt": "A beautiful landscape",
      "aspect_ratio": "1920x1080",
      "width": 1600,
      "height": 900
    }
    ```
    ❌ width和height会被忽略，实际使用1920×1080
    
    **正确做法：**
    - 要么只用aspect_ratio预设
    - 要么设置aspect_ratio="custom"并指定width/height
    
    ## 返回信息
    返回任务ID和完整的尺寸、比例、流程信息，可通过WebSocket或轮询获取结果
    """
    try:
      # 加载默认工作流
      workflow_file = workflow_dir / "qwen_t2i_distill.json"
      if not workflow_file.exists():
        raise HTTPException(
          status_code=404,
          detail="工作流文件不存在，请确保 workflows/qwen_t2i_distill.json 存在"
        )
      
      with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
      
      # 比例预设映射
      aspect_ratio_presets = {
        # 标准1K横竖屏
        '1280x720': (1280, 720, '标准1K横屏'),
        '720x1280': (720, 1280, '标准1K竖屏'),
        # 标准2K横竖屏
        '2560x1440': (2560, 1440, '标准2K横屏'),
        '1440x2560': (1440, 2560, '标准2K竖屏'),
        # 21:9 / 9:21 超宽屏
        '1512x648': (1512, 648, '21:9-1K横屏'),
        '2560x1080': (2560, 1080, '21:9-2K横屏'),
        '464x1080': (464, 1080, '9:21-1K竖屏'),
        '1080x2560': (1080, 2560, '9:21-2K竖屏'),
        # 16:9 / 9:16 全高清
        '1536x864': (1536, 864, '16:9-1K横屏'),
        '1920x1080': (1920, 1080, '16:9-2K横屏'),
        '608x1080': (608, 1080, '9:16-1K竖屏'),
        '1080x1920': (1080, 1920, '9:16-2K竖屏'),
        # 4:3 / 3:4 传统比例
        '1024x768': (1024, 768, '4:3横屏'),
        '768x1024': (768, 1024, '3:4竖屏'),
        '2048x1536': (2048, 1536, '4:3-2K横屏'),
        '1536x2048': (1536, 2048, '3:4-2K竖屏'),
        # 1:1 方形
        '1080x1080': (1080, 1080, '1:1方形'),
        '2160x2160': (2160, 2160, '1:1-2K方形')
      }
      
      # 处理比例预设（如果提供了aspect_ratio且不是custom，则使用预设值）
      # 优先级：aspect_ratio预设 > custom(使用width/height)
      final_width = data.width
      final_height = data.height
      ratio_info = "自定义"
      
      if data.aspect_ratio and data.aspect_ratio != 'custom':
        if data.aspect_ratio in aspect_ratio_presets:
          preset = aspect_ratio_presets[data.aspect_ratio]
          final_width, final_height, ratio_info = preset
          logger.info(f"📐 使用预设比例: {ratio_info} ({final_width}x{final_height})")
          if data.width != 1280 or data.height != 720:
            logger.info(f"   ℹ️ 忽略用户提供的width({data.width})和height({data.height})，使用预设值")
        else:
          logger.warning(f"⚠️ 未知的aspect_ratio值: {data.aspect_ratio}，使用width/height参数")
          ratio_info = f"自定义 ({final_width}x{final_height})"
      else:
        ratio_info = f"自定义 ({final_width}x{final_height})"
        logger.info(f"📐 使用自定义尺寸: {final_width}x{final_height}")
      
      # 处理seed（-1转为随机值）
      seed = data.seed
      if seed < 0:
        seed = random.randint(0, 18446744073709551615)
        logger.info(f"🎲 生成随机种子: {seed}")
      
      # 判断是否需要2K流程（放大+resize）
      # 阈值：宽度>1536 或 高度>1080 则使用2K流程
      use_2k_pipeline = final_width > 1536 or final_height > 1080
      
      # 计算基础生成尺寸
      if use_2k_pipeline:
        # 2K流程：生成1K基础图，再放大
        base_width = final_width // 2
        base_height = final_height // 2
        logger.info(f"🔍 使用2K流程: 基础尺寸 {base_width}x{base_height} -> 放大 -> 目标尺寸 {final_width}x{final_height}")
      else:
        # 1K流程：直接生成目标尺寸
        base_width = final_width
        base_height = final_height
        logger.info(f"📐 使用1K流程: 直接生成 {final_width}x{final_height}")
      
      # 更新工作流参数
      if "76" in workflow and "inputs" in workflow["76"]:
        workflow["76"]["inputs"]["text"] = data.prompt
      
      if "7" in workflow and "inputs" in workflow["7"]:
        workflow["7"]["inputs"]["text"] = data.negative_prompt
      
      if "3" in workflow and "inputs" in workflow["3"]:
        workflow["3"]["inputs"]["seed"] = seed
        workflow["3"]["inputs"]["steps"] = data.steps
      
      if "72" in workflow and "inputs" in workflow["72"]:
        workflow["72"]["inputs"]["width"] = base_width
        workflow["72"]["inputs"]["height"] = base_height
      
      # 根据流程调整节点配置
      if use_2k_pipeline:
        # 2K流程：启用放大和resize节点
        if "99" in workflow and "inputs" in workflow["99"]:
          workflow["99"]["inputs"]["target_width"] = final_width
          workflow["99"]["inputs"]["target_height"] = final_height
        
        # 确保SaveImage节点从ResizeAndPadImage获取图像
        if "101" in workflow and "inputs" in workflow["101"]:
          workflow["101"]["inputs"]["images"] = ["99", 0]
      else:
        # 1K流程：禁用放大和resize，直接保存VAE解码输出
        # 删除放大和resize节点
        if "94" in workflow:
          del workflow["94"]
        if "95" in workflow:
          del workflow["95"]
        if "99" in workflow:
          del workflow["99"]
        
        # SaveImage节点直接从VAEDecode获取图像
        if "101" in workflow and "inputs" in workflow["101"]:
          workflow["101"]["inputs"]["images"] = ["8", 0]
      
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
        "workflow_type": "text2image",
        "params": {
          "prompt": data.prompt,
          "negative_prompt": data.negative_prompt,
          "aspect_ratio": data.aspect_ratio or "custom",
          "ratio_info": ratio_info,
          "seed": seed,
          "steps": data.steps,
          "width": final_width,
          "height": final_height,
          "base_width": base_width if use_2k_pipeline else None,
          "base_height": base_height if use_2k_pipeline else None
        }
      })
      
      # 在后台等待任务完成
      background_tasks.add_task(wait_for_completion, prompt_id, 600)
      
      pipeline_type = "2K放大流程" if use_2k_pipeline else "1K直出流程"
      logger.info(f"📝 简化文生图任务已提交: {prompt_id}")
      logger.info(f"   提示词: {data.prompt[:50]}...")
      logger.info(f"   比例: {ratio_info}")
      logger.info(f"   流程: {pipeline_type}")
      logger.info(f"   目标尺寸: {final_width}x{final_height}, 步数: {data.steps}, 种子: {seed}")
      if use_2k_pipeline:
        logger.info(f"   基础尺寸: {base_width}x{base_height}")
      
      return R.success(
        data={
          "task_id": prompt_id,
          "status": "submitted",
          "seed": seed,
          "aspect_ratio": data.aspect_ratio or "custom",
          "ratio_info": ratio_info,
          "pipeline": pipeline_type,
          "width": final_width,
          "height": final_height,
          "target_size": f"{final_width}x{final_height}",
          "base_size": f"{base_width}x{base_height}" if use_2k_pipeline else None
        },
        message=f"任务已提交({pipeline_type})，比例: {ratio_info}，种子值: {seed}"
      )
      
    except Exception as e:
      logger.error(f"简化文生图接口错误: {e}")
      logger.error(f"错误堆栈: {traceback.format_exc()}")
      return R.server_error(message=f"文生图任务提交失败: {str(e)}")
  
  return router

