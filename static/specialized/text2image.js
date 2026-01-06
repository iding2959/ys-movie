/**
 * 文生图 API 测试页面 JavaScript
 */

// 表单提交处理
document.getElementById('text2imageForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const submitBtn = document.getElementById('submitBtn');
  const resultContainer = document.getElementById('resultContainer');
  const imageResult = document.getElementById('imageResult');
  
  // 禁用提交按钮
  submitBtn.disabled = true;
  submitBtn.textContent = '⏳ 提交中...';
  
  // 显示结果容器
  resultContainer.classList.add('show');
  imageResult.innerHTML = '';
  
  // 收集表单数据
  const formData = {
    prompt: document.getElementById('prompt').value,
    negative_prompt: document.getElementById('negative_prompt').value || '',
    aspect_ratio: document.getElementById('aspectRatio').value,
    width: parseInt(document.getElementById('width').value),
    height: parseInt(document.getElementById('height').value),
    steps: parseInt(document.getElementById('steps').value),
    seed: parseInt(document.getElementById('seed').value)
  };
  
  try {
    // 提交任务
    const response = await fetch('/api/text2image', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData)
    });
    
    if (!response.ok) {
      throw new Error('提交失败');
    }
    
    const result = await response.json();
    const taskId = result.data.task_id;
    const taskData = result.data;
    
    // 更新任务信息
    document.getElementById('taskId').textContent = taskId;
    document.getElementById('taskStatus').textContent = '已提交';
    document.getElementById('taskStatus').className = 'status-badge status-submitted';
    
    // 构建详细信息
    let progressInfo = `任务已提交到队列，等待处理...\n`;
    progressInfo += `\n📐 比例: ${taskData.ratio_info || '未知'}`;
    progressInfo += `\n📏 尺寸: ${taskData.width}×${taskData.height}`;
    progressInfo += `\n⚙️ 流程: ${taskData.pipeline || '未知'}`;
    if (taskData.base_size) {
      progressInfo += `\n🔍 基础尺寸: ${taskData.base_size}`;
    }
    progressInfo += `\n🎲 种子: ${taskData.seed}`;
    
    document.getElementById('progressText').innerHTML = progressInfo.replace(/\n/g, '<br>');
    
    // 开始轮询任务状态
    pollTaskStatus(taskId);
    
  } catch (error) {
    console.error('提交失败:', error);
    document.getElementById('taskStatus').textContent = '失败';
    document.getElementById('taskStatus').className = 'status-badge status-failed';
    document.getElementById('progressText').textContent = `错误: ${error.message}`;
    
    // 重新启用提交按钮
    submitBtn.disabled = false;
    submitBtn.textContent = '🚀 生成图像';
  }
});

/**
 * 轮询任务状态
 */
async function pollTaskStatus(taskId) {
  const submitBtn = document.getElementById('submitBtn');
  const statusElement = document.getElementById('taskStatus');
  const progressText = document.getElementById('progressText');
  const imageResult = document.getElementById('imageResult');
  
  let pollCount = 0;
  const maxPolls = 300; // 最多轮询5分钟（每秒一次）
  
  const poll = setInterval(async () => {
    pollCount++;
    
    try {
      const response = await fetch(`/api/task/${taskId}`);
      if (!response.ok) {
        throw new Error('查询失败');
      }
      
      const result = await response.json();
      const status = result.data.status;
      
      // 更新状态显示
      if (status === 'running') {
        statusElement.textContent = '生成中';
        statusElement.className = 'status-badge status-running';
        progressText.textContent = '正在生成图像，请稍候...';
        submitBtn.textContent = '⏳ 生成中...';
      } else if (status === 'completed') {
        clearInterval(poll);
        
        statusElement.textContent = '完成';
        statusElement.className = 'status-badge status-completed';
        progressText.textContent = '图像生成完成！';
        
        // 显示图像
        displayImage(result.data.result);
        
        // 重新启用提交按钮
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 生成图像';
        
      } else if (status === 'failed') {
        clearInterval(poll);
        
        statusElement.textContent = '失败';
        statusElement.className = 'status-badge status-failed';
        progressText.textContent = `生成失败: ${result.data.error || '未知错误'}`;
        
        // 重新启用提交按钮
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 生成图像';
      }
      
      // 超时处理
      if (pollCount >= maxPolls) {
        clearInterval(poll);
        statusElement.textContent = '超时';
        statusElement.className = 'status-badge status-failed';
        progressText.textContent = '查询超时，请稍后手动查询任务状态';
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 生成图像';
      }
      
    } catch (error) {
      console.error('查询任务状态失败:', error);
    }
  }, 1000); // 每秒查询一次
}

/**
 * 显示生成的图像
 */
