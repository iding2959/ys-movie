let uploadedFilename = null;
let ws = null;
let refreshButtonResetTimer = null;

// 任务名称管理
const TaskNameManager = {
  // 保存任务名称
  save(taskId, taskName) {
    if (!taskName || !taskName.trim()) return;
    const taskNames = this.getAll();
    taskNames[taskId] = taskName.trim();
    localStorage.setItem('super_video_task_names', JSON.stringify(taskNames));
  },
  
  // 获取任务名称
  get(taskId) {
    const taskNames = this.getAll();
    return taskNames[taskId] || '';
  },
  
  // 获取所有任务名称
  getAll() {
    try {
      const data = localStorage.getItem('super_video_task_names');
      return data ? JSON.parse(data) : {};
    } catch (e) {
      return {};
    }
  },
  
  // 删除任务名称
  delete(taskId) {
    const taskNames = this.getAll();
    delete taskNames[taskId];
    localStorage.setItem('super_video_task_names', JSON.stringify(taskNames));
  }
};

// 判断是否为视频文件
function isVideoFile(filename) {
  const videoExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'];
  return videoExtensions.some(ext => filename.toLowerCase().endsWith(ext));
}

// 判断是否为临时文件
function isTempFile(filename) {
  if (!filename) return true;
  // 过滤ComfyUI临时文件
  return filename.includes('_temp_') || 
         filename.startsWith('temp_') || 
         filename.includes('ComfyUI_temp');
}

// 过滤出最终输出文件
function filterFinalOutputs(images) {
  if (!images || !Array.isArray(images)) return [];
  const filtered = images.filter(img => !isTempFile(img.filename || ''));
  console.log(`文件过滤: 总数=${images.length}, 临时文件=${images.length - filtered.length}, 最终文件=${filtered.length}`);
  return filtered;
}

// WebSocket连接
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    console.log('WebSocket已连接');
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'task_update') {
        loadTasks();
      }
    } catch (e) {
      console.error('解析WebSocket消息失败:', e);
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket错误:', error);
  };
  
  ws.onclose = () => {
    console.log('WebSocket已断开，3秒后重连...');
    setTimeout(connectWebSocket, 3000);
  };
}

// 标签切换
function switchTab(tab) {
  const analysisTab = document.getElementById('analysisTab');
  const historyTab = document.getElementById('historyTab');
  const analysisPanel = document.getElementById('analysisPanel');
  const historyPanel = document.getElementById('historyPanel');

  // 移除所有active状态
  document.querySelectorAll('.action-btn').forEach(btn => {
    if (btn.id === 'analysisTab' || btn.id === 'historyTab') {
      btn.classList.remove('active');
    }
  });

  if (tab === 'analysis') {
    analysisTab.classList.add('active');
    analysisPanel.style.display = 'block';
    historyPanel.style.display = 'none';
  } else {
    historyTab.classList.add('active');
    analysisPanel.style.display = 'none';
    historyPanel.style.display = 'block';
    loadTasks();
  }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  connectWebSocket();
  loadTasks();
  initUploadArea();
  initModelSelect();
  initSubmitButton();
  initRefreshButton();
});

function initRefreshButton() {
  const refreshBtn = document.getElementById('refreshBtn');
  if (!refreshBtn) {
    return;
  }

  setRefreshButtonState('idle');

  refreshBtn.addEventListener('click', async () => {
    if (refreshBtn.dataset.state === 'loading') {
      return;
    }

    setRefreshButtonState('loading');
    showToast('正在刷新任务列表...', 'info');

    try {
      await loadTasks({ manual: true });
      setRefreshButtonState('success');
      showToast('任务列表已更新', 'success');
      scheduleRefreshButtonReset(1200);
    } catch (error) {
      console.error('刷新任务列表失败:', error);
      setRefreshButtonState('error');
      showToast(`刷新失败: ${error.message}`, 'error');
      scheduleRefreshButtonReset(2000);
    }
  });
}

function scheduleRefreshButtonReset(delay) {
  if (refreshButtonResetTimer) {
    clearTimeout(refreshButtonResetTimer);
  }

  refreshButtonResetTimer = setTimeout(() => {
    setRefreshButtonState('idle');
    refreshButtonResetTimer = null;
  }, delay);
}

function setRefreshButtonState(state) {
  const refreshBtn = document.getElementById('refreshBtn');
  if (!refreshBtn) {
    return;
  }

  const icon = refreshBtn.querySelector('.action-icon');
  const text = refreshBtn.querySelector('.action-text');

  refreshBtn.classList.remove('loading', 'success', 'error');
  refreshBtn.disabled = false;
  refreshBtn.dataset.state = state;

  if (icon) {
    icon.textContent = '🔄';
  }
  if (text) {
    text.textContent = '刷新';
  }

  if (state === 'loading') {
    refreshBtn.classList.add('loading');
    refreshBtn.disabled = true;
    if (text) {
      text.textContent = '刷新中';
    }
  } else if (state === 'success') {
    refreshBtn.classList.add('success');
    if (icon) {
      icon.textContent = '✅';
    }
    if (text) {
      text.textContent = '已刷新';
    }
  } else if (state === 'error') {
    refreshBtn.classList.add('error');
    if (icon) {
      icon.textContent = '⚠️';
    }
    if (text) {
      text.textContent = '刷新失败';
    }
  } else {
    refreshBtn.dataset.state = 'idle';
  }
}

