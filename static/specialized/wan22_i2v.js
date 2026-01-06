/**
 * Wan2.2 图生视频 API 测试页面 JavaScript
 */

let selectedDuration = 5;
let selectedImage = null;
let uploadedFilename = null;
let baseWidth = 480;
let baseHeight = 832;
let aspectRatio = 480 / 832;
let promptMode = 'single'; // 'single' 或 'multiple'

/**
 * 更新多提示词输入框
 */
function updateMultiplePrompts() {
  const container = document.getElementById('promptsList');
  const numSegments = selectedDuration / 5;
  
  container.innerHTML = '';
  
  for (let i = 0; i < numSegments; i++) {
    const startTime = i * 5;
    const endTime = (i + 1) * 5;
    const promptId = `prompt_${i}`;
    
    const promptItem = document.createElement('div');
    promptItem.className = 'prompt-item';
    promptItem.innerHTML = `
      <div class="prompt-item-header">
        <span class="prompt-item-label">片段 ${i + 1}</span>
        <span class="prompt-item-time">${startTime}秒 - ${endTime}秒</span>
      </div>
      <textarea 
        id="${promptId}" 
        name="${promptId}"
        placeholder="描述第${i + 1}个5秒片段的内容，例如：A woman walking gracefully through a beautiful garden"
        required></textarea>
    `;
    
    container.appendChild(promptItem);
  }
}

/**
 * 切换提示词模式
 */
function switchPromptMode(mode) {
  promptMode = mode;
  const singleContainer = document.getElementById('singlePromptContainer');
  const multipleContainer = document.getElementById('multiplePromptsContainer');
  const singlePrompt = document.getElementById('prompt');
  
  if (mode === 'single') {
    singleContainer.style.display = 'block';
    multipleContainer.style.display = 'none';
    singlePrompt.required = true;
    // 从多提示词复制第一个到单提示词（如果有内容）
    const firstPrompt = document.getElementById('prompt_0');
    if (firstPrompt && firstPrompt.value) {
      singlePrompt.value = firstPrompt.value;
    }
  } else {
    singleContainer.style.display = 'none';
    multipleContainer.style.display = 'block';
    singlePrompt.required = false;
    // 从单提示词复制到所有多提示词输入框
    const singleValue = singlePrompt.value;
    updateMultiplePrompts();
    if (singleValue) {
      const numSegments = selectedDuration / 5;
      for (let i = 0; i < numSegments; i++) {
        const promptInput = document.getElementById(`prompt_${i}`);
        if (promptInput && !promptInput.value) {
          promptInput.value = singleValue;
        }
      }
    }
  }
}

// 提示词模式切换事件
document.querySelectorAll('input[name="promptMode"]').forEach(radio => {
  radio.addEventListener('change', function() {
    switchPromptMode(this.value);
  });
});

// 时长选择按钮处理
document.querySelectorAll('.duration-btn').forEach(btn => {
  btn.addEventListener('click', function(e) {
    e.preventDefault();
    
    // 移除所有active类
    document.querySelectorAll('.duration-btn').forEach(b => b.classList.remove('active'));
    
    // 添加active类到当前按钮
    this.classList.add('active');
    
    // 更新选中的时长
    selectedDuration = parseInt(this.dataset.duration);
    document.getElementById('duration').value = selectedDuration;
    
    // 如果当前是多提示词模式，更新输入框数量
    if (promptMode === 'multiple') {
      updateMultiplePrompts();
    }
    
    // 更新单提示词提示信息
    const numSegments = selectedDuration / 5;
    const hintElement = document.getElementById('singlePromptHint');
    if (numSegments > 1) {
      hintElement.innerHTML = `⚠️ 提示：视频有${numSegments}个5秒片段，仅使用一个提示词可能影响效果。建议使用"多提示词"模式，为每个片段提供对应的提示词`;
      hintElement.style.color = '#f5576c';
    } else {
      hintElement.textContent = '提示：超过5秒的视频建议使用"多提示词"模式，为每个5秒片段提供对应的提示词以获得更好效果';
      hintElement.style.color = '#999';
    }
    
    console.log('选择时长:', selectedDuration, '秒');
  });
});

// 图片上传处理
document.getElementById('imageFile').addEventListener('change', async function(e) {
  const file = e.target.files[0];
  if (file) {
    selectedImage = file;
    
    // 显示预览
    const reader = new FileReader();
    reader.onload = function(e) {
      const preview = document.getElementById('imagePreview');
      const placeholder = document.getElementById('uploadPlaceholder');
      const uploadDiv = document.getElementById('imageUpload');
      
      preview.src = e.target.result;
      preview.style.display = 'block';
      placeholder.style.display = 'none';
      uploadDiv.classList.add('has-image');
    };
    reader.readAsDataURL(file);
    
    console.log('已选择图片:', file.name);
    
    // 分析图片并上传
    await analyzeAndUploadImage(file);
  }
});

