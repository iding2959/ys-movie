/**
 * InfiniteTalk I2V - 音频驱动视频生成
 */

let currentTaskId = null;
let statusCheckInterval = null;
let imageFile = null;
let audioFile = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  initializeFileUploads();
  initializeForm();
  initializeSizeSync();
});

/**
 * 初始化文件上传功能
 */
function initializeFileUploads() {
  // 图片上传
  const imageUpload = document.getElementById('imageUpload');
  const imageDropZone = document.getElementById('imageDropZone');
  const imagePreview = document.getElementById('imagePreview');

  imageDropZone.addEventListener('click', () => {
    imageUpload.click();
  });

  imageUpload.addEventListener('change', (e) => {
    handleImageSelect(e.target.files[0]);
  });

  // 拖拽上传
  imageDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    imageDropZone.classList.add('dragover');
  });

  imageDropZone.addEventListener('dragleave', () => {
    imageDropZone.classList.remove('dragover');
  });

  imageDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    imageDropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleImageSelect(e.dataTransfer.files[0]);
    }
  });

  // 音频上传
  const audioUpload = document.getElementById('audioUpload');
  const audioDropZone = document.getElementById('audioDropZone');
  const audioPreview = document.getElementById('audioPreview');

  audioDropZone.addEventListener('click', () => {
    audioUpload.click();
  });

  audioUpload.addEventListener('change', (e) => {
    handleAudioSelect(e.target.files[0]);
  });

  // 拖拽上传
  audioDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    audioDropZone.classList.add('dragover');
  });

  audioDropZone.addEventListener('dragleave', () => {
    audioDropZone.classList.remove('dragover');
  });

  audioDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    audioDropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleAudioSelect(e.dataTransfer.files[0]);
    }
  });
}

/**
 * 处理图片选择
 */
function handleImageSelect(file) {
  if (!file) return;

  if (!file.type.startsWith('image/')) {
    alert('请选择图片文件！');
    return;
  }

  imageFile = file;
  const reader = new FileReader();
  
  reader.onload = (e) => {
    const imagePreview = document.getElementById('imagePreview');
    imagePreview.innerHTML = `
      <img src="${e.target.result}" alt="预览图片">
      <div class="file-info">
        <p>📁 ${file.name}</p>
        <p>💾 ${formatFileSize(file.size)}</p>
      </div>
    `;
    
    // 隐藏上传提示文本
    const uploadText = imagePreview.previousElementSibling;
    if (uploadText) {
      uploadText.style.display = 'none';
    }
  };
  
  reader.readAsDataURL(file);
}

/**
 * 格式化秒数为时间字符串 (mm:ss)
 */
