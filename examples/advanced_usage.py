"""
高级用法示例

演示如何使用WorkflowBuilder类来构建和修改工作流
"""
import json
import requests
import time
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE = 'http://localhost:8000'

class WorkflowBuilder:
  """
  工作流构建器
  
  提供链式调用接口来构建和修改ComfyUI工作流
  """
  
  def __init__(self, template_path):
    """
    初始化构建器
    
    参数:
      template_path: 工作流模板文件路径
    """
    with open(template_path, 'r', encoding='utf-8') as f:
      self.workflow = json.load(f)
  
  def set_prompt(self, positive, negative=""):
    """设置提示词"""
    for node_id, node in self.workflow.items():
      if node['class_type'] == 'CLIPTextEncode':
        title = node.get('_meta', {}).get('title', '').lower()
        if 'positive' in title or 'clip text encode (positive' in title:
          node['inputs']['text'] = positive
        elif 'negative' in title or 'clip text encode (negative' in title:
          node['inputs']['text'] = negative
    return self
  
  def set_sampler(self, seed=-1, steps=20, cfg=1, sampler_name=None, scheduler=None, denoise=None):
    """设置采样器参数"""
    # 如果seed为-1，生成随机种子（ComfyUI不接受负数）
    if seed < 0:
      seed = random.randint(0, 18446744073709551615)
    
    for node_id, node in self.workflow.items():
      if node['class_type'] == 'KSampler':
        node['inputs']['seed'] = seed
        node['inputs']['steps'] = steps
        node['inputs']['cfg'] = cfg
        if sampler_name is not None:
          node['inputs']['sampler_name'] = sampler_name
        if scheduler is not None:
          node['inputs']['scheduler'] = scheduler
        if denoise is not None:
          node['inputs']['denoise'] = denoise
    return self
  
  def set_size(self, width, height, batch_size=1):
    """设置图像尺寸"""
    for node_id, node in self.workflow.items():
      if node['class_type'] in ['EmptySD3LatentImage', 'EmptyLatentImage']:
        node['inputs']['width'] = width
        node['inputs']['height'] = height
        node['inputs']['batch_size'] = batch_size
    return self
  
  def set_filename_prefix(self, prefix):
    """设置输出文件名前缀"""
    for node_id, node in self.workflow.items():
      if node['class_type'] == 'SaveImage':
        node['inputs']['filename_prefix'] = prefix
    return self
  
  def set_node_input(self, node_id, input_name, value):
    """
    直接设置指定节点的输入值
    
    参数:
      node_id: 节点ID（字符串）
      input_name: 输入名称
      value: 输入值
    """
    if node_id in self.workflow:
      self.workflow[node_id]['inputs'][input_name] = value
    return self
  
  def build(self):
    """构建并返回最终工作流"""
    return self.workflow
  
  def submit(self):
    """直接提交工作流"""
    payload = {
      "workflow": self.workflow,
      "params": {},
      "timeout": 600
    }
    response = requests.post(f'{API_BASE}/api/workflow/submit', json=payload)
    response.raise_for_status()
    return response.json()

def submit_workflow(workflow_data):
  """提交工作流"""
  # API期望的格式：{"workflow": {...}, "params": {}, "timeout": 600}
  payload = {
    "workflow": workflow_data,
    "params": {},
    "timeout": 600
  }
  response = requests.post(f'{API_BASE}/api/workflow/submit', json=payload)
  response.raise_for_status()
  return response.json()

def get_task_status(task_id):
  """查询任务状态"""
  response = requests.get(f'{API_BASE}/api/task/{task_id}')  # 注意：是task不是tasks
  response.raise_for_status()
  return response.json()

def wait_for_completion(task_id, timeout=300, verbose=True):
  """等待任务完成"""
  start_time = time.time()
  
  while time.time() - start_time < timeout:
    task = get_task_status(task_id)
    
    if task['status'] == 'completed':
      if verbose:
        print(f"✅ 任务完成！")
      return task
    elif task['status'] == 'failed':
      if verbose:
        print(f"❌ 任务失败: {task.get('error', '未知错误')}")
      return task
    
    if verbose:
      print(f"⏳ 任务状态: {task['status']}")
    time.sleep(2)
  
  if verbose:
    print(f"⚠️ 任务超时")
  return None

