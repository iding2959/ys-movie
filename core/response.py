"""
统一响应包装类
提供标准化的API响应格式
"""
from typing import Optional, Any, Generic, TypeVar
from pydantic import BaseModel, Field


T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
  """
  统一响应模型
  
  Attributes:
    code: 业务状态码 (200: 成功, 400: 客户端错误, 500: 服务器错误)
    success: 是否成功
    message: 响应消息
    data: 响应数据
  """
  code: int = Field(default=200, description="业务状态码")
  success: bool = Field(default=True, description="是否成功")
  message: str = Field(default="操作成功", description="响应消息")
  data: Optional[T] = Field(default=None, description="响应数据")
  
  class Config:
    json_schema_extra = {
      "example": {
        "code": 200,
        "success": True,
        "message": "操作成功",
        "data": {"key": "value"}
      }
    }


class Response:
  """
  响应工具类
  提供快捷方法创建统一格式的响应
  """
  
  @staticmethod
  def success(
    data: Any = None,
    message: str = "操作成功",
    code: int = 200
  ) -> ResponseModel:
    """
    成功响应
    
    Args:
      data: 响应数据
      message: 响应消息
      code: 状态码
      
    Returns:
      ResponseModel 实例
      
    Example:
      >>> Response.success(data={"user_id": 123}, message="用户创建成功")
    """
    return ResponseModel(
      code=code,
      success=True,
      message=message,
      data=data
    )
  
  @staticmethod
  def error(
    message: str = "操作失败",
    code: int = 500,
    data: Any = None
  ) -> ResponseModel:
    """
    错误响应
    
    Args:
      message: 错误消息
      code: 错误码
      data: 额外数据
      
    Returns:
      ResponseModel 实例
      
    Example:
      >>> Response.error(message="用户不存在", code=404)
    """
    return ResponseModel(
      code=code,
      success=False,
      message=message,
      data=data
    )
  
  @staticmethod
  def client_error(
    message: str = "请求参数错误",
    data: Any = None
  ) -> ResponseModel:
    """
    客户端错误响应 (400)
    
    Args:
      message: 错误消息
      data: 额外数据
      
    Returns:
      ResponseModel 实例
    """
    return ResponseModel(
      code=400,
      success=False,
      message=message,
      data=data
    )
  
  @staticmethod
  def bad_request(
    message: str = "请求参数错误",
    data: Any = None
  ) -> ResponseModel:
    """
    错误请求响应 (400) - client_error 的别名
    
    Args:
      message: 错误消息
      data: 额外数据
      
    Returns:
      ResponseModel 实例
    """
    return ResponseModel(
      code=400,
      success=False,
      message=message,
      data=data
    )
  
  @staticmethod
  def not_found(
    message: str = "资源不存在",
    data: Any = None
  ) -> ResponseModel:
    """
    资源不存在响应 (404)
    
    Args:
      message: 错误消息
      data: 额外数据
      
    Returns:
      ResponseModel 实例
    """
    return ResponseModel(
      code=404,
      success=False,
      message=message,
      data=data
    )
  
  @staticmethod
  def server_error(
    message: str = "服务器内部错误",
    data: Any = None
  ) -> ResponseModel:
    """
    服务器错误响应 (500)
    
    Args:
      message: 错误消息
      data: 额外数据
      
    Returns:
      ResponseModel 实例
    """
    return ResponseModel(
      code=500,
      success=False,
      message=message,
      data=data
    )
  
  @staticmethod
  def unauthorized(
    message: str = "未授权访问",
    data: Any = None
  ) -> ResponseModel:
    """
    未授权响应 (401)
    
    Args:
      message: 错误消息
      data: 额外数据
      
    Returns:
      ResponseModel 实例
    """
    return ResponseModel(
      code=401,
      success=False,
      message=message,
      data=data
    )
  
  @staticmethod
  def forbidden(
    message: str = "禁止访问",
    data: Any = None
  ) -> ResponseModel:
    """
    禁止访问响应 (403)
    
    Args:
      message: 错误消息
      data: 额外数据
      
    Returns:
      ResponseModel 实例
    """
    return ResponseModel(
      code=403,
      success=False,
      message=message,
      data=data
    )


# 便捷别名
class R(Response):
  """Response 类的简短别名"""
  pass