// 初始化上传区域
function initUploadArea() {
  const uploadArea = document.getElementById('uploadArea');
  const videoInput = document.getElementById('videoInput');
  const changeVideoBtn = document.getElementById('changeVideoBtn');

  if (!uploadArea || !videoInput) {
    console.error('上传区域初始化失败：缺少必要元素', {
      uploadArea: !!uploadArea,
      videoInput: !!videoInput
    });
    return;
  }

  console.log('初始化上传区域，绑定事件监听器');

  uploadArea.onclick = () => {
    console.log('点击上传区域，触发文件选择');
    videoInput.click();
  };

  uploadArea.ondragover = (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
  };

  uploadArea.ondragleave = () => {
    uploadArea.classList.remove('dragover');
  };

  uploadArea.ondrop = (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    console.log('拖放文件，文件数量:', e.dataTransfer.files.length);
    if (e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  videoInput.onchange = (e) => {
    console.log('文件选择器变化，文件数量:', e.target.files.length);
    if (e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  };

  // 更换视频按钮点击事件
  if (changeVideoBtn) {
    changeVideoBtn.onclick = (e) => {
      e.stopPropagation();
      resetUploadArea();
    };
  }

  console.log('上传区域初始化完成');
}

// 重置上传区域
function resetUploadArea() {
  const uploadArea = document.getElementById('uploadArea');
  const videoPreview = document.getElementById('videoPreview');
  const fileInfo = document.getElementById('fileInfo');
  const previewVideo = document.getElementById('previewVideo');
  const videoInput = document.getElementById('videoInput');
  const submitBtn = document.getElementById('submitBtn');

  // 重置上传文件名
  uploadedFilename = null;

  // 重置视频输入
  videoInput.value = '';

  // 重置文件信息显示和样式
  if (fileInfo) {
    fileInfo.style.display = 'none';
    fileInfo.textContent = '';
    fileInfo.style.background = '';
    fileInfo.style.color = '';
    fileInfo.style.alignItems = '';
    fileInfo.style.justifyContent = '';
  }

  // 禁用提交按钮
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = '🚀 提交';
  }

  // 重置视频预览
  if (previewVideo) {
    previewVideo.pause(); // 停止播放
    previewVideo.src = '';
    previewVideo.load(); // 确保视频元素被重置
  }

  // 立即隐藏预览区域
  if (videoPreview) {
    videoPreview.classList.remove('show');
    videoPreview.style.display = 'none';
    videoPreview.style.opacity = '';
  }

  // 立即恢复上传区域显示（不等待动画）
  if (uploadArea) {
    // 使用 grid 布局以保持图标居中（与CSS一致）
    uploadArea.style.display = 'grid';
    uploadArea.style.opacity = '1';
    uploadArea.style.visibility = 'visible';
    uploadArea.style.transition = ''; // 清除可能的过渡效果
    uploadArea.style.height = ''; // 恢复默认高度
    uploadArea.style.width = ''; // 恢复默认宽度
    // 确保上传区域回到正常状态
    uploadArea.classList.remove('dragover');
  }
}

// 处理文件选择
async function handleFileSelect(file) {
  console.log('handleFileSelect 被调用，文件:', file.name, '大小:', file.size);

  const uploadArea = document.getElementById('uploadArea');
  const fileInfo = document.getElementById('fileInfo');
  const videoPreview = document.getElementById('videoPreview');
  const previewVideo = document.getElementById('previewVideo');
  const submitBtn = document.getElementById('submitBtn');

  // 检查必要元素是否存在
  if (!fileInfo || !submitBtn) {
    console.error('缺少必要的DOM元素:', {
      fileInfo: !!fileInfo,
      submitBtn: !!submitBtn
    });
    showModal('错误', '页面元素加载不完整，请刷新页面重试', 'error');
    return;
  }

  // 先加载视频预览，并在元数据就绪后检查分辨率
  if (previewVideo) {
    const url = URL.createObjectURL(file);

    // 重置视频样式，确保保持原始宽高比
    previewVideo.style.width = '100%';
    previewVideo.style.height = 'auto';
    previewVideo.style.maxHeight = '600px';
    previewVideo.style.objectFit = 'contain';
    previewVideo.style.display = 'block';

    previewVideo.src = url;

    // 等待视频元数据加载完成后再进行分辨率校验和上传
    previewVideo.onloadedmetadata = async () => {
      const width = previewVideo.videoWidth;
      const height = previewVideo.videoHeight;

      console.log('检测到视频分辨率:', width, 'x', height);

      if (videoPreview) {
        // 让容器自适应视频高度
        videoPreview.style.height = 'auto';
        videoPreview.style.display = 'block';

        setTimeout(() => {
          videoPreview.classList.add('show');
          if (uploadArea) {
            uploadArea.style.opacity = '0';
          }
        }, 10);

        setTimeout(() => {
          if (uploadArea) {
            uploadArea.style.display = 'none';
          }
        }, 300);
      }
      await uploadVideoFile(file, fileInfo, submitBtn, uploadArea, videoPreview, previewVideo);
    };
  }
}

/**
 * 上传视频文件并根据结果更新 UI 状态
 * @param {File} file - 选择的视频文件
 * @param {HTMLElement} fileInfo - 显示上传状态的元素
 * @param {HTMLButtonElement} submitBtn - 提交按钮
 * @param {HTMLElement} uploadArea - 上传区域容器
 * @param {HTMLElement} videoPreview - 视频预览容器
 * @param {HTMLVideoElement} previewVideo - 预览用 video 元素
 */
async function uploadVideoFile(
  file,
  fileInfo,
  submitBtn,
  uploadArea,
  videoPreview,
  previewVideo
) {
  // 显示上传状态
  fileInfo.style.display = 'flex';
  fileInfo.style.alignItems = 'center';
  fileInfo.style.justifyContent = 'space-between';
  fileInfo.textContent = `⏳ 上传中: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
  fileInfo.style.background = '#e3f2fd';
  fileInfo.style.color = '#1976d2';

  // 禁用提交按钮
  submitBtn.disabled = true;
  submitBtn.textContent = '⏳ 上传中...';

  try {
    console.log('开始创建FormData并准备上传...');
    const formData = new FormData();
    formData.append('file', file);
    console.log('FormData已创建，准备发送请求到 /api/upload/video');

    const response = await fetch('/api/upload/video', {
      method: 'POST',
      body: formData
    });

    console.log('上传请求已发送，响应状态:', response.status, response.statusText);

    const result = await response.json();
    console.log('视频上传API返回:', result);

    // 支持code: 0, code: 200, success: true三种成功标识
    if (result.code === 0 || result.code === 200 || result.success === true) {
      uploadedFilename = result.data.filename;
      console.log('上传成功，文件名:', uploadedFilename);
      fileInfo.textContent = `✅ 已选择: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB) - 上传成功`;
      fileInfo.style.background = '#e8f5e9';
      fileInfo.style.color = '#2e7d32';
      submitBtn.disabled = false;
      submitBtn.textContent = '🚀 提交';
    } else {
      throw new Error(result.message || '上传失败');
    }
  } catch (error) {
    console.error('上传失败:', error);
    console.error('错误堆栈:', error.stack);
    fileInfo.textContent = `❌ 上传失败: ${error.message}`;
    fileInfo.style.background = '#ffebee';
    fileInfo.style.color = '#c62828';
    submitBtn.disabled = true;
    submitBtn.textContent = '🚀 提交';

    // 上传失败，恢复显示上传区域
    if (videoPreview) {
      videoPreview.classList.remove('show');
      setTimeout(() => {
        if (videoPreview) videoPreview.style.display = 'none';
        if (uploadArea) {
          uploadArea.style.display = 'grid'; // 使用 grid 以保持图标居中
          uploadArea.style.opacity = '1';
        }
        if (previewVideo) previewVideo.src = '';
      }, 300);
    }
  }
}

// 初始化模型选择
function initModelSelect() {
  // 检查是否已有选中的模型
  const checkedModel = document.querySelector('input[name="modelSelect"]:checked');
  if (checkedModel) {
    return;
  }
  
  // 默认选中第一个模型（FlashVSR）
  const firstModel = document.querySelector('input[name="modelSelect"]');
  if (firstModel) {
    firstModel.checked = true;
  }
}

// 自定义模态框
function showModal(title, message, type = 'info') {
  // 创建模态框 HTML
  const modal = document.createElement('div');
  modal.className = 'custom-alert-modal';
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    animation: fadeIn 0.3s ease;
  `;

  const iconMap = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️'
  };

  const colorMap = {
    'success': '#4caf50',
    'error': '#f44336',
    'warning': '#ff9800',
    'info': '#2196f3'
  };

  modal.innerHTML = `
    <div class="custom-alert-content" style="
      background: white;
      border-radius: 16px;
      padding: 30px;
      max-width: 400px;
      width: 90%;
      box-shadow: 0 10px 40px rgba(0,0,0,0.3);
      animation: slideIn 0.3s ease;
      text-align: center;
    ">
      <div style="font-size: 48px; margin-bottom: 15px;">${iconMap[type]}</div>
      <h3 style="margin: 0 0 15px 0; color: ${colorMap[type]}; font-size: 20px;">${title}</h3>
      <p style="margin: 0 0 25px 0; color: #666; white-space: pre-wrap; line-height: 1.6;">${message}</p>
      <button onclick="this.closest('.custom-alert-modal').remove()" style="
        background: ${colorMap[type]};
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 8px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s;
      " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 5px 15px rgba(0,0,0,0.2)'"
         onmouseout="this.style.transform=''; this.style.boxShadow=''">
        确定
      </button>
    </div>
  `;

  document.body.appendChild(modal);

  // 点击背景关闭
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });

  // 添加动画样式
  if (!document.getElementById('custom-alert-styles')) {
    const style = document.createElement('style');
    style.id = 'custom-alert-styles';
    style.textContent = `
      @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      @keyframes slideIn {
        from { transform: translateY(-50px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
      }
    `;
    document.head.appendChild(style);
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) {
    return;
  }

  const supportedTypes = ['success', 'error', 'info'];
  const toastType = supportedTypes.includes(type) ? type : 'info';
  const toast = document.createElement('div');
  toast.className = `toast toast-${toastType}`;
  toast.textContent = message;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 2200);
}