/**
 * 分析图片并上传到服务器
 */
async function analyzeAndUploadImage(file) {
  const dimensionHint = document.getElementById('dimensionHint');
  dimensionHint.textContent = '正在分析图片...';
  dimensionHint.style.color = '#667eea';
  
  try {
    const formData = new FormData();
    formData.append('image', file);
    
    const response = await fetch('/api/wan22_i2v/analyze_image', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error('图片分析失败');
    }
    
    const result = await response.json();
    const data = result.data;
    
    // 保存上传的文件名
    uploadedFilename = data.filename;
    
    // 保存基准尺寸和比例
    baseWidth = data.suggested_width;
    baseHeight = data.suggested_height;
    aspectRatio = data.aspect_ratio;
    
    // 更新显示
    updateDimensions(100);
    
    // 启用缩放滑块
    document.getElementById('scaleSlider').disabled = false;
    
    // 更新提示信息
    dimensionHint.innerHTML = `
      <span style="color: #4caf50;">✓</span> 
      原始尺寸: ${data.original_width}×${data.original_height}, 
      建议尺寸: ${baseWidth}×${baseHeight}
    `;
    dimensionHint.style.color = '#4caf50';
    
    console.log('图片分析完成:', data);
    
  } catch (error) {
    console.error('图片分析失败:', error);
    dimensionHint.textContent = '图片分析失败，将使用默认尺寸';
    dimensionHint.style.color = '#f44336';
  }
}

/**
 * 根据缩放比例更新尺寸显示
 */
function updateDimensions(scale) {
  const scaleFactor = scale / 100;
  let width = Math.round(baseWidth * scaleFactor);
  let height = Math.round(baseHeight * scaleFactor);
  
  // 对齐到32的倍数（Wan2.2模型要求，避免张量维度不匹配）
  width = Math.max(256, Math.min(1920, (Math.round(width / 32)) * 32));
  height = Math.max(256, Math.min(1920, (Math.round(height / 32)) * 32));
  
  // 32的倍数自动满足偶数要求
  if (width % 2 === 1) {
    width = Math.floor(width / 32) * 32;
  }
  if (height % 2 === 1) {
    height = Math.floor(height / 32) * 32;
  }
  
  // 更新显示
  document.getElementById('widthDisplay').textContent = width;
  document.getElementById('heightDisplay').textContent = height;
  document.getElementById('scaleValue').textContent = scale;
  
  // 更新隐藏字段
  document.getElementById('width').value = width;
  document.getElementById('height').value = height;
  
  // 计算并显示比例
  const gcd = (a, b) => b === 0 ? a : gcd(b, a % b);
  const divisor = gcd(width, height);
  const ratioW = width / divisor;
  const ratioH = height / divisor;
  document.getElementById('ratioDisplay').textContent = `${ratioW}:${ratioH}`;
}

// 缩放滑块事件
document.getElementById('scaleSlider').addEventListener('input', function(e) {
  const scale = parseInt(e.target.value);
  updateDimensions(scale);
});