function displayImage(result) {
  const imageResult = document.getElementById('imageResult');
  
  if (!result || !result.outputs || !result.outputs.images) {
    imageResult.innerHTML = '<p style="color: #f44336;">未找到生成的图像</p>';
    return;
  }
  
  const images = result.outputs.images;
  
  if (images.length === 0) {
    imageResult.innerHTML = '<p style="color: #f44336;">没有生成图像</p>';
    return;
  }
  
  let html = '<div style="margin-top: 20px;">';
  
  images.forEach((img, index) => {
    const filename = img.filename;
    const subfolder = img.subfolder || '';
    const type = img.type || 'output';
    const imageUrl = `/api/image/${filename}?subfolder=${subfolder}&type=${type}`;
    
    html += `
      <div style="margin-bottom: 20px;">
        <h3>图像 ${index + 1}</h3>
        <img src="${imageUrl}" class="result-image" alt="生成的图像 ${index + 1}">
        <div style="margin-top: 10px;">
          <a href="${imageUrl}" target="_blank" style="color: #667eea; text-decoration: none;">
            🔗 在新标签页打开
          </a>
          <span style="margin: 0 10px; color: #ddd;">|</span>
          <a href="${imageUrl}" download="${filename}" style="color: #667eea; text-decoration: none;">
            💾 下载图像
          </a>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  imageResult.innerHTML = html;
}

// 页面加载时的初始化
document.addEventListener('DOMContentLoaded', function() {
  console.log('文生图API测试页面已加载');
  
  // 比例选择器事件
  const aspectRatioSelect = document.getElementById('aspectRatio');
  const widthInput = document.getElementById('width');
  const heightInput = document.getElementById('height');
  
  // 比例预设映射
  const aspectRatioPresets = {
    // 标准比例
    '1280x720': { width: 1280, height: 720, label: '标准1K横屏' },
    '720x1280': { width: 720, height: 1280, label: '标准1K竖屏' },
    '2560x1440': { width: 2560, height: 1440, label: '标准2K横屏' },
    '1440x2560': { width: 1440, height: 2560, label: '标准2K竖屏' },
    // 超宽屏
    '1512x648': { width: 1512, height: 648, label: '21:9-1K横屏' },
    '2560x1080': { width: 2560, height: 1080, label: '21:9-2K横屏' },
    '464x1080': { width: 464, height: 1080, label: '9:21-1K竖屏' },
    '1080x2560': { width: 1080, height: 2560, label: '9:21-2K竖屏' },
    // 全高清
    '1536x864': { width: 1536, height: 864, label: '16:9-1K横屏' },
    '1920x1080': { width: 1920, height: 1080, label: '16:9-2K横屏' },
    '608x1080': { width: 608, height: 1080, label: '9:16-1K竖屏' },
    '1080x1920': { width: 1080, height: 1920, label: '9:16-2K竖屏' },
    // 传统比例
    '1024x768': { width: 1024, height: 768, label: '4:3横屏' },
    '768x1024': { width: 768, height: 1024, label: '3:4竖屏' },
    '2048x1536': { width: 2048, height: 1536, label: '4:3-2K横屏' },
    '1536x2048': { width: 1536, height: 2048, label: '3:4-2K竖屏' },
    // 方形
    '1080x1080': { width: 1080, height: 1080, label: '1:1方形' },
    '2160x2160': { width: 2160, height: 2160, label: '1:1-2K方形' }
  };
  
  // 监听比例选择变化
  aspectRatioSelect.addEventListener('change', function() {
    const selectedValue = this.value;
    
    if (selectedValue !== 'custom' && aspectRatioPresets[selectedValue]) {
      const preset = aspectRatioPresets[selectedValue];
      widthInput.value = preset.width;
      heightInput.value = preset.height;
      updatePipelineHint(preset.width, preset.height);
      console.log(`已应用预设比例: ${preset.label} (${preset.width}x${preset.height})`);
    }
  });
  
  // 监听宽度和高度的手动修改
  function checkCustomSize() {
    const currentWidth = parseInt(widthInput.value);
    const currentHeight = parseInt(heightInput.value);
    const selectedValue = aspectRatioSelect.value;
    
    // 如果当前选择不是自定义，且输入值与预设不匹配，则切换到自定义
    if (selectedValue !== 'custom') {
      const preset = aspectRatioPresets[selectedValue];
      if (!preset || preset.width !== currentWidth || preset.height !== currentHeight) {
        aspectRatioSelect.value = 'custom';
        console.log(`检测到自定义尺寸: ${currentWidth}x${currentHeight}`);
      }
    }
    
    // 更新流程提示
    updatePipelineHint(currentWidth, currentHeight);
  }
  
  // 更新流程提示
  function updatePipelineHint(width, height) {
    const use2K = width > 1536 || height > 1080;
    const widthLabel = widthInput.parentElement.querySelector('label');
    const heightLabel = heightInput.parentElement.querySelector('label');
    
    // 移除旧的提示
    const oldHint = widthInput.parentElement.parentElement.querySelector('.size-info');
    if (oldHint) {
      oldHint.remove();
    }
    
    // 添加新的提示
    const hint = document.createElement('span');
    hint.className = 'size-info';
    hint.textContent = use2K ? '🔍 2K放大流程' : '📐 1K直出流程';
    hint.title = use2K 
      ? `将生成${Math.floor(width/2)}×${Math.floor(height/2)}的基础图，然后放大到${width}×${height}`
      : `直接生成${width}×${height}的图像`;
    
    widthLabel.appendChild(hint);
  }
  
  widthInput.addEventListener('input', checkCustomSize);
  heightInput.addEventListener('input', checkCustomSize);
  
  // 初始化时也显示流程提示
  updatePipelineHint(parseInt(widthInput.value), parseInt(heightInput.value));
});

