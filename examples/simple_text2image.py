"""
简化的文生图示例
使用 /api/text2image 端点，只需提供提示词即可
"""
import requests
import json
import time

# API配置
API_BASE = "http://localhost:8000"

def text2image(prompt, **kwargs):
  """
  简化的文生图函数
  
  参数:
    prompt: 正向提示词（必需）
    negative_prompt: 负向提示词（可选，默认使用详细的负向提示词）
    width: 图像宽度（可选，默认: 1024）
    height: 图像高度（可选，默认: 1024）
    steps: 采样步数（可选，默认: 10）
    seed: 随机种子（可选，默认: -1表示随机）
  
  返回:
    任务ID
  """
  url = f"{API_BASE}/api/text2image"
  
  payload = {
    "prompt": prompt,
    **kwargs  # 包含所有可选参数
  }
  
  response = requests.post(url, json=payload)
  response.raise_for_status()
  
  result = response.json()
  return result['task_id']

def wait_for_result(task_id, max_wait=300):
  """等待任务完成并返回结果"""
  url = f"{API_BASE}/api/task/{task_id}"
  
  start_time = time.time()
  while time.time() - start_time < max_wait:
    response = requests.get(url)
    response.raise_for_status()
    
    task = response.json()
    status = task['status']
    
    print(f"⏳ 状态: {status}")
    
    if status == 'completed':
      return task
    elif status == 'failed':
      print(f"❌ 任务失败: {task.get('error', '未知错误')}")
      return None
    
    time.sleep(2)
  
  print("⏰ 等待超时")
  return None

def download_images(task):
  """从任务结果下载图片（方式1：传统方式）"""
  import os
  
  # 提取outputs（可能在result.outputs或result.result.outputs）
  outputs_data = task.get('result', {}).get('outputs') or \
                 (task.get('result', {}).get('result', {}).get('outputs') if task.get('result', {}).get('result') else None)
  
  if not outputs_data or not outputs_data.get('images'):
    print("⚠️  没有找到图片")
    return []
  
  # 创建输出目录
  output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
  os.makedirs(output_dir, exist_ok=True)
  
  downloaded = []
  images = outputs_data['images']
  
  print(f"\n📸 找到 {len(images)} 张图片")
  
  for i, img_info in enumerate(images, 1):
    filename = img_info.get('filename')
    subfolder = img_info.get('subfolder', '')
    img_type = img_info.get('type', 'output')
    
    # 构建图片URL
    image_url = f"{API_BASE}/api/image/{filename}?subfolder={subfolder}&type={img_type}"
    
    print(f"\n🖼️  图片{i}: {filename}")
    print(f"  正在下载...")
    
    try:
      response = requests.get(image_url)
      response.raise_for_status()
      
      filepath = os.path.join(output_dir, filename)
      with open(filepath, 'wb') as f:
        f.write(response.content)
      
      file_size = len(response.content) / 1024  # KB
      print(f"  ✅ 已保存: {filepath} ({file_size:.1f} KB)")
      downloaded.append(filepath)
    except Exception as e:
      print(f"  ❌ 下载失败: {e}")
  
  return downloaded

def download_images_by_task_id(task_id):
  """
  从任务ID直接下载图片（方式2：简化方式，推荐）
  使用新的 /api/task/{task_id}/image 端点
  """
  import os
  
  # 创建输出目录
  output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
  os.makedirs(output_dir, exist_ok=True)
  
  try:
    # 先获取图片信息
    info_url = f"{API_BASE}/api/task/{task_id}/images"
    response = requests.get(info_url)
    response.raise_for_status()
    
    info = response.json()
    total = info.get('total', 0)
    
    if total == 0:
      print("⚠️  任务没有生成图片")
      return []
    
    print(f"\n📸 任务共生成 {total} 张图片")
    
    downloaded = []
    for i in range(total):
      # 使用任务ID + 索引直接获取图片
      image_url = f"{API_BASE}/api/task/{task_id}/image?index={i}"
      
      print(f"\n🖼️  下载第 {i+1} 张图片...")
      
      try:
        response = requests.get(image_url)
        response.raise_for_status()
        
        # 从响应头获取文件名
        filename = f"task_{task_id}_{i}.png"
        if 'Content-Disposition' in response.headers:
          import re
          match = re.search(r'filename=([^;]+)', response.headers['Content-Disposition'])
          if match:
            filename = match.group(1).strip('"')
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'wb') as f:
          f.write(response.content)
        
        file_size = len(response.content) / 1024  # KB
        print(f"  ✅ 已保存: {filepath} ({file_size:.1f} KB)")
        downloaded.append(filepath)
      except Exception as e:
        print(f"  ❌ 下载第 {i+1} 张失败: {e}")
    
    return downloaded
    
  except Exception as e:
    print(f"❌ 获取图片信息失败: {e}")
    return []

def main():
  print("=" * 60)
  print("简化文生图示例")
  print("=" * 60)
  
  # 示例1：最简单的用法，只提供提示词
  print("\n【示例1】最简单的用法 - 使用任务ID直接下载（推荐）")
  print("-" * 60)
  
  try:
    task_id = text2image(
      prompt="A beautiful sunset over the ocean, vibrant colors, highly detailed"
    )
    print(f"✅ 任务已提交: {task_id}")
    
    # 等待完成
    task = wait_for_result(task_id)
    if task:
      print("\n✅ 任务完成！")
      # 方式2：直接使用任务ID下载（推荐，更简单）
      images = download_images_by_task_id(task_id)
      if images:
        print(f"\n🎉 成功！共下载 {len(images)} 张图片")
  except Exception as e:
    print(f"❌ 错误: {e}")
  
  # 示例2：自定义参数
  print("\n\n【示例2】自定义参数")
  print("-" * 60)
  
  try:
    task_id = text2image(
      prompt="A cute cat wearing a hat, studio lighting, professional photography",
      negative_prompt="cartoon, illustration, blurry, low quality, distorted, ugly",  # 可自定义负向提示词
      width=768,
      height=768,
      steps=15,
      seed=12345  # 使用固定种子以获得可复现的结果
    )
    print(f"✅ 任务已提交: {task_id}")
    
    # 等待完成
    task = wait_for_result(task_id)
    if task:
      print("\n✅ 任务完成！")
      # 下载图片
      images = download_images(task)
      if images:
        print(f"\n🎉 成功！图片已保存")
  except Exception as e:
    print(f"❌ 错误: {e}")
  
  # 示例3：使用随机种子生成多张不同的图片
  print("\n\n【示例3】批量生成（随机种子）")
  print("-" * 60)
  
  base_prompt = "A futuristic city at night, neon lights, cyberpunk style"
  
  for i in range(3):
    try:
      print(f"\n生成第 {i+1} 张...")
      task_id = text2image(
        prompt=base_prompt,
        steps=12,
        seed=-1  # 每次使用不同的随机种子
      )
      print(f"  任务ID: {task_id}")
      
      # 等待完成
      task = wait_for_result(task_id)
      if task:
        # 下载图片
        images = download_images(task)
        if images:
          print(f"  ✅ 第 {i+1} 张已保存")
    except Exception as e:
      print(f"  ❌ 第 {i+1} 张失败: {e}")
  
  print("\n" + "=" * 60)
  print("所有示例执行完成！")
  print("=" * 60)

if __name__ == "__main__":
  main()