// 表单提交处理
document.getElementById('wan22Form').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  if (!selectedImage) {
    alert('请先上传一张图片！');
    return;
  }
  
  if (!uploadedFilename) {
    alert('图片正在上传中，请稍候...');
    return;
  }
  
  const submitBtn = document.getElementById('submitBtn');
  const resultContainer = document.getElementById('resultContainer');
  const videoResult = document.getElementById('videoResult');
  
  // 禁用提交按钮
  submitBtn.disabled = true;
  submitBtn.textContent = '⏳ 提交中...';
  
  // 显示结果容器
  resultContainer.classList.add('show');
  videoResult.innerHTML = '';
  
  // 收集提示词数据
  let promptValue;
  if (promptMode === 'single') {
    // 单提示词模式
    promptValue = document.getElementById('prompt').value.trim();
    if (!promptValue) {
      alert('请输入视频描述提示词！');
      submitBtn.disabled = false;
      submitBtn.textContent = '🎬 生成视频';
      return;
    }
  } else {
    // 多提示词模式
    const numSegments = selectedDuration / 5;
    const prompts = [];
    let hasEmpty = false;
    
    for (let i = 0; i < numSegments; i++) {
      const promptInput = document.getElementById(`prompt_${i}`);
      if (promptInput) {
        const value = promptInput.value.trim();
        if (!value) {
          hasEmpty = true;
        }
        prompts.push(value || '');
      }
    }
    
    // 检查是否所有提示词都已填写
    const emptyCount = prompts.filter(p => !p).length;
    if (emptyCount > 0) {
      // 如果所有提示词都为空，直接阻止提交
      if (emptyCount === prompts.length) {
        alert('请至少为一个片段填写提示词！');
        submitBtn.disabled = false;
        submitBtn.textContent = '🎬 生成视频';
        return;
      }
      
      // 如果有部分空白，询问用户是否自动填充
      const confirmFill = confirm(`检测到有${emptyCount}个片段未填写提示词。\n\n选择"确定"将使用第一个已填写的提示词填充空白项，选择"取消"返回填写。`);
      if (!confirmFill) {
        submitBtn.disabled = false;
        submitBtn.textContent = '🎬 生成视频';
        return;
      }
      // 用第一个非空提示词填充空白项
      const firstNonEmpty = prompts.find(p => p) || '';
      for (let i = 0; i < prompts.length; i++) {
        if (!prompts[i]) {
          prompts[i] = firstNonEmpty;
        }
      }
    }
    
    // 如果所有提示词都相同，可以使用单个字符串；否则使用数组
    const allSame = prompts.every(p => p === prompts[0]);
    promptValue = allSame ? prompts[0] : prompts;
  }
  
  // 使用已上传的图片文件名，调用generate API
  const requestData = {
    image_filename: uploadedFilename,
    prompt: promptValue,
    negative_prompt: document.getElementById('negative_prompt').value || '',
    duration: selectedDuration,
    width: parseInt(document.getElementById('width').value),
    height: parseInt(document.getElementById('height').value),
    frame_rate: parseInt(document.getElementById('frame_rate').value),
    steps: parseInt(document.getElementById('steps').value),
    seed: parseInt(document.getElementById('seed').value)
  };
  
  try {
    // 提交任务（图片已上传，使用generate API）
    const response = await fetch('/api/wan22_i2v/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || '提交失败');
    }
    
    const result = await response.json();
    const taskId = result.data.task_id;
    const segments = result.data.segments;
    
    // 更新任务信息
    document.getElementById('taskId').textContent = taskId;
    document.getElementById('videoDuration').textContent = selectedDuration;
    document.getElementById('segmentCount').textContent = segments;
    document.getElementById('taskStatus').textContent = '已提交';
    document.getElementById('taskStatus').className = 'status-badge status-submitted';
    document.getElementById('progressText').textContent = `任务已提交，将生成 ${segments} 个5秒片段并自动拼接...`;
    
    submitBtn.textContent = '⏳ 生成中...';
    
    // 开始轮询任务状态
    pollTaskStatus(taskId, segments);
    
  } catch (error) {
    console.error('提交失败:', error);
    document.getElementById('taskStatus').textContent = '失败';
    document.getElementById('taskStatus').className = 'status-badge status-failed';
    document.getElementById('progressText').textContent = `错误: ${error.message}`;
    
    // 重新启用提交按钮
    submitBtn.disabled = false;
    submitBtn.textContent = '🎬 生成视频';
  }
});

/**
 * 轮询任务状态
 */
async function pollTaskStatus(taskId, segments) {
  const submitBtn = document.getElementById('submitBtn');
  const statusElement = document.getElementById('taskStatus');
  const progressText = document.getElementById('progressText');
  const videoResult = document.getElementById('videoResult');
  
  let pollCount = 0;
  const maxPolls = 900; // 最多轮询15分钟（每秒一次）
  
  const poll = setInterval(async () => {
    pollCount++;
    
    try {
      const response = await fetch(`/api/task/${taskId}`);
      if (!response.ok) {
        throw new Error('查询失败');
      }
      
      const result = await response.json();
      const status = result.data.status;
      
      // 计算预估时间
      const estimatedMinutes = Math.ceil(segments * 1.5); // 每片段约1.5分钟
      const elapsedSeconds = pollCount;
      const elapsedMinutes = Math.floor(elapsedSeconds / 60);
      
      // 更新状态显示
      if (status === 'running') {
        statusElement.textContent = '生成中';
        statusElement.className = 'status-badge status-running';
        progressText.innerHTML = `
          正在生成视频... <br>
          <small>已用时: ${elapsedMinutes}分${elapsedSeconds % 60}秒 | 预计需要: ${estimatedMinutes}分钟</small>
        `;
      } else if (status === 'completed') {
        clearInterval(poll);
        
        statusElement.textContent = '完成';
        statusElement.className = 'status-badge status-completed';
        progressText.textContent = `视频生成完成！总用时: ${elapsedMinutes}分${elapsedSeconds % 60}秒`;
        
        // 显示视频
        displayVideo(result.data.result);
        
        // 重新启用提交按钮
        submitBtn.disabled = false;
        submitBtn.textContent = '🎬 生成视频';
        
      } else if (status === 'failed') {
        clearInterval(poll);
        
        statusElement.textContent = '失败';
        statusElement.className = 'status-badge status-failed';
        progressText.textContent = `生成失败: ${result.data.error || '未知错误'}`;
        
        // 重新启用提交按钮
        submitBtn.disabled = false;
        submitBtn.textContent = '🎬 生成视频';
      }
      
      // 超时处理
      if (pollCount >= maxPolls) {
        clearInterval(poll);
        statusElement.textContent = '超时';
        statusElement.className = 'status-badge status-failed';
        progressText.textContent = '查询超时，请稍后手动查询任务状态';
        submitBtn.disabled = false;
        submitBtn.textContent = '🎬 生成视频';
      }
      
    } catch (error) {
      console.error('查询任务状态失败:', error);
    }
  }, 1000); // 每秒查询一次
}