function formatDuration(seconds) {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * 处理音频选择
 */
function handleAudioSelect(file) {
  if (!file) return;

  if (!file.type.startsWith('audio/')) {
    alert('请选择音频文件！');
    return;
  }

  audioFile = file;
  const reader = new FileReader();
  
  reader.onload = (e) => {
    const audioPreview = document.getElementById('audioPreview');
    
    // 创建临时音频元素获取时长
    const tempAudio = new Audio(e.target.result);
    
    tempAudio.onloadedmetadata = () => {
      const duration = tempAudio.duration;
      const durationText = formatDuration(duration);
      
      // 设置音频结束时间为实际时长
      document.getElementById('audioStartTime').value = '0:00';
      document.getElementById('audioEndTime').value = durationText;
      
      // 显示音频信息
      const durationInfo = document.getElementById('audioDurationInfo');
      const durationTextEl = document.getElementById('audioDurationText');
      durationInfo.style.display = 'block';
      durationTextEl.textContent = `时长 ${durationText} (${Math.round(duration)}秒)`;
      
      // 更新预览
      audioPreview.innerHTML = `
        <audio controls src="${e.target.result}"></audio>
        <div class="file-info">
          <p>📁 ${file.name}</p>
          <p>💾 ${formatFileSize(file.size)} | ⏱️ ${durationText}</p>
        </div>
      `;
      
      // 隐藏上传提示文本
      const uploadText = audioPreview.previousElementSibling;
      if (uploadText) {
        uploadText.style.display = 'none';
      }
    };
    
    tempAudio.onerror = () => {
      // 如果无法获取时长，使用默认预览
      audioPreview.innerHTML = `
        <audio controls src="${e.target.result}"></audio>
        <div class="file-info">
          <p>📁 ${file.name}</p>
          <p>💾 ${formatFileSize(file.size)}</p>
        </div>
      `;
      
      const uploadText = audioPreview.previousElementSibling;
      if (uploadText) {
        uploadText.style.display = 'none';
      }
    };
  };
  
  reader.readAsDataURL(file);
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * 初始化表单提交
 */
function initializeForm() {
  const form = document.getElementById('generateForm');
  const submitBtn = document.getElementById('submitBtn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!imageFile) {
      alert('请上传图片！');
      return;
    }
    
    if (!audioFile) {
      alert('请上传音频！');
      return;
    }

    // 禁用提交按钮
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ 正在提交...';

    try {
      await submitGeneration();
      // 提交成功后更新按钮文本
      submitBtn.textContent = '⏳ 等待生成...';
    } catch (error) {
      console.error('提交失败:', error);
      alert('提交失败: ' + error.message);
      submitBtn.disabled = false;
      submitBtn.textContent = '🚀 开始生成视频';
    }
  });
}

/**
 * 初始化尺寸同步
 */
function initializeSizeSync() {
  const widthSelect = document.getElementById('width');
  const heightSelect = document.getElementById('height');

  widthSelect.addEventListener('change', () => {
    syncSizeOptions();
  });

  heightSelect.addEventListener('change', () => {
    syncSizeOptions();
  });
}

/**
 * 同步尺寸选项
 */
function syncSizeOptions() {
  const width = parseInt(document.getElementById('width').value);
  const height = parseInt(document.getElementById('height').value);
  
  // 自动调整高度选项
  const heightSelect = document.getElementById('height');
  if (width === 720) {
    heightSelect.innerHTML = '<option value="480">480 (横屏)</option>';
    heightSelect.value = '480';
  } else if (width === 480) {
    heightSelect.innerHTML = '<option value="720">720 (竖屏)</option>';
    heightSelect.value = '720';
  } else if (width === 832) {
    heightSelect.innerHTML = '<option value="480">480 (宽屏)</option>';
    heightSelect.value = '480';
  }
}

/**
 * 提交生成请求
 */