// 确认对话框
function showConfirm(title, message, onConfirm) {
  const modal = document.createElement('div');
  modal.className = 'custom-confirm-modal';
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    animation: fadeIn 0.3s ease;
  `;

  modal.innerHTML = `
    <div class="custom-confirm-content" style="
      background: white;
      border-radius: 16px;
      padding: 30px;
      max-width: 400px;
      width: 90%;
      box-shadow: 0 10px 40px rgba(0,0,0,0.3);
      animation: slideIn 0.3s ease;
    ">
      <div style="font-size: 48px; margin-bottom: 15px; text-align: center;">⚠️</div>
      <h3 style="margin: 0 0 15px 0; color: #ff9800; font-size: 20px; text-align: center;">${title}</h3>
      <p style="margin: 0 0 25px 0; color: #666; white-space: pre-wrap; line-height: 1.6; text-align: center;">${message}</p>
      <div style="display: flex; gap: 10px; justify-content: center;">
        <button class="confirm-cancel" style="
          background: #e0e0e0;
          color: #666;
          border: none;
          padding: 12px 30px;
          border-radius: 8px;
          font-size: 16px;
          font-weight: bold;
          cursor: pointer;
          transition: all 0.3s;
        ">取消</button>
        <button class="confirm-ok" style="
          background: #f44336;
          color: white;
          border: none;
          padding: 12px 30px;
          border-radius: 8px;
          font-size: 16px;
          font-weight: bold;
          cursor: pointer;
          transition: all 0.3s;
        ">确定</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  modal.querySelector('.confirm-cancel').onclick = () => modal.remove();
  modal.querySelector('.confirm-ok').onclick = () => {
    modal.remove();
    onConfirm();
  };

  // 点击背景关闭
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

// 初始化提交按钮
function initSubmitButton() {
  document.getElementById('submitBtn').onclick = async () => {
    // 获取处理选项（前端展示用，不回传processing_option）
    const selectedOption = document.querySelector('input[name="processingOption"]:checked');
    
    // 模型选择，回传后端
    const modelRadio = document.querySelector('input[name="modelSelect"]:checked');
    const modelName = modelRadio && modelRadio.value ? modelRadio.value : 'FlashVSR';
    
    const taskNameInput = document.getElementById('taskNameInput');
    const userTaskName = taskNameInput.value.trim();
    const submitBtn = document.getElementById('submitBtn');

    if (!uploadedFilename) {
      showModal('提示', '请先上传视频文件', 'warning');
      return;
    }
    
    // 检查是否选择了一个处理选项
    if (!selectedOption) {
      showModal('提示', '请选择一个处理选项', 'warning');
      return;
    }

    // 根据选项确定工作流（仅回传 workflow_key）
    const workflowKey = selectedOption && selectedOption.value === 'seedvr2'
      ? 'seedvr2'
      : 'flash_vsr';

    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ 提交中...';

    let response, result;
    try {
      // 自动生成任务名称（使用时间戳）
      const taskName = `sv_${Date.now()}`;
      
      console.log('提交任务数据:', {
        task_name: taskName,
        model_name: modelName,
        video_filename: uploadedFilename,
        workflow_key: workflowKey
      });
      
      response = await fetch('/api/super_video/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          task_name: taskName,
          model_name: modelName,
          video_filename: uploadedFilename,
          workflow_key: workflowKey
        })
      });

      result = await response.json();

      console.log('提交任务API返回:', result);
      console.log('HTTP状态码:', response.status);
      
      // 如果有错误详情，打印出来
      if (result.detail) {
        console.error('API错误详情:', result.detail);
      }

      // 支持多种成功状态码
      if (result.code === 0 || result.code === 200 || result.success === true) {
        // 保存用户输入的任务名称（如果有）
        if (userTaskName) {
          TaskNameManager.save(result.data.task_id, userTaskName);
        }
        
        // 构建成功消息
        let successMessage = '任务已成功提交！';
        if (userTaskName) {
          successMessage += `\n任务名称: ${userTaskName}`;
        }
        successMessage += `\n任务ID: ${result.data.task_id}`;
        
        showModal(
          '提交成功', 
          successMessage, 
          'success'
        );
        loadTasks();
        
        // 重置表单
        taskNameInput.value = '';
        // 重置上传区域
        resetUploadArea();
      } else {
        // 提供更详细的错误信息
        const errorMsg = result.message || result.detail || '提交失败';
        throw new Error(errorMsg);
      }
    } catch (error) {
      console.error('提交失败:', error);
      console.error('完整错误对象:', JSON.stringify(error, null, 2));
      
      let errorMessage = error.message;
      
      // 处理FastAPI验证错误（422状态码）
      if (response && response.status === 422 && result && result.detail) {
        if (Array.isArray(result.detail)) {
          // 格式化验证错误信息
          const errors = result.detail.map(err => {
            const field = err.loc ? err.loc.join('.') : 'unknown';
            return `${field}: ${err.msg}`;
          }).join('\n');
          errorMessage = `请求参数错误:\n${errors}`;
        } else {
          errorMessage = result.detail;
        }
      }
      
      showModal('提交失败', errorMessage, 'error');
    } finally {
      submitBtn.disabled = !uploadedFilename;
      submitBtn.textContent = '🚀 提交';
    }
  };
}