/**
 * 显示生成的视频
 */
function displayVideo(result) {
  const videoResult = document.getElementById('videoResult');
  
  if (!result || !result.outputs) {
    videoResult.innerHTML = '<p style="color: #f44336;">未找到生成的视频</p>';
    return;
  }
  
  const outputs = result.outputs;
  let videos = [];
  
  // 方法1: 从 images 数组中查找视频文件
  if (outputs.images && Array.isArray(outputs.images)) {
    const imageVideos = outputs.images.filter(item => {
      const filename = item.filename.toLowerCase();
      return filename.endsWith('.mp4') || filename.endsWith('.webm') || filename.endsWith('.gif');
    });
    videos = videos.concat(imageVideos);
  }
  
  // 方法2: 从 other 数组中的 gifs 字段查找视频
  if (outputs.other && Array.isArray(outputs.other)) {
    outputs.other.forEach(item => {
      if (item.type === 'gifs' && Array.isArray(item.data)) {
        videos = videos.concat(item.data);
      }
    });
  }
  
  // 方法3: 从 videos 数组查找
  if (outputs.videos && Array.isArray(outputs.videos)) {
    videos = videos.concat(outputs.videos);
  }
  
  if (videos.length === 0) {
    videoResult.innerHTML = `
      <p style="color: #f44336;">没有生成视频文件</p>
      <details style="margin-top: 10px; color: #666; font-size: 14px;">
        <summary>查看原始输出数据</summary>
        <pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; margin-top: 10px;">${JSON.stringify(outputs, null, 2)}</pre>
      </details>
    `;
    return;
  }
  
  console.log('找到视频文件:', videos);
  
  let html = '<div style="margin-top: 20px;">';
  
  videos.forEach((video, index) => {
    const filename = video.filename;
    const subfolder = video.subfolder || '';
    const type = video.type || 'output';
    const videoUrl = `/api/video/${filename}?subfolder=${subfolder}&type=${type}`;
    const frameRate = video.frame_rate || video.framerate || 'N/A';
    const format = video.format || 'video/h264-mp4';
    
    html += `
      <div style="margin-bottom: 30px; padding: 20px; background: #f9f9f9; border-radius: 8px;">
        <h3 style="margin-top: 0;">生成的视频 ${index + 1}</h3>
        <video controls class="video-result" style="width: 100%;">
          <source src="${videoUrl}" type="video/mp4">
          您的浏览器不支持视频播放
        </video>
        <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 15px; align-items: center;">
          <a href="${videoUrl}" target="_blank" style="color: #f5576c; text-decoration: none; font-weight: 500;">
            🔗 在新标签页打开
          </a>
          <span style="color: #ddd;">|</span>
          <a href="${videoUrl}" download="${filename}" style="color: #f5576c; text-decoration: none; font-weight: 500;">
            💾 下载视频
          </a>
          <span style="color: #ddd;">|</span>
          <span style="color: #999; font-size: 14px;">文件名: ${filename}</span>
          ${frameRate !== 'N/A' ? `<span style="color: #ddd;">|</span><span style="color: #999; font-size: 14px;">帧率: ${frameRate} FPS</span>` : ''}
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  videoResult.innerHTML = html;
}

// 页面加载时的初始化
document.addEventListener('DOMContentLoaded', function() {
  console.log('Wan2.2图生视频API测试页面已加载');
  console.log('默认时长:', selectedDuration, '秒');
  
  // 初始化提示词提示信息
  const numSegments = selectedDuration / 5;
  const hintElement = document.getElementById('singlePromptHint');
  if (numSegments > 1) {
    hintElement.innerHTML = `⚠️ 提示：视频有${numSegments}个5秒片段，仅使用一个提示词可能影响效果。建议使用"多提示词"模式，为每个片段提供对应的提示词`;
    hintElement.style.color = '#f5576c';
  }
});

