"""
工具函数
"""
from typing import Dict, Any
import copy
import random


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


def generate_seed() -> int:
  """
  生成随机种子，避免工作流被跳过
  
  注意：ComfyUI 的 FlashVSR 节点限制种子最大值为 2^50 (1125899906842624)
  使用 2^50 作为上限以确保兼容性
  
  Returns:
    1 到 2^50 之间的随机整数
  """
  return random.randint(1, 2 ** 50)


def apply_random_seeds(workflow: dict):
  """
  为存在seed字段且为空/零的节点填充随机种子，避免被跳过
  
  注意：ComfyUI 的某些节点（如 FlashVSR）限制种子最大值为 2^50 (1125899906842624)
  使用 2^50 作为上限以确保兼容性
  
  Args:
    workflow: 工作流字典，会被原地修改
  """
  for node in workflow.values():
    if not isinstance(node, dict):
      continue
    inputs = node.get("inputs")
    if not isinstance(inputs, dict):
      continue
    if "seed" in inputs:
      seed_val = inputs.get("seed")
      if seed_val in (None, "", 0):
        inputs["seed"] = generate_seed()

