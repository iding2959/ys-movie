"""
系统信息相关接口
"""
from fastapi import APIRouter, HTTPException
from core.comfyui_client import ComfyUIClient
from core.models import SystemInfo
from core.response import R
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["系统信息"])


def setup_system_routes(comfyui_server: str, protocol: str = "http", 
                       ws_protocol: str = "ws"):
  """
  设置系统路由，注入依赖
  
  Args:
    comfyui_server: ComfyUI 服务器地址
    protocol: HTTP协议
    ws_protocol: WebSocket协议
  """
  # 创建客户端实例（在路由级别共享）
  client = ComfyUIClient(comfyui_server, protocol, ws_protocol)
  
  @router.get("/health")
  async def health_check():
    """健康检查"""
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        stats = await client.async_get_system_stats()
        return R.success(
          data={
            "status": "healthy",
            "comfyui_server": comfyui_server,
            "comfyui_url": f"{protocol}://{comfyui_server}",
            "comfyui_status": "connected",
            "system_stats": stats
          },
          message="系统健康"
        )
    except Exception as e:
      return R.error(
        message="系统不健康",
        code=503,
        data={
          "status": "unhealthy",
          "comfyui_server": comfyui_server,
          "comfyui_url": f"{protocol}://{comfyui_server}",
          "comfyui_status": "disconnected",
          "error": str(e)
        }
      )
  
  @router.get("/system/info")
  async def get_system_info():
    """获取系统信息"""
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        stats = await client.async_get_system_stats()
        return R.success(
          data={
            "comfyui_server": comfyui_server,
            "status": "connected",
            "stats": stats
          },
          message="获取系统信息成功"
        )
    except Exception as e:
      return R.error(
        message=f"无法连接到ComfyUI服务器: {str(e)}",
        code=503
      )
  
  @router.get("/diagnose")
  async def diagnose():
    """诊断系统状态"""
    from datetime import datetime
    
    diagnostics = {
      "comfyui_server": comfyui_server,
      "timestamp": datetime.now().isoformat(),
      "checks": {}
    }
    
    async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
      # 检查健康状态
      try:
        health = await client.async_get_system_stats()
        diagnostics["checks"]["system_stats"] = {"status": "ok", "data": health}
      except Exception as e:
        diagnostics["checks"]["system_stats"] = {"status": "failed", "error": str(e)}
      
      # 检查队列
      try:
        queue = await client.async_get_queue()
        diagnostics["checks"]["queue"] = {"status": "ok", "data": queue}
      except Exception as e:
        diagnostics["checks"]["queue"] = {"status": "failed", "error": str(e)}
      
      # 检查节点信息
      try:
        nodes = await client.async_get_object_info()
        diagnostics["checks"]["nodes"] = {"status": "ok", "count": len(nodes)}
      except Exception as e:
        diagnostics["checks"]["nodes"] = {"status": "failed", "error": str(e)}
    
    return R.success(data=diagnostics, message="系统诊断完成")
  
  @router.get(
    "/nodes",
    summary="获取所有可用节点信息",
    description="获取ComfyUI的所有节点定义。注意：返回数据量较大，建议使用API客户端而非浏览器直接访问。",
    response_description="节点信息列表",
    responses={
      200: {
        "description": "成功获取节点信息",
        "content": {
          "application/json": {
            "example": {
              "code": 200,
              "success": True,
              "message": "获取节点信息成功",
              "data": {
                "total": 100,
                "nodes": {
                  "KSampler": {
                    "input": {"required": {}, "optional": {}},
                    "output": ["LATENT"],
                    "category": "sampling"
                  }
                }
              }
            }
          }
        }
      }
    }
  )
  async def get_nodes():
    """获取所有可用节点信息（数据量较大）"""
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        nodes = await client.async_get_object_info()
        return R.success(
          data={
            "total": len(nodes),
            "nodes": nodes
          },
          message="获取节点信息成功"
        )
    except Exception as e:
      return R.server_error(message=f"获取节点信息失败: {str(e)}")
  
  @router.get("/nodes/list")
  async def get_nodes_list():
    """获取节点名称列表（轻量级，不包含详细信息）"""
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        nodes = await client.async_get_object_info()
        # 只返回节点名称和分类
        node_list = []
        for node_name, node_info in nodes.items():
          node_list.append({
            "name": node_name,
            "category": node_info.get("category", "unknown"),
            "display_name": node_info.get("display_name", node_name)
          })
        
        return R.success(
          data={
            "total": len(node_list),
            "nodes": node_list
          },
          message="获取节点列表成功"
        )
    except Exception as e:
      return R.server_error(message=f"获取节点列表失败: {str(e)}")
  
  @router.get("/queue")
  async def get_queue():
    """获取队列状态"""
    try:
      async with ComfyUIClient(comfyui_server, protocol, ws_protocol) as client:
        queue = await client.async_get_queue()
        return R.success(data=queue, message="获取队列状态成功")
    except Exception as e:
      return R.server_error(message=f"获取队列状态失败: {str(e)}")
  
  @router.post("/queue/clear")
  async def clear_queue():
    """清空队列"""
    try:
      # 注意: clear_queue 是同步方法
      client = ComfyUIClient(comfyui_server, protocol, ws_protocol)
      success = client.clear_queue()
      return R.success(
        data={"success": success},
        message="清空队列成功" if success else "清空队列失败"
      )
    except Exception as e:
      return R.server_error(message=f"清空队列失败: {str(e)}")
  
  @router.post("/interrupt/{prompt_id}")
  async def interrupt_task(prompt_id: str):
    """中断指定任务"""
    try:
      # 注意: interrupt 是同步方法
      client = ComfyUIClient(comfyui_server, protocol, ws_protocol)
      success = client.interrupt(prompt_id)
      return R.success(
        data={"success": success, "prompt_id": prompt_id},
        message="任务中断成功" if success else "任务中断失败"
      )
    except Exception as e:
      return R.server_error(message=f"中断任务失败: {str(e)}")
  
  return router