// 加载任务列表
async function loadTasks(options = {}) {
  const { manual = false } = options;
  const taskList = document.getElementById('taskList');

  try {
    const response = await fetch('/api/tasks');
    const result = await response.json();

    console.log('API返回完整数据:', result);

    // 处理不同的响应格式
    let tasks = [];
    // 检查多种成功状态：code === 0 或 code === 200 或 success === true
    if ((result.code === 0 || result.code === 200 || result.success === true) && result.data) {
      // 新格式：{code: 200, data: {total: 6, tasks: [...]}}
      if (result.data.tasks && Array.isArray(result.data.tasks)) {
        tasks = result.data.tasks;
        console.log('使用新格式，解析到任务数:', tasks.length);
      }
      // 旧格式：{code: 0, data: [...]}
      else if (Array.isArray(result.data)) {
        tasks = result.data;
        console.log('使用旧格式，解析到任务数:', tasks.length);
      }
      else {
        console.error('无法识别的data格式:', result.data);
      }
    } else if (Array.isArray(result)) {
      tasks = result;
      console.log('直接数组格式，任务数:', tasks.length);
    }

    if (tasks.length === 0) {
      console.log('没有解析到任何任务');
      taskList.innerHTML = '<div class="empty-state">暂无任务<br><span style="font-size: 12px;">提交任务后将在此显示</span></div>';
      return true;
    }

    console.log('任务列表:', tasks.map(t => ({id: t.task_id, type: t.workflow_type})));

    // 按创建时间倒序排列（最新的在最上面）
    tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    taskList.innerHTML = tasks.map((task, index) => {
      // 状态图标和文本
      const statusIcons = {
        'running': '⏳',
        'pending': '⏸️',
        'submitted': '📤',
        'completed': '✅',
        'failed': '❌'
      };
      const statusIcon = statusIcons[task.status] || '📋';
      
      const statusText = {
        'running': '运行中',
        'pending': '排队中',
        'submitted': '已提交',
        'completed': '已完成',
        'failed': '失败'
      };
      const displayStatus = statusText[task.status] || task.status;

      // 来源文本
      const sourceText = {
        'queue': '队列',
        'history': '历史记录',
        'local': '当前会话'
      };
      const displaySource = sourceText[task.source] || task.source || '未知';

      // 时间格式化
      const createdTime = new Date(task.created_at).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
      const completedTime = task.completed_at ? 
        `<br>完成时间: ${new Date(task.completed_at).toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        })}` : '';

      // 结果预览（复刻首页逻辑）
      let resultPreview = '';
      if (task.result && task.result.outputs) {
        const images = task.result.outputs.images || [];
        // 过滤临时文件
        const finalImages = filterFinalOutputs(images);
        
        if (finalImages.length > 0) {
          resultPreview = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; margin-top: 15px;">
              ${finalImages.slice(0, 4).map(img => {
                const filename = img.filename || '';
                const subfolder = img.subfolder || '';
                const type = img.type || 'output';
                
                if (isVideoFile(filename)) {
                  let videoUrl = `/api/video/${filename}?type=${type}`;
                  if (subfolder && subfolder.trim() !== '') {
                    videoUrl += `&subfolder=${subfolder}`;
                  }
                  return '<div style="position: relative; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; height: 100px; display: flex; align-items: center; justify-content: center; cursor: pointer;"><div style="color: white; text-align: center;"><div style="font-size: 30px;">🎬</div><div style="font-size: 10px;">点击播放</div></div><div style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); color: white; padding: 2px 6px; border-radius: 3px; font-size: 9px;">📹 视频</div></div>';
                } else {
                  const imageUrl = `/api/image/${filename}?subfolder=${subfolder}&type=${type}`;
                  return '<div style="border-radius: 8px; overflow: hidden; height: 100px; background: #f0f0f0;"><img src="' + imageUrl + '" alt="Result" loading="lazy" style="width: 100%; height: 100%; object-fit: cover;"></div>';
                }
              }).join('')}
            </div>
            ${finalImages.length > 4 ? `<p style="color: #999; font-size: 12px; margin-top: 10px;">还有 ${finalImages.length - 4} 个文件...</p>` : ''}
          `;
        }
      }

      // 获取用户自定义的任务名称
      const customTaskName = TaskNameManager.get(task.task_id);
      const taskNameDisplay = customTaskName 
        ? `<div style="font-size: 16px; font-weight: 600; color: #2d3748; margin-bottom: 8px;">📝 ${customTaskName}</div>`
        : '';

      return `
        <div class="task-item ${task.status}">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
            <div style="flex: 1; min-width: 0;">
              ${taskNameDisplay}
              <span style="font-family: monospace; font-size: 13px; color: #666;">${task.task_id}</span>
            </div>
            <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 10px;">
              <span class="task-status ${task.status}" style="flex-shrink: 0;">${statusIcon} ${displayStatus}</span>
              <button onclick="showTaskDetail('${task.task_id}')" style="padding: 10px 24px; font-size: 14px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; cursor: pointer; transition: all 0.3s; white-space: nowrap;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 5px 15px rgba(102,126,234,0.4)'" onmouseout="this.style.transform=''; this.style.boxShadow=''">
                查看详情
              </button>
            </div>
          </div>
          <div style="color: #666; font-size: 13px; margin-bottom: 10px; line-height: 1.8;">
            创建时间: ${createdTime}${completedTime}
          </div>
          ${resultPreview}
          ${task.error ? `<div style="color: #f44336; margin-top: 10px; font-size: 13px; padding: 10px; background: #ffebee; border-radius: 6px;">❌ ${task.error}</div>` : ''}
        </div>
      `;
    }).join('');

    return true;
  } catch (error) {
    console.error('加载任务列表失败:', error);
    taskList.innerHTML = `<div class="empty-state" style="color: #d32f2f;">❌ 加载失败<br><span style="font-size: 12px;">${error.message}</span></div>`;
    if (manual) {
      throw error;
    }
    return false;
  }
}

// 显示任务详情（参考首页逻辑）
async function showTaskDetail(taskId) {
  const modal = document.getElementById('taskDetailModal');
  const content = document.getElementById('taskDetailContent');
  
  // 显示加载状态
  content.innerHTML = `
    <div style="text-align: center; padding: 50px; color: #666;">
      <div style="font-size: 40px; margin-bottom: 20px;">⏳</div>
      <div style="font-size: 16px;">正在加载任务详情...</div>
    </div>
  `;
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  
  try {
    // 从API获取任务详情
    const response = await fetch(`/api/task/${taskId}`);
    const result = await response.json();
    
    console.log('任务详情API返回:', result);
    
    // 处理统一响应格式
    const data = result.data || result;
    
    // 时间格式化函数
    const formatDateTime = (dateStr) => {
      if (!dateStr) return '';
      return new Date(dateStr).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    };
    
    let imagesHtml = '';
    let videosHtml = '';
    
    if (data.result && data.result.outputs) {
      const outputs = data.result.outputs;
      
      // 处理 outputs.images 数组（可能包含图片和视频）
      if (outputs.images && Array.isArray(outputs.images)) {
        outputs.images.forEach(img => {
          const filename = img.filename || '';
          const subfolder = img.subfolder || '';
          const type = img.type || 'output';
          const nodeId = img.node_id || 'unknown';
          
          // 跳过临时文件
          if (isTempFile(filename)) {
            return;
          }
          
          if (isVideoFile(filename)) {
            // 视频文件
            let videoUrl = `/api/video/${filename}?type=${type}`;
            if (subfolder && subfolder.trim() !== '') {
              videoUrl += `&subfolder=${subfolder}`;
            }
            
            videosHtml += `
              <div style="margin: 10px 0;"><strong>节点 ${nodeId} (视频):</strong></div>
              <video controls preload="metadata" style="max-width: 100%; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <source src="${videoUrl}" type="video/mp4">
                您的浏览器不支持视频播放
              </video>
              <div style="font-size: 12px; color: #666; margin-bottom: 15px;">
                文件: ${filename} | 位置: ${subfolder || '默认输出'}
              </div>
            `;
          } else {
            // 图片文件
            const imgUrl = `/api/image/${filename}?subfolder=${subfolder}&type=${type}`;
            imagesHtml += `
              <div style="margin: 10px 0;"><strong>节点 ${nodeId}:</strong></div>
              <img src="${imgUrl}" style="max-width: 100%; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer;" onclick="window.open('${imgUrl}', '_blank')" />
            `;
          }
        });
      }
      
      // 处理各节点的输出（旧格式兼容）
      Object.entries(outputs).forEach(([nodeId, output]) => {
        if (output.images && output.images.length > 0) {
          output.images.forEach((img, idx) => {
            const filename = img.filename || '';
            const subfolder = img.subfolder || '';
            const type = img.type || 'output';
            
            // 跳过临时文件
            if (isTempFile(filename)) {
              return;
            }
            
            if (isVideoFile(filename)) {
              let videoUrl = `/api/video/${filename}?type=${type}`;
              if (subfolder && subfolder.trim() !== '') {
                videoUrl += `&subfolder=${subfolder}`;
              }
              
              videosHtml += `
                <div style="margin: 10px 0;"><strong>节点 ${nodeId} (视频):</strong></div>
                <video controls preload="metadata" style="max-width: 100%; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                  <source src="${videoUrl}" type="video/mp4">
                  您的浏览器不支持视频播放
                </video>
              `;
            } else {
              const imgUrl = `/api/image/${filename}?subfolder=${subfolder}&type=${type}`;
              if (!imagesHtml.includes(imgUrl)) {
                imagesHtml += `<div style="margin: 10px 0;"><strong>节点 ${nodeId}:</strong></div>`;
                imagesHtml += `<img src="${imgUrl}" style="max-width: 100%; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer;" onclick="window.open('${imgUrl}', '_blank')" />`;
              }
            }
          });
        }
        
        // 处理 gifs 输出（视频）
        if (output.gifs && output.gifs.length > 0) {
          videosHtml += `<div style="margin: 10px 0;"><strong>节点 ${nodeId} (视频):</strong></div>`;
          output.gifs.forEach(video => {
            let videoUrl = `/api/video/${video.filename}?type=${video.type || 'output'}`;
            if (video.subfolder && video.subfolder.trim() !== '') {
              videoUrl += `&subfolder=${video.subfolder}`;
            }
            
            videosHtml += `
              <video controls preload="metadata" style="max-width: 100%; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <source src="${videoUrl}" type="${video.format || 'video/mp4'}">
                您的浏览器不支持视频播放
              </video>
              <div style="font-size: 12px; color: #666; margin-bottom: 15px;">
                帧率: ${video.frame_rate || 'N/A'} fps | 文件: ${video.filename}
              </div>
            `;
          });
        }
      });
      
      // 处理 outputs.other 数组（包含 gifs 等）
      if (outputs.other && Array.isArray(outputs.other)) {
        outputs.other.forEach(item => {
          if (item.type === 'gifs' && item.data && Array.isArray(item.data)) {
            const nodeId = item.node_id || 'unknown';
            videosHtml += `
              <div style="margin: 15px 0;">
                <div style="padding: 10px; background: #f5f5f5; border-radius: 8px; font-weight: bold; margin-bottom: 10px;">
                  📹 节点 ${nodeId} - 生成的视频 (${item.data.length}个)
                </div>
            `;
            item.data.forEach((video, index) => {
              let videoUrl = `/api/video/${video.filename}?type=${video.type || 'output'}`;
              if (video.subfolder && video.subfolder.trim() !== '') {
                videoUrl += `&subfolder=${video.subfolder}`;
              }
              
              // 调试信息
              console.log(`视频 ${index + 1}:`, {
                filename: video.filename,
                subfolder: video.subfolder,
                type: video.type,
                url: videoUrl
              });
              
              const videoId = `video_${nodeId}_${index}`;
              
              // 标准化MIME类型
              let mimeType = 'video/mp4';
              if (video.format) {
                // video/h264-mp4 -> video/mp4
                if (video.format.includes('mp4')) {
                  mimeType = 'video/mp4';
                } else if (video.format.includes('webm')) {
                  mimeType = 'video/webm';
                } else {
                  mimeType = video.format;
                }
              }
              
              videosHtml += `
                <div style="margin: 10px 0;">
                  <strong>节点 ${nodeId}:</strong>
                  <span style="color: #999; font-size: 12px; margin-left: 10px;">URL: ${videoUrl}</span>
                </div>
                <div style="position: relative;">
                  <video 
                    id="${videoId}"
                    controls 
                    preload="metadata" 
                    style="max-width: 100%; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
                    onerror="console.error('视频加载失败:', '${videoUrl}'); this.nextElementSibling.style.display='block';"
                    onloadeddata="console.log('视频加载成功:', '${videoUrl}')">
                    <source src="${videoUrl}" type="${mimeType}">
                    您的浏览器不支持视频播放
                  </video>
                  <div style="display: none; padding: 10px; background: #ffebee; color: #c62828; border-radius: 5px; margin: 10px 0;">
                    ⚠️ 视频加载失败，请尝试：
                    <a href="${videoUrl}" target="_blank" style="color: #c62828; text-decoration: underline;">直接访问视频链接</a>
                  </div>
                </div>
                <div style="margin: 10px 0;">
                  <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
                    帧率: ${video.frame_rate || 'N/A'} fps | 文件: ${video.filename}
                  </div>
                  <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <a href="${videoUrl}" target="_blank" style="display: inline-block; padding: 6px 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 5px; font-size: 12px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                      🔗 新窗口打开
                    </a>
                    <a href="${videoUrl}" download="${video.filename}" style="display: inline-block; padding: 6px 12px; background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); color: white; text-decoration: none; border-radius: 5px; font-size: 12px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                      💾 下载
                    </a>
                  </div>
                </div>
              `;
            });
            videosHtml += `</div>`;
          }
        });
      }
    }
    
    // 获取任务名称
    const customTaskName = TaskNameManager.get(data.task_id);
    const taskNameSection = customTaskName 
      ? `<div style="margin: 20px 0; padding: 15px; background: linear-gradient(135deg, #f0f4ff 0%, #e6f0ff 100%); border-left: 4px solid #667eea; border-radius: 10px;">
          <strong style="color: #667eea;">📝 任务名称:</strong> 
          <span style="font-size: 16px; color: #2d3748; margin-left: 10px;">${customTaskName}</span>
        </div>`
      : '';
    
    // 失败原因显示
    let errorSection = '';
    if (data.status === 'failed') {
      const errorMessage = data.error || data.error_message || '未知错误';
      errorSection = `
        <div style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border-left: 4px solid #f44336; border-radius: 10px; box-shadow: 0 2px 8px rgba(244, 67, 54, 0.2);">
          <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 24px; margin-right: 10px;">❌</span>
            <strong style="font-size: 16px; color: #d32f2f;">失败原因</strong>
          </div>
          <div style="padding: 12px; background: white; border-radius: 6px; color: #c62828; font-size: 14px; line-height: 1.6; white-space: pre-wrap; font-family: monospace; word-break: break-word;">${errorMessage}</div>
        </div>
      `;
    }
    
    content.innerHTML = `
      ${taskNameSection}
      <div style="margin: 20px 0;">
        <strong>任务ID:</strong> <span style="font-family: monospace; font-size: 13px;">${data.task_id}</span>
      </div>
      <div style="margin: 20px 0;">
        <strong>状态:</strong> <span class="task-status status-${data.status}">${data.status}</span>
      </div>
      <div style="margin: 20px 0;">
        <strong>创建时间:</strong> ${formatDateTime(data.created_at)}
      </div>
      ${data.completed_at ? `<div style="margin: 20px 0;"><strong>完成时间:</strong> ${formatDateTime(data.completed_at)}</div>` : ''}
      ${errorSection}
      ${imagesHtml ? `<div style="margin: 20px 0;"><strong>生成的图片:</strong>${imagesHtml}</div>` : ''}
      ${videosHtml ? `<div style="margin: 20px 0;"><strong>生成的视频:</strong>${videosHtml}</div>` : ''}
    `;
    
  } catch (error) {
    console.error('加载任务详情失败:', error);
    content.innerHTML = `
      <div style="text-align: center; padding: 50px; color: #d32f2f;">
        <div style="font-size: 40px; margin-bottom: 20px;">❌</div>
        <div style="font-size: 16px;">加载失败: ${error.message}</div>
      </div>
    `;
  }
}

// 关闭任务详情
function closeTaskDetail() {
  document.getElementById('taskDetailModal').style.display = 'none';
  document.body.style.overflow = 'auto';
}

// 下载任务视频
function downloadTasks() {
  const tasks = Array.from(document.querySelectorAll('.task-item.completed'));
  if (tasks.length === 0) {
    showModal('提示', '没有已完成的任务可供下载', 'info');
    return;
  }
  showModal('提示', `找到 ${tasks.length} 个已完成的任务\n功能开发中...`, 'info');
}

// 删除已完成任务
async function deleteCompleted() {
  showConfirm(
    '确认删除', 
    '确定要删除所有已完成的任务吗？\n此操作不可恢复。',
    async () => {
      try {
        const response = await fetch('/api/tasks');
        const result = await response.json();
        
        let tasks = [];
        // 检查多种成功状态：code === 0 或 code === 200 或 success === true
        if ((result.code === 0 || result.code === 200 || result.success === true) && result.data) {
          // 新格式：{code: 200, data: {total: 6, tasks: [...]}}
          if (result.data.tasks && Array.isArray(result.data.tasks)) {
            tasks = result.data.tasks;
          }
          // 旧格式：{code: 0, data: [...]}
          else if (Array.isArray(result.data)) {
            tasks = result.data;
          }
        } else if (Array.isArray(result)) {
          tasks = result;
        }
        
        const completedTasks = tasks.filter(t => t.status === 'completed');
        
        if (completedTasks.length === 0) {
          showModal('提示', '没有已完成的任务可供删除', 'info');
          return;
        }
        
        // 这里应该调用删除API，目前先提示
        showModal('提示', `找到 ${completedTasks.length} 个已完成的任务\n删除API开发中...`, 'info');
        
      } catch (error) {
        console.error('删除任务失败:', error);
        showModal('删除失败', error.message, 'error');
      }
    }
  );
}
