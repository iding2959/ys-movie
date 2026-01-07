"""
工作流管理相关接口
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from core.comfyui_client import ComfyUIClient
from core.models import WorkflowSubmit, WorkflowUpdate, TaskResponse
from core.managers import TaskManager, ConnectionManager
from core.utils import apply_params_to_workflow, apply_random_seeds
from core.response import R, ResponseModel
from pathlib import Path
from datetime import datetime
import json
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["工作流管理"])


def setup_workflow_routes(
  comfyui_server: str,
  task_manager: TaskManager,
  connection_manager: ConnectionManager,
  workflow_dir: Path,
  protocol: str = "http",
  ws_protocol: str = "ws"
):
  """
  设置工作流管理路由
  
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
    try:
      task_manager.update_task(prompt_id, {"status": "running"})
      
      await connection_manager.broadcast(json.dumps({
        "type": "task_update",
        "task_id": prompt_id,
        "status": "running"
      }))
      
      logger.info(f"开始等待任务完成: {prompt_id}")
      
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
      logger.error(f"执行任务 {prompt_id} 失败: {e}")
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
  
  @router.post("/workflow/submit", response_model=ResponseModel)
  async def submit_workflow(
    data: WorkflowSubmit,
    background_tasks: BackgroundTasks
  ):
    """提交工作流任务（完整版）"""
    try:
      # 应用动态参数到工作流
      workflow = data.workflow
      if data.params:
        workflow = apply_params_to_workflow(workflow, data.params)
      
      # 补全随机种子
      apply_random_seeds(workflow)
      
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
        "workflow_type": "custom",
        "params": data.params
      })
      
      # 在后台等待任务完成
      background_tasks.add_task(wait_for_completion, prompt_id, data.timeout)
      
      logger.info(f"📝 工作流任务已提交: {prompt_id}")
      
      return R.success(
        data={
          "task_id": prompt_id,
          "status": "submitted"
        },
        message="任务已提交到队列"
      )
    except Exception as e:
      logger.error(f"提交工作流失败: {e}")
      return R.server_error(message=f"提交工作流失败: {str(e)}")
  
  @router.post("/workflow/upload")
  async def upload_workflow(file: UploadFile = File(...)):
    """上传工作流文件（仅接受API格式）"""
    if not file.filename.endswith('.json'):
      raise HTTPException(
        status_code=400,
        detail="只支持JSON格式的工作流文件"
      )
    
    file_path = workflow_dir / file.filename
    content = await file.read()
    
    try:
      # 验证JSON格式
      workflow = json.loads(content)
      if 'nodes' in workflow and isinstance(workflow['nodes'], list):
        raise HTTPException(
          status_code=400,
          detail="仅支持API格式工作流（键为节点ID的字典），UI格式已不再支持"
        )
      
      # 保存到文件
      with open(file_path, 'wb') as f:
        f.write(content)
      
      return R.success(
        data={
          "filename": file.filename,
          "path": str(file_path),
          "nodes": len(workflow),
          "format": "API",
          "workflow": workflow
        },
        message="工作流上传成功"
      )
    except json.JSONDecodeError:
      return R.client_error(message="无效的JSON格式")
    except Exception as e:
      logger.error(f"处理工作流文件失败: {e}")
      return R.server_error(message=f"处理工作流失败: {str(e)}")
  
  @router.get("/workflows")
  async def list_workflows():
    """列出所有保存的工作流"""
    workflows = []
    for file_path in workflow_dir.glob("*.json"):
      try:
        with open(file_path, 'r', encoding='utf-8') as f:
          workflow = json.load(f)
          workflows.append({
            "filename": file_path.name,
            "path": str(file_path),
            "nodes": len(workflow),
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
          })
      except:
        continue
    
    return R.success(
      data={"total": len(workflows), "workflows": workflows},
      message="获取工作流列表成功"
    )
  
  @router.get("/workflow/{filename}")
  async def get_workflow(filename: str):
    """获取指定工作流"""
    file_path = workflow_dir / filename
    if not file_path.exists():
      return R.not_found(message="工作流文件不存在")
    
    try:
      with open(file_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
      return R.success(
        data={
          "filename": filename,
          "workflow": workflow
        },
        message="获取工作流成功"
      )
    except Exception as e:
      return R.server_error(message=f"读取工作流失败: {str(e)}")
  
  @router.post("/workflow/update")
  async def update_workflow_node(data: WorkflowUpdate):
    """更新工作流中的节点参数"""
    workflow = data.workflow
    node_id = data.node_id
    updates = data.updates
    
    if node_id not in workflow:
      return R.not_found(message=f"节点 {node_id} 不存在")
    
    # 更新节点参数
    if "inputs" in workflow[node_id]:
      workflow[node_id]["inputs"].update(updates)
    else:
      workflow[node_id]["inputs"] = updates
    
    return R.success(
      data={
        "success": True,
        "workflow": workflow,
        "updated_node": node_id
      },
      message="工作流节点更新成功"
    )
  
  return router

