"""
Pydantic 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class WorkflowSubmit(BaseModel):
  """工作流提交模型"""
  workflow: Dict[str, Any] = Field(..., description="工作流JSON数据")
  params: Optional[Dict[str, Any]] = Field(None, description="动态参数")
  timeout: Optional[int] = Field(600, description="超时时间（秒）")


class WorkflowUpdate(BaseModel):
  """工作流更新模型"""
  workflow: Dict[str, Any] = Field(..., description="工作流JSON数据")
  node_id: str = Field(..., description="要更新的节点ID")
  updates: Dict[str, Any] = Field(..., description="更新的参数")


class TaskResponse(BaseModel):
  """任务响应模型"""
  task_id: str
  status: str
  message: Optional[str] = None
  result: Optional[Dict[str, Any]] = None


class SystemInfo(BaseModel):
  """系统信息模型"""
  comfyui_server: str
  status: str
  stats: Optional[Dict[str, Any]] = None


class SimpleText2ImageRequest(BaseModel):
  """
  简化的文生图请求模型
  
  尺寸设置方式：
  1. 使用预设比例（推荐）：设置aspect_ratio为预设值，width/height会被忽略
  2. 自定义尺寸：设置aspect_ratio="custom"，然后指定width和height
  """
  prompt: str = Field(
    ..., 
    description="✍️ 正向提示词（必填）", 
    min_length=1,
    examples=["A beautiful landscape with mountains at sunset"]
  )
  
  negative_prompt: Optional[str] = Field(
    # 质量问题
    "low quality, worst quality, low resolution, blurry, blur, out of focus, "
    "bokeh, grainy, noisy, pixelated, jpeg artifacts, compression artifacts, "
    "watermark, text, logo, signature, username, artist name, "
    # 解剖和比例问题
    "bad anatomy, bad proportions, deformed, disfigured, mutated, mutation, "
    "extra limbs, extra fingers, extra arms, extra legs, missing limbs, "
    "missing fingers, fused fingers, too many fingers, long neck, long body, "
    "malformed hands, poorly drawn hands, poorly drawn face, ugly face, "
    "cropped, cut off, cloned face, duplicate, "
    # 风格问题
    "cartoon, anime, illustration, painting, drawing, sketch, 3d render, cgi, "
    "unrealistic, artificial, synthetic, fake, "
    # 皮肤和修图问题
    "overly smooth skin, plastic skin, airbrushed, beauty filter, "
    "over-processed, over-edited, over-saturated, overexposed, underexposed, "
    # 表情和姿态问题
    "stiff expression, awkward pose, unnatural pose, tiling, repetitive, "
    # AI生成痕迹
    "ai-generated look, digital art style, stylized, abstract, "
    # 其他常见问题
    "monochrome, black and white, error, gross, disgusting, morbid",
    description="🚫 负向提示词（可选，已有默认值）"
  )
  
  aspect_ratio: Optional[str] = Field(
    "1280x720",
    description=(
      "📐 图片比例预设（选择预设后width/height会被忽略）\n"
      "标准：1280x720|720x1280|2560x1440|1440x2560\n"
      "21:9：1512x648|2560x1080|464x1080|1080x2560\n"
      "16:9：1536x864|1920x1080|608x1080|1080x1920\n"
      "4:3：1024x768|768x1024|2048x1536|1536x2048\n"
      "1:1：1080x1080|2160x2160\n"
      "自定义：custom（需指定width和height）"
    ),
    examples=["1920x1080", "2560x1440", "1080x1920", "custom"]
  )
  
  width: Optional[int] = Field(
    1280,
    description="📏 图像宽度（仅当aspect_ratio=custom时生效，否则被忽略）",
    ge=256,
    le=2560
  )
  
  height: Optional[int] = Field(
    720,
    description="📐 图像高度（仅当aspect_ratio=custom时生效，否则被忽略）",
    ge=256,
    le=2560
  )
  
  steps: Optional[int] = Field(
    10, 
    description="🎯 采样步数（默认10）", 
    ge=1, 
    le=100
  )
  
  seed: Optional[int] = Field(
    -1, 
    description="🎲 随机种子（-1表示随机）",
    examples=[-1, 12345, 67890]
  )