async function submitGeneration() {
  const formData = new FormData();
  
  // 添加文件
  formData.append('image', imageFile);
  formData.append('audio', audioFile);
  
  // 添加参数
  formData.append('prompt', document.getElementById('prompt').value);
  formData.append('negative_prompt', document.getElementById('negativePrompt').value);
  formData.append('width', document.getElementById('width').value);
  formData.append('height', document.getElementById('height').value);
  formData.append('audio_start_time', document.getElementById('audioStartTime').value);
  formData.append('audio_end_time', document.getElementById('audioEndTime').value);
  formData.append('steps', document.getElementById('steps').value);
  formData.append('cfg', document.getElementById('cfg').value);
  formData.append('shift', document.getElementById('shift').value);
  formData.append('fps', document.getElementById('fps').value);
  formData.append('timeout', document.getElementById('timeout').value);
  
  const seed = document.getElementById('seed').value;
  if (seed) {
    formData.append('seed', seed);
  }

  // 发送请求
  const response = await fetch('/api/infinitetalk-i2v/generate', {
    method: 'POST',
    body: formData
  });

  const result = await response.json();

  if (!response.ok || result.code !== 200) {
    throw new Error(result.msg || '请求失败');
  }

  // 显示结果容器
  const resultContainer = document.getElementById('resultContainer');
  resultContainer.classList.add('show');

  // 保存任务ID
  currentTaskId = result.data.task_id;

  // 更新任务信息
  document.getElementById('taskId').textContent = currentTaskId;
  document.getElementById('videoSize').textContent = 
    `${document.getElementById('width').value} x ${document.getElementById('height').value}`;
  document.getElementById('seedValue').textContent = seed || '随机';

  // 更新状态
  updateStatus('pending', '任务已提交，等待处理...');

  // 开始轮询状态
  startStatusPolling();

  // 滚动到结果区域
  resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * 更新状态显示
 */
function updateStatus(status, message) {
  const statusBadge = document.getElementById('statusBadge');
  const progressBar = document.getElementById('progressBar');
  
  // 移除所有状态类
  statusBadge.classList.remove('status-pending', 'status-running', 'status-completed', 'status-failed');
  
  // 添加当前状态类
  statusBadge.classList.add(`status-${status}`);
  
  // 更新文本
  const statusText = {
    'pending': '⏳ 等待中',
    'running': '⚙️ 生成中',
    'completed': '✅ 已完成',
    'failed': '❌ 失败'
  };
  
  statusBadge.textContent = statusText[status] || status;
  
  // 显示/隐藏进度条
  if (status === 'running') {
    progressBar.style.display = 'block';
  } else {
    progressBar.style.display = 'none';
  }
}

/**
 * 开始轮询任务状态
 */
function startStatusPolling() {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
  }

  statusCheckInterval = setInterval(async () => {
    try {
      await checkTaskStatus();
    } catch (error) {
      console.error('状态检查失败:', error);
    }
  }, 2000); // 每2秒检查一次
}

/**
 * 停止轮询
 */
function stopStatusPolling() {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
    statusCheckInterval = null;
  }
}

/**
 * 检查任务状态
 */
async function checkTaskStatus() {
  if (!currentTaskId) return;

  const response = await fetch(`/api/task/${currentTaskId}`);
  const result = await response.json();

  if (!response.ok || result.code !== 200) {
    console.error('查询状态失败:', result.msg);
    return;
  }

  const task = result.data;
  const status = task.status;

  // 更新状态显示
  updateStatus(status);

  // 如果任务完成
  if (status === 'completed') {
    stopStatusPolling();
    displayResult(task);
    
    // 恢复提交按钮
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = false;
    submitBtn.textContent = '🚀 开始生成视频';
  }

  // 如果任务失败
  if (status === 'failed') {
    stopStatusPolling();
    displayError(task.error || '生成失败');
    
    // 恢复提交按钮
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = false;
    submitBtn.textContent = '🚀 开始生成视频';
  }
}

/**
 * 判断文件是否为视频文件
 */
function isVideoFile(filename) {
  const videoExtensions = ['.mp4', '.webm', '.gif', '.avi', '.mov', '.mkv', '.m4v', '.flv'];
  const lowerFilename = filename.toLowerCase();
  return videoExtensions.some(ext => lowerFilename.endsWith(ext));
}

/**
 * 显示生成结果
 */
