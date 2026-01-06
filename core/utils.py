"""
工具函数
"""
from typing import Dict, Any
import copy


def apply_params_to_workflow(
  workflow: Dict[str, Any],
  params: Dict[str, Any]
) -> Dict[str, Any]:
  """
  将动态参数应用到工作流
  
  参数格式支持两种方式:
  1. "node_id.input_name": value - 精确指定节点和输入
  2. "input_name": value - 在所有节点中查找匹配的输入名
  
  Args:
    workflow: 原始工作流字典
    params: 参数字典
    
  Returns:
    应用参数后的工作流副本
    
  Example:
    >>> workflow = {
    ...   "1": {"inputs": {"seed": 0}},
    ...   "2": {"inputs": {"text": "hello"}}
    ... }
    >>> params = {"1.seed": 42, "text": "world"}
    >>> result = apply_params_to_workflow(workflow, params)
  """
  workflow_copy = copy.deepcopy(workflow)
  
  for key, value in params.items():
    if "." in key:
      # 格式: node_id.input_name
      node_id, input_name = key.split(".", 1)
      if node_id in workflow_copy and "inputs" in workflow_copy[node_id]:
        workflow_copy[node_id]["inputs"][input_name] = value
    else:
      # 格式: input_name - 在所有节点中查找
      for node_id, node_data in workflow_copy.items():
        if "inputs" in node_data and key in node_data["inputs"]:
          node_data["inputs"][key] = value
  
  return workflow_copy

