"""
基础API使用示例

演示如何通过API调用ComfyUI工作流生成图片
"""
import json
import requests
import time
import sys
import os
import random

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE = 'http://192.168.48.132:8000'

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
  response = requests.get(f'{API_BASE}/api/task/{task_id}') 
  response.raise_for_status()
  return response.json()

def wait_for_completion(task_id, timeout=300):
  """等待任务完成"""
  start_time = time.time()
  
  while time.time() - start_time < timeout:
    task = get_task_status(task_id)
    
    if task['status'] == 'completed':
      print(f"✅ 任务完成！")
      return task
    elif task['status'] == 'failed':
      print(f"❌ 任务失败: {task.get('error', '未知错误')}")
      return task
    
    print(f"⏳ 任务状态: {task['status']}")
    time.sleep(2)
  
  print(f"⚠️ 任务超时")
  return None

def generate_image(prompt, negative_prompt="", seed=-1, steps=10, width=1024, height=1024):
  """生成图片"""
  
  # 读取工作流模板
  workflow_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'workflows',
    'qwen_t2i_distill.json'
  )
  
  with open(workflow_path, 'r', encoding='utf-8') as f:
    workflow = json.load(f)
  
  # 修改参数
  # 如果seed为-1，生成随机种子（ComfyUI不接受负数）
  if seed < 0:
    seed = random.randint(0, 18446744073709551615)
  
  workflow['3']['inputs']['seed'] = seed
  workflow['3']['inputs']['steps'] = steps
  workflow['6']['inputs']['text'] = prompt
  workflow['7']['inputs']['text'] = negative_prompt
  workflow['72']['inputs']['width'] = width
  workflow['72']['inputs']['height'] = height
  
  # 提交任务
  print(f"\n🚀 提交任务...")
  print(f"📝 提示词: {prompt}")
  print(f"🎲 种子: {seed} {'(随机生成)' if seed != workflow['3']['inputs']['seed'] else ''}")
  print(f"📐 尺寸: {width}x{height}")
  print(f"🔢 步数: {steps}")
  
  task = submit_workflow(workflow)
  task_id = task['task_id']
  print(f"📋 任务ID: {task_id}")
  
  # 等待完成
  result = wait_for_completion(task_id)
  
  if result and result['status'] == 'completed':
    print(f"\n🎉 生成成功！")
    
    # 提取outputs（可能在result.outputs或result.result.outputs）
    outputs_data = result.get('outputs') or (result.get('result', {}).get('outputs') if result.get('result') else None)
    
    # 显示图片URL并下载
    if outputs_data and outputs_data.get('images'):
      downloaded_images = []
      images = outputs_data['images']
      
      # 创建输出目录
      output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
      os.makedirs(output_dir, exist_ok=True)
      
      print(f"\n📸 找到 {len(images)} 张图片")
      
      for i, img_info in enumerate(images, 1):
        # 提取图片信息
        filename = img_info.get('filename')
        subfolder = img_info.get('subfolder', '')
        img_type = img_info.get('type', 'output')
        
        print(f"\n🖼️  图片{i}: {filename}")
        
        # 方法1：通过API服务器（推荐，更规范）
        image_url = f"{API_BASE}/api/image/{filename}?subfolder={subfolder}&type={img_type}"
        
        # 方法2：直接从ComfyUI获取（备用）
        comfyui_url = f"http://192.168.48.123:8188/view?filename={filename}&subfolder={subfolder}&type={img_type}"
        
        # 先尝试方法1（通过API）
        try:
          print(f"  正在从API服务器下载...")
          response = requests.get(image_url)
          response.raise_for_status()
          
          filepath = os.path.join(output_dir, filename)
          with open(filepath, 'wb') as f:
            f.write(response.content)
          
          file_size = len(response.content) / 1024  # KB
          print(f"  ✅ 已保存: {filepath} ({file_size:.1f} KB)")
          downloaded_images.append(filepath)
          
        except Exception as e:
          # 如果API失败，尝试直接从ComfyUI获取
          print(f"  ⚠️  API下载失败: {e}")
          try:
            print(f"  尝试直接从ComfyUI下载...")
            response = requests.get(comfyui_url)
            response.raise_for_status()
            
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
              f.write(response.content)
            
            file_size = len(response.content) / 1024
            print(f"  ✅ 已保存（直接方式）: {filepath} ({file_size:.1f} KB)")
            downloaded_images.append(filepath)
          except Exception as e2:
            print(f"  ❌ 两种方式都失败")
            print(f"     - API服务器: {e}")
            print(f"     - ComfyUI直接: {e2}")
            print(f"  💡 提示: 请检查网络连接和服务状态")
      
      result['downloaded_images'] = downloaded_images
      
      if downloaded_images:
        print(f"\n📂 所有图片已保存到: {output_dir}")
        print(f"✨ 共下载 {len(downloaded_images)} 张图片")
    else:
      print(f"\n⚠️  没有找到输出图片")
      print(f"outputs_data: {json.dumps(outputs_data, indent=2, ensure_ascii=False) if outputs_data else 'None'}")
  
  return result

if __name__ == '__main__':
  print("=" * 60)
  print("ComfyUI API - 基础使用示例")
  print("=" * 60)
  
  # 示例1：简单生成
  print("\n【示例1】简单生成一张图片")
  result1 = generate_image(
    prompt="Generate a realistic portrait of a 25-year-old Asian person in ambient daylight. Face should show natural skin texture with visible pores, scattered freckles, small moles, light blemishes, and subtle asymmetry. Expression relaxed and lifelike, eyes vivid but natural, hair slightly imperfect with natural strands. Lighting should be slightly uneven and natural, creating gentle highlights and soft shadows. Background softly blurred, resembling a candid, real-world photo rather than a studio shot.",
    negative_prompt="blurry, low quality",
    seed=10086,
    steps=10
  )
  
  # # 示例2：使用固定种子
  # print("\n" + "=" * 60)
  # print("\n【示例2】使用固定种子生成（可重现）")
  # result2 = generate_image(
  #   prompt="A cute cat sitting on a windowsill",
  #   negative_prompt="blurry, low quality, distorted",
  #   seed=123456789,
  #   steps=15,
  #   width=1024,
  #   height=1024
  # )
  
  # # 示例3：高质量生成
  # print("\n" + "=" * 60)
  # print("\n【示例3】高质量生成（更多步数）")
  # result3 = generate_image(
  #   prompt="Portrait of a young woman, natural lighting, professional photography",
  #   negative_prompt="cartoon, illustration, low quality, blurry, distorted",
  #   seed=-1,
  #   steps=30,
  #   width=1328,
  #   height=1328
  # )
  
  # print("\n" + "=" * 60)
  # print("✅ 所有示例执行完成！")
  # print("=" * 60)