function displayResult(task) {
  const videoResult = document.getElementById('videoResult');
  const errorMessage = document.getElementById('errorMessage');
  
  errorMessage.textContent = '';

  if (!task.result || !task.result.outputs) {
    displayError('未找到输出结果');
    return;
  }

  const outputs = task.result.outputs;
  const foundVideos = [];

  // 1. 检查 outputs.images 数组（可能包含视频文件）
  if (outputs.images && Array.isArray(outputs.images)) {
    outputs.images.forEach(img => {
      const filename = img.filename || '';
      if (isVideoFile(filename)) {
        foundVideos.push({
          filename: img.filename,
          subfolder: img.subfolder || '',
          type: img.type || 'output',
          node_id: img.node_id || 'unknown'
        });
      }
    });
  }

  // 2. 检查各节点的输出
  Object.entries(outputs).forEach(([nodeId, output]) => {
    // 检查 images 数组中的视频文件
    if (output.images && Array.isArray(output.images)) {
      output.images.forEach(img => {
        const filename = img.filename || '';
        if (isVideoFile(filename)) {
          // 避免重复添加
          if (!foundVideos.some(v => v.filename === img.filename)) {
            foundVideos.push({
              filename: img.filename,
              subfolder: img.subfolder || '',
              type: img.type || 'output',
              node_id: nodeId
            });
          }
        }
      });
    }

    // 检查 gifs 数组
    if (output.gifs && Array.isArray(output.gifs)) {
      output.gifs.forEach(video => {
        if (!foundVideos.some(v => v.filename === video.filename)) {
          foundVideos.push({
            filename: video.filename,
            subfolder: video.subfolder || '',
            type: video.type || 'output',
            node_id: nodeId,
            frame_rate: video.frame_rate,
            format: video.format
          });
        }
      });
    }

    // 检查 videos 数组
    if (output.videos && Array.isArray(output.videos)) {
      output.videos.forEach(video => {
        if (!foundVideos.some(v => v.filename === video.filename)) {
          foundVideos.push({
            filename: video.filename,
            subfolder: video.subfolder || '',
            type: video.type || 'output',
            node_id: nodeId
          });
        }
      });
    }
  });

  // 3. 检查 outputs.other 数组
  if (outputs.other && Array.isArray(outputs.other)) {
    outputs.other.forEach(item => {
      if (item.type === 'gifs' && item.data && Array.isArray(item.data)) {
        item.data.forEach(video => {
          if (!foundVideos.some(v => v.filename === video.filename)) {
            foundVideos.push({
              filename: video.filename,
              subfolder: video.subfolder || '',
              type: video.type || 'output',
              node_id: item.node_id || 'unknown',
              frame_rate: video.frame_rate,
              format: video.format
            });
          }
        });
      }
    });
  }

  // 显示找到的视频
  if (foundVideos.length > 0) {
    let html = '<div class="video-gallery">';
    
    foundVideos.forEach((video, index) => {
      // 构建视频URL - 修复：只在subfolder非空时才添加参数
      let videoUrl = `/api/video/${video.filename}?type=${video.type}`;
      if (video.subfolder && video.subfolder.trim() !== '') {
        videoUrl += `&subfolder=${encodeURIComponent(video.subfolder)}`;
      }
      
      html += `
        <div class="video-item">
          <h4>生成的视频 ${foundVideos.length > 1 ? (index + 1) : ''}</h4>
          <video controls class="result-video" preload="metadata">
            <source src="${videoUrl}" type="video/mp4">
            您的浏览器不支持视频播放
          </video>
          <div style="margin: 10px 0; font-size: 12px; color: #666;">
            ${video.frame_rate ? `帧率: ${video.frame_rate} fps | ` : ''}
            文件: ${video.filename}
            ${video.node_id ? ` | 节点: ${video.node_id}` : ''}
          </div>
          <div class="video-actions">
            <a href="${videoUrl}" download="${video.filename}" class="download-btn">
              💾 下载视频
            </a>
            <a href="${videoUrl}" target="_blank" class="download-btn" style="margin-left: 10px;">
              🔗 新窗口打开
            </a>
          </div>
        </div>
      `;
    });
    
    html += '</div>';
    videoResult.innerHTML = html;
    
    console.log('找到视频:', foundVideos);
  } else {
    displayError('未找到视频输出');
    console.log('完整输出数据:', outputs);
  }
}

/**
 * 显示错误信息
 */
function displayError(message) {
  const errorMessage = document.getElementById('errorMessage');
  errorMessage.textContent = `❌ 错误: ${message}`;
  
  const videoResult = document.getElementById('videoResult');
  videoResult.innerHTML = '';
}

