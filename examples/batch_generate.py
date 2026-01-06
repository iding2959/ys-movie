"""
批量生成示例

演示如何批量提交多个任务并监控执行
"""
import json
import requests
import time
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE = 'http://localhost:8000'

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

def batch_generate(prompts, base_workflow='workflows/qwen_t2i_distill.json', **params):
  """
  批量生成图片
  
  参数:
    prompts: 提示词列表
    base_workflow: 工作流模板路径
    **params: 其他参数 (seed, steps, width, height等)
  """
  
  workflow_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    base_workflow
  )
  
  with open(workflow_path, 'r', encoding='utf-8') as f:
    workflow_template = json.load(f)
  
  tasks = []
  
  print(f"\n🚀 开始批量提交 {len(prompts)} 个任务...")
  print("=" * 60)
  
  for i, prompt in enumerate(prompts, 1):
    # 深拷贝工作流
    workflow = json.loads(json.dumps(workflow_template))
    
    # 应用参数
    seed = params.get('seed', -1)
    # 如果seed为-1，每次生成不同的随机种子
    if seed < 0:
      seed = random.randint(0, 18446744073709551615)
    
    workflow['3']['inputs']['seed'] = seed
    workflow['3']['inputs']['steps'] = params.get('steps', 10)
    workflow['6']['inputs']['text'] = prompt
    workflow['7']['inputs']['text'] = params.get('negative_prompt', '')
    
    if 'width' in params:
      workflow['72']['inputs']['width'] = params['width']
    if 'height' in params:
      workflow['72']['inputs']['height'] = params['height']
    
    # 自定义文件名前缀
    workflow['60']['inputs']['filename_prefix'] = f'batch_{i:03d}'
    
    # 提交
    print(f"[{i}/{len(prompts)}] 提交: {prompt[:50]}...")
    try:
      task = submit_workflow(workflow)
      tasks.append({
        'task_id': task['task_id'],
        'prompt': prompt,
        'index': i
      })
      print(f"  ✅ 任务ID: {task['task_id']}")
    except Exception as e:
      print(f"  ❌ 提交失败: {e}")
      tasks.append({
        'task_id': None,
        'prompt': prompt,
        'index': i,
        'error': str(e)
      })
  
  print("=" * 60)
  print(f"✅ 已提交 {len([t for t in tasks if t['task_id']])} 个任务")
  
  return tasks

def monitor_tasks(tasks, check_interval=5):
  """
  监控批量任务的执行状态
  
  参数:
    tasks: 任务列表
    check_interval: 检查间隔（秒）
  """
  
  print(f"\n📊 开始监控任务执行...")
  print("=" * 60)
  
  pending_tasks = [t for t in tasks if t['task_id']]
  completed = []
  failed = []
  
  while pending_tasks:
    print(f"\n⏳ 待完成: {len(pending_tasks)} | 已完成: {len(completed)} | 失败: {len(failed)}")
    
    for task in pending_tasks[:]:  # 创建副本以便修改
      try:
        status = get_task_status(task['task_id'])
        
        if status['status'] == 'completed':
          print(f"✅ [{task['index']}] 完成: {task['prompt'][:40]}...")
          task['result'] = status
          completed.append(task)
          pending_tasks.remove(task)
          
        elif status['status'] == 'failed':
          print(f"❌ [{task['index']}] 失败: {task['prompt'][:40]}...")
          task['result'] = status
          failed.append(task)
          pending_tasks.remove(task)
          
      except Exception as e:
        print(f"⚠️  查询任务 {task['task_id']} 状态失败: {e}")
    
    if pending_tasks:
      time.sleep(check_interval)
  
  print("\n" + "=" * 60)
  print(f"🎉 批量任务执行完成！")
  print(f"  ✅ 成功: {len(completed)}")
  print(f"  ❌ 失败: {len(failed)}")
  print("=" * 60)
  
  # 显示结果
  if completed:
    print(f"\n📸 生成的图片：")
    for task in completed:
      if task['result'].get('outputs'):
        for output in task['result']['outputs']:
          if output['type'] == 'image':
            print(f"  [{task['index']:02d}] {API_BASE}{output['url']}")
  
  return {
    'completed': completed,
    'failed': failed
  }

if __name__ == '__main__':
  print("=" * 60)
  print("ComfyUI API - 批量生成示例")
  print("=" * 60)
  
  # 定义批量提示词
  prompts = [
    "A serene mountain landscape at dawn with mist",
    "A bustling city street at night with neon lights",
    "A colorful garden full of blooming flowers",
    "A peaceful beach with crystal clear water",
    "A cozy coffee shop interior with warm lighting",
    "A futuristic spaceship flying through space",
    "A magical forest with glowing mushrooms",
    "A vintage car on a desert highway"
  ]
  
  # 批量提交任务
  tasks = batch_generate(
    prompts,
    seed=-1,  # 每个都随机
    steps=15,
    width=1024,
    height=1024,
    negative_prompt="blurry, low quality, distorted, ugly"
  )
  
  # 监控执行
  results = monitor_tasks(tasks, check_interval=3)
  
  print("\n✅ 程序执行完成！")