if __name__ == '__main__':
  print("=" * 60)
  print("ComfyUI API - 高级用法示例")
  print("=" * 60)
  
  workflow_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'workflows',
    'qwen_t2i_distill.json'
  )
  
  # 示例1：使用WorkflowBuilder链式调用
  print("\n【示例1】使用WorkflowBuilder链式调用")
  print("-" * 60)
  
  workflow = (WorkflowBuilder(workflow_path)
    .set_prompt(
      positive="A beautiful sunset over mountains, vibrant colors, peaceful scene",
      negative="blurry, low quality, distorted"
    )
    .set_sampler(seed=-1, steps=20, cfg=1.5)
    .set_size(1024, 1024)
    .set_filename_prefix("advanced_example_1")
    .build())
  
  task1 = submit_workflow(workflow)
  print(f"📋 任务ID: {task1['task_id']}")
  result1 = wait_for_completion(task1['task_id'])
  
  # 示例2：测试不同采样步数
  print("\n" + "=" * 60)
  print("\n【示例2】测试不同采样步数（固定种子对比）")
  print("-" * 60)
  
  seed = 987654321
  prompt = "Portrait of a young woman, professional photography"
  
  for steps in [10, 20, 30]:
    print(f"\n🔢 测试 {steps} 步...")
    
    workflow = (WorkflowBuilder(workflow_path)
      .set_prompt(positive=prompt, negative="low quality, blurry")
      .set_sampler(seed=seed, steps=steps)
      .set_size(1024, 1024)
      .set_filename_prefix(f"steps_test_{steps}")
      .build())
    
    task = submit_workflow(workflow)
    print(f"📋 任务ID: {task['task_id']}")
    wait_for_completion(task['task_id'], verbose=False)
  
  # 示例3：测试不同分辨率
  print("\n" + "=" * 60)
  print("\n【示例3】测试不同分辨率")
  print("-" * 60)
  
  resolutions = [
    (512, 512, "小图"),
    (1024, 1024, "中图"),
    (1328, 1328, "大图")
  ]
  
  for width, height, label in resolutions:
    print(f"\n📐 测试 {label} ({width}x{height})...")
    
    workflow = (WorkflowBuilder(workflow_path)
      .set_prompt(
        positive="A cute cat sitting on a windowsill",
        negative="blurry, low quality"
      )
      .set_sampler(seed=-1, steps=15)
      .set_size(width, height)
      .set_filename_prefix(f"resolution_test_{width}x{height}")
      .build())
    
    task = submit_workflow(workflow)
    print(f"📋 任务ID: {task['task_id']}")
    wait_for_completion(task['task_id'], verbose=False)
  
  # 示例4：直接修改节点参数
  print("\n" + "=" * 60)
  print("\n【示例4】直接修改特定节点参数")
  print("-" * 60)
  
  workflow = (WorkflowBuilder(workflow_path)
    .set_prompt(
      positive="A magical forest with glowing mushrooms",
      negative="low quality, ugly"
    )
    .set_sampler(seed=-1, steps=25, cfg=2.0)
    .set_size(1024, 1024)
    .set_node_input('3', 'denoise', 0.95)  # 直接修改节点3的denoise参数
    .set_filename_prefix("custom_denoise")
    .build())
  
  task4 = submit_workflow(workflow)
  print(f"📋 任务ID: {task4['task_id']}")
  result4 = wait_for_completion(task4['task_id'])
  
  # 示例5：使用submit()方法直接提交
  print("\n" + "=" * 60)
  print("\n【示例5】使用submit()方法直接提交")
  print("-" * 60)
  
  builder = WorkflowBuilder(workflow_path)
  task5 = builder.set_prompt(
    positive="A futuristic city skyline at night",
    negative="blurry, low quality"
  ).set_sampler(seed=-1, steps=20).set_size(1024, 1024).submit()
  
  print(f"📋 任务ID: {task5['task_id']}")
  result5 = wait_for_completion(task5['task_id'])
  
  print("\n" + "=" * 60)
  print("✅ 所有示例执行完成！")
  print("=" * 60)

