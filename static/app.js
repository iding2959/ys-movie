/**
 * ComfyUI API 调试工具 - 主要JavaScript文件
 */

// 全局变量
let ws = null;
let currentWorkflow = null;
let serverInfo = {
  address: '',
  connected: false
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
  initWebSocket();
  checkServerStatus();
  loadWorkflows();
  loadTasks();
  setupFileUpload();
  setupDragAndDrop();
  
  // 定期刷新（静默更新，不显示加载状态）
  setInterval(checkServerStatus, 5000);
  setInterval(() => loadTasks(200, false), 3000); // false = 不显示加载状态
  setInterval(updateQueueInfo, 2000);
});

/**
 * 格式化时间显示
 * @param {string|null} dateStr - ISO格式的时间字符串
 * @returns {string} 格式化后的时间字符串
 */
function formatDateTime(dateStr) {
  if (!dateStr) {
    return '未知';
  }
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return '无效时间';
    }
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (e) {
    return '无效时间';
  }
}

// 显示所有状态示例
function showStatusExamples() {
  const modal = document.getElementById('resultModal');
  const content = document.getElementById('modalContent');
  
  const exampleTasks = [
    {
      task_id: 'example-running-001',
      status: 'running',
      created_at: new Date().toISOString(),
      source: 'queue',
      workflow_type: '文生图'
    },
    {
      task_id: 'example-pending-001',
      status: 'pending',
      created_at: new Date(Date.now() - 60000).toISOString(),
      source: 'queue',
      workflow_type: '图生图'
    },
    {
      task_id: 'example-completed-001',
      status: 'completed',
      created_at: new Date(Date.now() - 300000).toISOString(),
      completed_at: new Date(Date.now() - 120000).toISOString(),
      source: 'history',
      workflow_type: '文生图',
      result: {
        outputs: {
          images: [
            {
              filename: 'example_image.png',
              subfolder: '',
              type: 'output',
              node_id: '9'
            }
          ]
        }
      }
    },
    {
      task_id: 'example-failed-001',
      status: 'failed',
      created_at: new Date(Date.now() - 600000).toISOString(),
      failed_at: new Date(Date.now() - 500000).toISOString(),
      source: 'local',
      workflow_type: 'API格式',
      error: '模型文件未找到：checkpoints/sd_model.safetensors'
    },
    {
      task_id: 'example-submitted-001',
      status: 'submitted',
      created_at: new Date(Date.now() - 10000).toISOString(),
      source: 'local',
      workflow_type: 'API格式'
    }
  ];
  
  let html = '<h3>📊 所有任务状态示例</h3>';
  html += '<p style="color: #666; font-size: 14px; margin-bottom: 20px;">以下是系统支持的所有任务状态及其显示效果：</p>';
  
  exampleTasks.forEach(task => {
    html += createTaskElement(task);
  });
  
  html += `
    <div style="margin-top: 30px; padding: 20px; background: #f5f5f5; border-radius: 10px; line-height: 1.8;">
      <h4 style="margin-top: 0;">💡 状态说明：</h4>
      <ul style="margin: 15px 0; padding-left: 20px;">
        <li><strong>⏳ 运行中 (running)</strong> - 任务正在ComfyUI中执行</li>
        <li><strong>⏸️ 排队中 (pending)</strong> - 任务在队列中等待执行（快速连续提交多个任务时会出现）</li>
        <li><strong>📤 已提交 (submitted)</strong> - 任务刚提交，等待ComfyUI确认</li>
        <li><strong>✅ 已完成 (completed)</strong> - 任务成功完成，可查看结果</li>
        <li><strong>❌ 失败 (failed)</strong> - 任务执行失败（如模型缺失、参数错误等）</li>
      </ul>
      <p style="color: #666; font-size: 13px; margin-top: 15px;">
        <strong>提示：</strong>如果你没有看到"排队中"状态，可以尝试快速连续提交2-3个任务，就能看到任务排队的效果。
      </p>
    </div>
  `;
  
  content.innerHTML = html;
  modal.classList.add('active');
}

// 运行诊断
async function runDiagnosis() {
  const modal = document.getElementById('resultModal');
  const content = document.getElementById('modalContent');
  
  content.innerHTML = `
    <div style="padding: 20px;">
      <h3>🔧 系统诊断进行中...</h3>
      <div class="json-viewer">正在检查各项连接...</div>
    </div>
  `;
  modal.classList.add('active');
  
  try {
    const response = await fetch('/api/diagnose');
    const result = await response.json();
    
    // 处理统一响应格式
    const data = result.data || result;
    
    // 构建诊断报告
    let html = '<h3>🔧 系统诊断报告</h3>';
    html += `<p style="color: #666; font-size: 14px; margin-bottom: 20px;">生成时间: ${formatDateTime(data.timestamp)}</p>`;
    html += `<p><strong>ComfyUI服务器:</strong> ${data.comfyui_server}</p>`;
    
    html += '<h4 style="margin-top: 20px; margin-bottom: 10px;">检查结果:</h4>';
    
    for (const [checkName, checkResult] of Object.entries(data.checks)) {
      const statusIcon = checkResult.status === 'ok' ? '✅' : '❌';
      const statusColor = checkResult.status === 'ok' ? '#4caf50' : '#f44336';
      
      html += `<div style="margin-bottom: 15px; padding: 10px; background: #f5f5f5; border-left: 4px solid ${statusColor}; border-radius: 5px;">`;
      html += `<strong>${statusIcon} ${checkName}</strong>`;
      
      if (checkResult.status === 'ok') {
        if (checkResult.count) {
          html += `<p style="color: #666; margin: 5px 0; font-size: 14px;">节点数: ${checkResult.count}</p>`;
        } else if (checkResult.data) {
          html += `<details style="margin: 5px 0; font-size: 14px; color: #666;">
            <summary>查看详情</summary>
            <div class="json-viewer" style="margin-top: 10px; font-size: 12px;">${JSON.stringify(checkResult.data, null, 2).substring(0, 500)}...</div>
          </details>`;
        }
      } else {
        html += `<p style="color: #f44336; margin: 5px 0; font-size: 14px;"><strong>错误:</strong> ${checkResult.error}</p>`;
      }
      
      html += '</div>';
    }
    
    // 添加建议
    html += '<h4 style="margin-top: 20px; margin-bottom: 10px;">可能的解决方案:</h4>';
    html += '<ul style="font-size: 14px; line-height: 1.8; color: #666;">';
    html += '<li>确保ComfyUI服务器正在运行 (http://' + data.comfyui_server + ')</li>';
    html += '<li>检查网络连接和防火墙设置</li>';
    html += '<li>确认ComfyUI服务器地址正确</li>';
    html += '<li>查看浏览器控制台(F12)获取更多错误信息</li>';
    html += '</ul>';
    
    content.innerHTML = html;
  } catch (error) {
    content.innerHTML = `
      <div style="padding: 20px;">
        <h3>❌ 诊断失败</h3>
        <p style="color: #f44336; margin: 20px 0;">无法获取诊断信息: ${error.message}</p>
        <p style="color: #666; font-size: 14px;">请检查:</p>
        <ul style="font-size: 14px; color: #666; line-height: 1.8;">
          <li>API服务是否正常运行</li>
          <li>浏览器网络连接</li>
          <li>浏览器控制台是否有错误信息</li>
        </ul>
      </div>
    `;
  }
}

// WebSocket连接
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  ws = new WebSocket(wsUrl);
  
  ws.onopen = function() {
    console.log('WebSocket连接成功');
    document.getElementById('wsStatus').textContent = '已连接';
    document.getElementById('wsStatus').style.color = '#4caf50';
  };
  
  ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    handleWebSocketMessage(data);
  };
  
  ws.onerror = function(error) {
    console.error('WebSocket错误:', error);
    document.getElementById('wsStatus').textContent = '连接错误';
    document.getElementById('wsStatus').style.color = '#f44336';
  };
  
  ws.onclose = function() {
    console.log('WebSocket连接断开');
    document.getElementById('wsStatus').textContent = '未连接';
    document.getElementById('wsStatus').style.color = '#999';
    // 5秒后重连
    setTimeout(initWebSocket, 5000);
  };
}

// 处理WebSocket消息
function handleWebSocketMessage(data) {
  if (data.type === 'task_update') {
    updateTaskStatus(data.task_id, data.status, data.result);
    
    // 显示通知
    showNotification(`任务 ${data.task_id.slice(0, 8)} 状态: ${data.status}`);
  }
}

// 检查服务器状态
async function checkServerStatus() {
  try {
    const response = await fetch('/api/health');
    const result = await response.json();
    
    // 处理统一响应格式
    const data = result.data || result;
    
    serverInfo.address = data.comfyui_server;
    serverInfo.connected = data.comfyui_status === 'connected';
    
    document.getElementById('serverAddress').textContent = serverInfo.address;
    document.getElementById('connectionStatus').textContent = serverInfo.connected ? '已连接' : '未连接';
    
    const indicator = document.getElementById('statusIndicator');
    indicator.className = 'status-indicator ' + (serverInfo.connected ? 'status-connected' : 'status-disconnected');
  } catch (error) {
    console.error('检查服务器状态失败:', error);
    serverInfo.connected = false;
    document.getElementById('connectionStatus').textContent = '连接失败';
    document.getElementById('statusIndicator').className = 'status-indicator status-disconnected';
  }
}

// 更新队列信息
async function updateQueueInfo() {
  try {
    const response = await fetch('/api/queue');
    const result = await response.json();
    
    // 处理统一响应格式
    const data = result.data || result;
    
    document.getElementById('queueRunning').textContent = data.queue_running?.length || 0;
    document.getElementById('queuePending').textContent = data.queue_pending?.length || 0;
  } catch (error) {
    console.error('获取队列信息失败:', error);
  }
}

// 加载工作流列表
async function loadWorkflows() {
  try {
    const response = await fetch('/api/workflows');
    const result = await response.json();
    
    // 处理统一响应格式
    const data = result.data || result;
    const workflows = data.workflows || [];
    
    const listEl = document.getElementById('workflowList');
    if (workflows.length === 0) {
      listEl.innerHTML = '<p style="color: #999; text-align: center;">暂无工作流</p>';
    } else {
      listEl.innerHTML = workflows.map(wf => `
        <div class="workflow-card" onclick="selectWorkflow('${wf.filename}')">
          <div class="workflow-name">${wf.filename}</div>
          <div class="workflow-info">节点数: ${wf.nodes} | 修改时间: ${formatDateTime(wf.modified)}</div>
        </div>
      `).join('');
    }
  } catch (error) {
    console.error('加载工作流失败:', error);
  }
}

// 选择工作流
async function selectWorkflow(filename) {
  try {
    const response = await fetch(`/api/workflow/${filename}`);
    const result = await response.json();
    
    // 处理统一响应格式
    const data = result.data || result;
    currentWorkflow = data.workflow;
    displayWorkflow(currentWorkflow);
    
    // 更新选中状态
    document.querySelectorAll('.workflow-card').forEach(card => {
      card.classList.remove('selected');
      if (card.querySelector('.workflow-name').textContent === filename) {
        card.classList.add('selected');
      }
    });
  } catch (error) {
    console.error('加载工作流失败:', error);
    showNotification('加载工作流失败', 'error');
  }
}

// 设置文件上传
function setupFileUpload() {
  const fileInput = document.getElementById('fileInput');
  fileInput.addEventListener('change', handleFileSelect);
}

// 设置拖拽上传
function setupDragAndDrop() {
  const uploadArea = document.getElementById('uploadArea');
  
  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
  });
  
  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
  });
  
  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });
}

// 处理文件选择
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    handleFile(file);
  }
}

// 处理文件
async function handleFile(file) {
  if (!file.name.endsWith('.json')) {
    showNotification('请选择JSON格式的工作流文件', 'error');
    return;
  }
  
  try {
    // 上传文件
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/workflow/upload', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error('上传失败');
    }
    
    const result = await response.json();
    // 处理统一响应格式
    const data = result.data || result;
    currentWorkflow = data.workflow;
    
    displayWorkflow(currentWorkflow);
    loadWorkflows(); // 刷新工作流列表
    
    showNotification('工作流上传成功', 'success');
  } catch (error) {
    console.error('处理文件失败:', error);
    showNotification('处理文件失败: ' + error.message, 'error');
  }
}

// 显示工作流
function displayWorkflow(workflow) {
  document.getElementById('workflowEditor').style.display = 'block';
  document.getElementById('workflowPreview').textContent = JSON.stringify(workflow, null, 2);
  
  // 提取可编辑的参数
  extractParameters(workflow);
}

// 提取参数 (由于代码较长,保持原有逻辑)
function extractParameters(workflow) {
  const params = [];
  const importantParams = [];
  
  for (const [nodeId, node] of Object.entries(workflow)) {
    const nodeType = node.class_type || node.type;
    
    if (node.class_type && node.inputs) {
      for (const [inputName, inputValue] of Object.entries(node.inputs)) {
        if (Array.isArray(inputValue)) continue;
        
        if (nodeType === 'LoadImage' && inputName === 'image') {
          // LoadImage节点的图片输入
          importantParams.push({
            nodeId,
            inputName,
            value: inputValue,
            type: 'image',
            label: `节点${nodeId} - 图片上传`,
            isApiFormat: true
          });
        } else if (nodeType === 'CLIPTextEncode' && inputName === 'text') {
          importantParams.push({
            nodeId,
            inputName,
            value: inputValue,
            type: 'textarea',
            label: `节点${nodeId} - 文本提示词`,
            isApiFormat: true
          });
        } else if (nodeType === 'KSampler') {
          const paramConfig = {
            'seed': { type: 'number', label: '种子 (输入-1使用随机值)' },
            'steps': { type: 'number', label: '步数' },
            'cfg': { type: 'number', label: 'CFG' },
            'denoise': { type: 'number', label: '降噪强度' },
            'sampler_name': { type: 'text', label: '采样器' },
            'scheduler': { type: 'text', label: '调度器' }
          };
          if (paramConfig[inputName]) {
            importantParams.push({
              nodeId,
              inputName,
              value: inputValue,
              type: paramConfig[inputName].type,
              label: `节点${nodeId} - ${paramConfig[inputName].label}`,
              isApiFormat: true
            });
          }
        } else if (nodeType === 'EmptySD3LatentImage') {
          const paramConfig = {
            'width': { type: 'number', label: '宽度' },
            'height': { type: 'number', label: '高度' },
            'batch_size': { type: 'number', label: '批量大小' }
          };
          if (paramConfig[inputName]) {
            importantParams.push({
              nodeId,
              inputName,
              value: inputValue,
              type: paramConfig[inputName].type,
              label: `节点${nodeId} - ${paramConfig[inputName].label}`,
              isApiFormat: true
            });
          }
        } else {
          if (typeof inputValue === 'string' || typeof inputValue === 'number') {
            params.push({
              nodeId,
              inputName,
              value: inputValue,
              type: typeof inputValue === 'number' ? 'number' : 'text',
              label: `节点${nodeId} - ${inputName}`,
              isApiFormat: true
            });
          }
        }
      }
    } else if (node.widgets_values && Array.isArray(node.widgets_values)) {
      if (node.type === 'CLIPTextEncode') {
        if (node.widgets_values[0]) {
          importantParams.push({
            nodeId,
            inputName: 'text',
            value: node.widgets_values[0],
            type: 'textarea',
            label: node.title || `节点${nodeId} - 文本提示词`,
            widgetIndex: 0
          });
        }
      } else if (node.type === 'KSampler') {
        const samplerParams = [
          { name: 'seed', index: 0, type: 'number', label: '种子' },
          { name: 'steps', index: 2, type: 'number', label: '步数' },
          { name: 'cfg', index: 3, type: 'number', label: 'CFG' },
          { name: 'denoise', index: 6, type: 'number', label: '降噪强度' }
        ];
        samplerParams.forEach(param => {
          if (node.widgets_values[param.index] !== undefined) {
            importantParams.push({
              nodeId,
              inputName: param.name,
              value: node.widgets_values[param.index],
              type: param.type,
              label: `节点${nodeId} - ${param.label}`,
              widgetIndex: param.index
            });
          }
        });
      } else if (node.type === 'EmptySD3LatentImage') {
        const sizeParams = [
          { name: 'width', index: 0, type: 'number', label: '宽度' },
          { name: 'height', index: 1, type: 'number', label: '高度' },
          { name: 'batch_size', index: 2, type: 'number', label: '批量大小' }
        ];
        sizeParams.forEach(param => {
          if (node.widgets_values[param.index] !== undefined) {
            importantParams.push({
              nodeId,
              inputName: param.name,
              value: node.widgets_values[param.index],
              type: param.type,
              label: `节点${nodeId} - ${param.label}`,
              widgetIndex: param.index
            });
          }
        });
      } else if (node.type === 'ModelSamplingAuraFlow') {
        if (node.widgets_values[0] !== undefined) {
          params.push({
            nodeId,
            inputName: 'shift',
            value: node.widgets_values[0],
            type: 'number',
            label: `节点${nodeId} - Shift参数`,
            widgetIndex: 0
          });
        }
      }
      
      node.widgets_values.forEach((value, index) => {
        if (value !== undefined && value !== null && 
            !importantParams.some(p => p.nodeId === nodeId && p.widgetIndex === index) &&
            !params.some(p => p.nodeId === nodeId && p.widgetIndex === index)) {
          if (typeof value === 'string' || typeof value === 'number') {
            params.push({
              nodeId,
              inputName: `param_${index}`,
              value: value,
              type: typeof value === 'number' ? 'number' : 'text',
              label: `节点${nodeId} - 参数${index}`,
              widgetIndex: index
            });
          }
        }
      });
    }
  }
  
  const allParams = [...importantParams, ...params];
  
  document.getElementById('paramEditor').style.display = 'block';
  const paramList = document.getElementById('paramList');
  
  if (allParams.length > 0) {
    // 创建参数渲染函数
    const renderParam = (param) => {
      const paramId = param.isApiFormat 
        ? `param_${param.nodeId}_${param.inputName}`
        : `param_${param.nodeId}_${param.widgetIndex}`;
      
      if (param.type === 'image') {
        return `
          <div class="param-item" style="flex-direction: column; align-items: flex-start;">
            <label for="${paramId}">${param.label}</label>
            <div style="width: 100%; margin-top: 5px;">
              <input 
                type="file" 
                id="${paramId}" 
                accept="image/*"
                data-node="${param.nodeId}"
                data-input="${param.inputName || ''}"
                data-index="${param.widgetIndex || ''}"
                data-api-format="${param.isApiFormat || false}"
                style="display: block; width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; cursor: pointer;"
              >
              <div id="${paramId}_preview" style="margin-top: 10px; text-align: center;">
                ${param.value ? `<p style="color: #666; font-size: 14px;">当前图片: ${param.value}</p>` : ''}
              </div>
            </div>
          </div>
        `;
      } else if (param.type === 'textarea') {
        return `
          <div class="param-item" style="flex-direction: column; align-items: flex-start;">
            <label for="${paramId}">${param.label}</label>
            <textarea 
              id="${paramId}" 
              data-node="${param.nodeId}"
              data-input="${param.inputName || ''}"
              data-index="${param.widgetIndex || ''}"
              data-api-format="${param.isApiFormat || false}"
              style="width: 100%; min-height: 100px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; margin-top: 5px; resize: vertical;"
            >${param.value}</textarea>
          </div>
        `;
      } else {
        return `
          <div class="param-item">
            <label for="${paramId}">${param.label}</label>
            <input 
              type="${param.type}" 
              id="${paramId}" 
              value="${param.value}"
              data-node="${param.nodeId}"
              data-input="${param.inputName || ''}"
              data-index="${param.widgetIndex || ''}"
              data-api-format="${param.isApiFormat || false}"
              ${param.type === 'number' ? 'step="any"' : ''}
            >
          </div>
        `;
      }
    };
    
    // 初始只显示前15个参数
    const initialLimit = 15;
    const hasMore = allParams.length > initialLimit;
    
    paramList.innerHTML = allParams.slice(0, initialLimit).map(renderParam).join('');
    
    if (hasMore) {
      // 创建"显示更多"区域
      const moreSection = document.createElement('div');
      moreSection.id = 'moreParamsSection';
      moreSection.style.cssText = 'margin-top: 15px;';
      
      // 隐藏的参数区域
      const hiddenParamsDiv = document.createElement('div');
      hiddenParamsDiv.id = 'hiddenParams';
      hiddenParamsDiv.style.display = 'none';
      hiddenParamsDiv.innerHTML = allParams.slice(initialLimit).map(renderParam).join('');
      
      // "显示更多"按钮
      const toggleBtn = document.createElement('button');
      toggleBtn.id = 'toggleParamsBtn';
      toggleBtn.textContent = `📋 显示更多参数 (${allParams.length - initialLimit} 个)`;
      toggleBtn.style.cssText = 'width: 100%; padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; margin-bottom: 10px;';
      
      toggleBtn.onclick = () => {
        const hiddenDiv = document.getElementById('hiddenParams');
        const btn = document.getElementById('toggleParamsBtn');
        if (hiddenDiv.style.display === 'none') {
          hiddenDiv.style.display = 'block';
          btn.textContent = '📋 收起参数';
          btn.style.background = 'linear-gradient(135deg, #ff9800 0%, #f57c00 100%)';
        } else {
          hiddenDiv.style.display = 'none';
          btn.textContent = `📋 显示更多参数 (${allParams.length - initialLimit} 个)`;
          btn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        }
      };
      
      moreSection.appendChild(toggleBtn);
      moreSection.appendChild(hiddenParamsDiv);
      paramList.appendChild(moreSection);
      
      // 添加统计信息
      const statsDiv = document.createElement('div');
      statsDiv.style.cssText = 'margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 14px; color: #666;';
      statsDiv.innerHTML = `
        <strong>参数统计：</strong>
        总计 ${allParams.length} 个参数 
        (重要参数: ${importantParams.length} 个, 其他参数: ${params.length} 个)
      `;
      paramList.appendChild(statsDiv);
    }
  } else {
    paramList.innerHTML = '<p style="color: #666; font-size: 14px;">此工作流使用默认参数，你可以直接提交执行。</p>';
  }
  
  const paramEditor = document.getElementById('paramEditor');
  const oldButtonGroups = paramEditor.querySelectorAll('.workflow-button-group');
  oldButtonGroups.forEach(group => group.remove());
  
  const buttonGroup = document.createElement('div');
  buttonGroup.className = 'workflow-button-group';
  buttonGroup.style.cssText = 'display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;';
  buttonGroup.innerHTML = `
    <button onclick="submitWorkflow()" id="submitBtn" style="flex: 1; min-width: 150px;">
      🚀 提交执行
    </button>
    <button onclick="resetParams()" style="flex: 1; min-width: 150px; background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);">
      🔄 重置参数
    </button>
    <button onclick="saveWorkflow()" style="flex: 1; min-width: 150px; background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);">
      💾 保存工作流
    </button>
  `;
  
  paramEditor.appendChild(buttonGroup);
  
  // 为图片输入添加预览功能
  document.querySelectorAll('input[type="file"][accept="image/*"]').forEach(input => {
    input.addEventListener('change', function(e) {
      const file = e.target.files[0];
      if (file) {
        const previewId = `${this.id}_preview`;
        const previewDiv = document.getElementById(previewId);
        
        if (previewDiv) {
          const reader = new FileReader();
          reader.onload = function(e) {
            previewDiv.innerHTML = `
              <p style="color: #666; font-size: 14px; margin-bottom: 5px;">已选择: ${file.name}</p>
              <img src="${e.target.result}" 
                   style="max-width: 100%; max-height: 200px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" 
                   alt="图片预览">
            `;
          };
          reader.readAsDataURL(file);
        }
      }
    });
  });
  
  return allParams;
}

// 提交工作流
async function submitWorkflow() {
  if (!currentWorkflow) {
    showNotification('请先选择或上传工作流', 'error');
    return;
  }
  
  const workflow = JSON.parse(JSON.stringify(currentWorkflow));
  
  // 首先处理图片上传
  const imageInputs = document.querySelectorAll('#paramList input[type="file"]');
  for (const fileInput of imageInputs) {
    if (fileInput.files && fileInput.files.length > 0) {
      const file = fileInput.files[0];
      const nodeId = fileInput.dataset.node;
      const inputName = fileInput.dataset.input;
      const isApiFormat = fileInput.dataset.apiFormat === 'true';
      
      try {
        showNotification(`正在上传图片: ${file.name}...`, 'info');
        
        // 上传图片到服务器
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch('/api/upload/image', {
          method: 'POST',
          body: formData
        });
        
        if (!uploadResponse.ok) {
          throw new Error('图片上传失败');
        }
        
        const uploadResult = await uploadResponse.json();
        const uploadedFilename = uploadResult.data.filename;
        
        // 更新workflow中的图片文件名
        if (isApiFormat && workflow[nodeId] && workflow[nodeId].inputs && inputName) {
          workflow[nodeId].inputs[inputName] = uploadedFilename;
        }
        
        showNotification(`图片上传成功: ${uploadedFilename}`, 'success');
      } catch (error) {
        showNotification(`图片上传失败: ${error.message}`, 'error');
        return; // 如果图片上传失败，不继续提交workflow
      }
    }
  }
  
  // 处理其他参数
  document.querySelectorAll('#paramList input:not([type="file"]), #paramList textarea').forEach(element => {
    const nodeId = element.dataset.node;
    const isApiFormat = element.dataset.apiFormat === 'true';
    let value = element.value;
    
    if (element.type === 'number') {
      value = parseFloat(value);
    }
    
    if (isApiFormat) {
      const inputName = element.dataset.input;
      if (workflow[nodeId] && workflow[nodeId].inputs && inputName) {
        if (inputName === 'seed' && (value < 0 || element.value === 'random')) {
          value = Math.floor(Math.random() * 18446744073709551615);
          console.log('🎲 生成随机种子:', value);
        }
        workflow[nodeId].inputs[inputName] = value;
      }
    } else {
      const widgetIndex = parseInt(element.dataset.index);
      if (workflow[nodeId] && workflow[nodeId].widgets_values && widgetIndex !== undefined) {
        workflow[nodeId].widgets_values[widgetIndex] = value;
      }
    }
  });
  
  const submitBtn = document.getElementById('submitBtn');
  submitBtn.disabled = true;
  submitBtn.innerHTML = '提交中 <span class="loading-spinner"></span>';
  
  try {
    const response = await fetch('/api/workflow/submit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        workflow,
        params: {},
        timeout: 600
      })
    });
    
    if (!response.ok) {
      const errorResult = await response.json();
      const errorData = errorResult.data || errorResult;
      const errorMsg = errorResult.message || errorData.detail || errorData.message || '提交失败';
      throw new Error(errorMsg);
    }
    
    const result = await response.json();
    // 处理统一响应格式
    const data = result.data || result;
    showNotification(`任务已提交: ${data.task_id.slice(0, 8)}...`, 'success');
    
    switchTab('tasks');
    loadTasks(200, false); // 静默刷新
  } catch (error) {
    console.error('提交工作流失败:', error);
    showNotification('提交失败: ' + error.message, 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '🚀 提交执行';
  }
}

// 重置参数
function resetParams() {
  if (!currentWorkflow) {
    showNotification('没有加载的工作流', 'error');
    return;
  }
  
  extractParameters(currentWorkflow);
  showNotification('参数已重置为默认值', 'success');
}

// 保存工作流
async function saveWorkflow() {
  if (!currentWorkflow) {
    showNotification('没有加载的工作流', 'error');
    return;
  }
  
  const workflow = JSON.parse(JSON.stringify(currentWorkflow));
  document.querySelectorAll('#paramList input, #paramList textarea').forEach(element => {
    const nodeId = element.dataset.node;
    const isApiFormat = element.dataset.apiFormat === 'true';
    let value = element.value;
    
    if (element.type === 'number') {
      value = parseFloat(value);
    }
    
    if (isApiFormat) {
      const inputName = element.dataset.input;
      if (workflow[nodeId] && workflow[nodeId].inputs && inputName) {
        workflow[nodeId].inputs[inputName] = value;
      }
    } else {
      const widgetIndex = parseInt(element.dataset.index);
      if (workflow[nodeId] && workflow[nodeId].widgets_values && widgetIndex !== undefined) {
        workflow[nodeId].widgets_values[widgetIndex] = value;
      }
    }
  });
  
  const dataStr = JSON.stringify(workflow, null, 2);
  const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
  
  const exportFileDefaultName = `workflow_${new Date().getTime()}.json`;
  
  const linkElement = document.createElement('a');
  linkElement.setAttribute('href', dataUri);
  linkElement.setAttribute('download', exportFileDefaultName);
  linkElement.click();
  
  showNotification('工作流已保存', 'success');
}

// 全局分页状态
let currentPage = 1;
let pageSize = 25;
let allTasks = [];
let isFirstLoad = true; // 标记是否首次加载

// 加载任务列表
async function loadTasks(limit = 200, showLoading = true) {
  const taskList = document.getElementById('taskList');
  
  // 只在首次加载或手动刷新时显示加载状态
  if (showLoading && isFirstLoad) {
    taskList.innerHTML = `
      <div style="text-align: center; padding: 50px; color: #666;">
        <div style="font-size: 40px; margin-bottom: 20px;">⏳</div>
        <div style="font-size: 16px;">正在加载任务列表...</div>
      </div>
    `;
  }
  
  try {
    const response = await fetch(`/api/tasks?limit=${limit}`);
    const result = await response.json();
    
    console.log('获取到的任务数据:', result); // 调试信息
    
    // 处理统一响应格式：{ code, success, message, data }
    const data = result.data || result;
    const tasks = data.tasks || [];
    
    // 快速检测数据是否变化（比较数量和前几个任务的状态）
    const tasksChanged = 
      tasks.length !== allTasks.length ||
      (tasks.length > 0 && allTasks.length > 0 && (
        tasks[0].status !== allTasks[0].status ||
        tasks[0].task_id !== allTasks[0].task_id
      ));
    
    if (!isFirstLoad && !tasksChanged) {
      return; // 数据没变，直接返回
    }
    
    // 优化排序逻辑：
    // 1. running 和 pending 按提交时间排序（最新的在前）
    // 2. completed 按完成时间排序（最新完成的在前）
    // 3. 其他状态按创建时间排序
    allTasks = tasks.sort((a, b) => {
      // 状态分组
      const activeStates = ['running', 'pending'];
      const isAActive = activeStates.includes(a.status);
      const isBActive = activeStates.includes(b.status);
      
      // 活跃任务（运行中/排队中）优先显示
      if (isAActive && !isBActive) return -1;
      if (!isAActive && isBActive) return 1;
      
      // 都是活跃任务，按创建时间排序（最新的在前）
      if (isAActive && isBActive) {
        const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return timeB - timeA;
      }
      
      // 都不是活跃任务，按完成时间或创建时间排序
      const timeA = a.completed_at ? new Date(a.completed_at).getTime() : 
                   (a.created_at ? new Date(a.created_at).getTime() : 0);
      const timeB = b.completed_at ? new Date(b.completed_at).getTime() : 
                   (b.created_at ? new Date(b.created_at).getTime() : 0);
      return timeB - timeA;
    });
    
    // 重置到第一页并渲染（只在首次加载时重置页码）
    if (isFirstLoad) {
      currentPage = 1;
    }
    renderTasksPage();
    
    // 标记首次加载完成
    isFirstLoad = false;
    
  } catch (error) {
    console.error('加载任务失败:', error);
    taskList.innerHTML = `<p style="text-align: center; color: #f44336; margin-top: 50px;">加载任务失败: ${error.message}</p>`;
    isFirstLoad = false;
  }
}

// 渲染任务列表（分页）
function renderTasksPage() {
  const taskList = document.getElementById('taskList');
  
  if (allTasks.length === 0) {
    taskList.innerHTML = '<p style="text-align: center; color: #999; margin-top: 50px;">暂无任务</p>';
    return;
  }
  
  const totalPages = Math.ceil(allTasks.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, allTasks.length);
  const pageTasks = allTasks.slice(startIndex, endIndex);
  
  // 渲染任务列表
  taskList.innerHTML = pageTasks.map(task => createTaskElement(task)).join('');
  
  // 添加分页组件
  const paginationDiv = createPaginationComponent(totalPages);
  taskList.appendChild(paginationDiv);
}

// 创建分页组件
function createPaginationComponent(totalPages) {
  const paginationDiv = document.createElement('div');
  paginationDiv.style.cssText = 'margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 10px;';
  
  // 统计信息
  const startIndex = (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, allTasks.length);
  
  const statsDiv = document.createElement('div');
  statsDiv.style.cssText = 'text-align: center; color: #666; font-size: 14px; margin-bottom: 15px;';
  statsDiv.innerHTML = `
    显示 <strong>${startIndex}</strong> - <strong>${endIndex}</strong> 条，
    共 <strong>${allTasks.length}</strong> 条任务
  `;
  paginationDiv.appendChild(statsDiv);
  
  // 分页按钮容器
  const buttonsDiv = document.createElement('div');
  buttonsDiv.style.cssText = 'display: flex; justify-content: center; align-items: center; gap: 10px; flex-wrap: wrap;';
  
  // 上一页按钮
  const prevBtn = createPageButton('« 上一页', currentPage > 1, () => {
    if (currentPage > 1) {
      currentPage--;
      renderTasksPage();
      scrollToTop();
    }
  });
  buttonsDiv.appendChild(prevBtn);
  
  // 页码按钮
  const pageButtons = createPageNumbers(currentPage, totalPages);
  pageButtons.forEach(btn => buttonsDiv.appendChild(btn));
  
  // 下一页按钮
  const nextBtn = createPageButton('下一页 »', currentPage < totalPages, () => {
    if (currentPage < totalPages) {
      currentPage++;
      renderTasksPage();
      scrollToTop();
    }
  });
  buttonsDiv.appendChild(nextBtn);
  
  paginationDiv.appendChild(buttonsDiv);
  
  // 每页显示数量选择器
  const pageSizeDiv = document.createElement('div');
  pageSizeDiv.style.cssText = 'text-align: center; margin-top: 15px;';
  pageSizeDiv.innerHTML = `
    <label style="color: #666; font-size: 14px; margin-right: 10px;">每页显示：</label>
    <select id="pageSizeSelect" style="padding: 5px 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px;">
      <option value="10" ${pageSize === 10 ? 'selected' : ''}>10条</option>
      <option value="25" ${pageSize === 25 ? 'selected' : ''}>25条</option>
      <option value="50" ${pageSize === 50 ? 'selected' : ''}>50条</option>
      <option value="100" ${pageSize === 100 ? 'selected' : ''}>100条</option>
    </select>
  `;
  
  paginationDiv.appendChild(pageSizeDiv);
  
  // 添加选择器事件监听
  setTimeout(() => {
    const selector = document.getElementById('pageSizeSelect');
    if (selector) {
      selector.addEventListener('change', (e) => {
        pageSize = parseInt(e.target.value);
        currentPage = 1;
        renderTasksPage();
        scrollToTop();
      });
    }
  }, 0);
  
  return paginationDiv;
}

// 创建分页按钮
function createPageButton(text, enabled, onClick) {
  const btn = document.createElement('button');
  btn.textContent = text;
  btn.disabled = !enabled;
  btn.style.cssText = `
    padding: 8px 16px;
    border: none;
    border-radius: 5px;
    font-size: 14px;
    cursor: ${enabled ? 'pointer' : 'not-allowed'};
    background: ${enabled ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#e0e0e0'};
    color: ${enabled ? 'white' : '#999'};
    transition: all 0.3s ease;
  `;
  
  if (enabled) {
    btn.onmouseover = () => btn.style.transform = 'scale(1.05)';
    btn.onmouseout = () => btn.style.transform = 'scale(1)';
    btn.onclick = onClick;
  }
  
  return btn;
}

// 创建页码按钮
function createPageNumbers(current, total) {
  const buttons = [];
  const maxVisible = 7; // 最多显示7个页码按钮
  
  let startPage = Math.max(1, current - Math.floor(maxVisible / 2));
  let endPage = Math.min(total, startPage + maxVisible - 1);
  
  // 调整起始页
  if (endPage - startPage < maxVisible - 1) {
    startPage = Math.max(1, endPage - maxVisible + 1);
  }
  
  // 第一页
  if (startPage > 1) {
    buttons.push(createNumberButton(1, current));
    if (startPage > 2) {
      const ellipsis = document.createElement('span');
      ellipsis.textContent = '...';
      ellipsis.style.cssText = 'padding: 8px; color: #999;';
      buttons.push(ellipsis);
    }
  }
  
  // 中间页码
  for (let i = startPage; i <= endPage; i++) {
    buttons.push(createNumberButton(i, current));
  }
  
  // 最后一页
  if (endPage < total) {
    if (endPage < total - 1) {
      const ellipsis = document.createElement('span');
      ellipsis.textContent = '...';
      ellipsis.style.cssText = 'padding: 8px; color: #999;';
      buttons.push(ellipsis);
    }
    buttons.push(createNumberButton(total, current));
  }
  
  return buttons;
}

// 创建数字页码按钮
function createNumberButton(pageNum, currentPageNum) {
  const btn = document.createElement('button');
  btn.textContent = pageNum;
  const isCurrent = pageNum === currentPageNum;
  
  btn.style.cssText = `
    padding: 8px 12px;
    border: ${isCurrent ? 'none' : '1px solid #ddd'};
    border-radius: 5px;
    font-size: 14px;
    cursor: ${isCurrent ? 'default' : 'pointer'};
    background: ${isCurrent ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'white'};
    color: ${isCurrent ? 'white' : '#333'};
    font-weight: ${isCurrent ? 'bold' : 'normal'};
    transition: all 0.3s ease;
    min-width: 40px;
  `;
  
  if (!isCurrent) {
    btn.onmouseover = () => {
      btn.style.background = '#f0f0f0';
      btn.style.transform = 'scale(1.05)';
    };
    btn.onmouseout = () => {
      btn.style.background = 'white';
      btn.style.transform = 'scale(1)';
    };
    btn.onclick = () => {
      currentPage = pageNum;
      renderTasksPage();
      scrollToTop();
    };
  }
  
  return btn;
}

// 滚动到顶部
function scrollToTop() {
  const tasksTab = document.getElementById('tasksTab');
  if (tasksTab) {
    tasksTab.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

/**
 * 判断文件是否为视频文件
 * @param {string} filename - 文件名
 * @returns {boolean} 是否为视频文件
 */
function isVideoFile(filename) {
  const videoExtensions = ['.mp4', '.webm', '.gif', '.avi', '.mov', '.mkv', '.m4v', '.flv'];
  const lowerFilename = filename.toLowerCase();
  return videoExtensions.some(ext => lowerFilename.endsWith(ext));
}

/**
 * 测试视频URL是否可访问
 * @param {string} videoUrl - 视频URL
 * @returns {Promise<Object>} 测试结果
 */
async function testVideoUrl(videoUrl) {
  try {
    console.log('测试视频URL:', videoUrl);
    const response = await fetch(videoUrl, { method: 'HEAD' });
    console.log('视频URL响应:', {
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries())
    });
    return {
      success: response.ok,
      status: response.status,
      headers: Object.fromEntries(response.headers.entries())
    };
  } catch (error) {
    console.error('视频URL测试失败:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// 创建任务元素（修复版，处理null值）
function createTaskElement(task) {
  const statusClass = `status-${task.status}`;
  const taskClass = `task-item ${task.status}`;
  
  let resultPreview = '';
  if (task.result && task.result.outputs) {
    const images = task.result.outputs.images || [];
    if (images.length > 0) {
      resultPreview = `
        <div class="result-preview">
          ${images.slice(0, 4).map(img => {
            const filename = img.filename || '';
            const subfolder = img.subfolder || '';
            const type = img.type || 'output';
            
            // 判断是图片还是视频
            if (isVideoFile(filename)) {
              // 视频文件 - 使用缩略图占位，修复URL构建
              let videoUrl = `/api/video/${filename}?type=${type}`;
              if (subfolder && subfolder.trim() !== '') {
                videoUrl += `&subfolder=${subfolder}`;
              }
              
              return `
                <div class="result-image" onclick="viewVideo('${videoUrl}', '${filename}')" style="position: relative; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; cursor: pointer;">
                  <div style="color: white; text-align: center;">
                    <div style="font-size: 40px; margin-bottom: 5px;">🎬</div>
                    <div style="font-size: 12px;">点击播放</div>
                  </div>
                  <div style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.7); color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">
                    📹 视频
                  </div>
                </div>
              `;
            } else {
              // 图片文件 - 使用懒加载
              const imageUrl = `/api/image/${filename}?subfolder=${subfolder}&type=${type}`;
              return `
                <div class="result-image" onclick="viewImage('${imageUrl}')">
                  <img src="${imageUrl}" alt="Result" loading="lazy" style="background: #f0f0f0;">
                </div>
              `;
            }
          }).join('')}
          ${images.length > 4 ? `<p style="color: #999;">还有 ${images.length - 4} 个文件...</p>` : ''}
        </div>
      `;
    }
  }
  
  // 使用formatDateTime函数处理时间显示
  const createdTime = formatDateTime(task.created_at);
  const completedTime = task.completed_at ? `<br>完成时间: ${formatDateTime(task.completed_at)}` : '';
  
  // 为不同状态添加图标
  const statusIcons = {
    'running': '⏳',
    'pending': '⏸️',
    'submitted': '📤',
    'completed': '✅',
    'failed': '❌'
  };
  const statusIcon = statusIcons[task.status] || '📋';
  
  // 状态文本本地化
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
  
  return `
    <div class="${taskClass}">
      <div class="task-header">
        <span class="task-id">${task.task_id}</span>
        <span class="task-status ${statusClass}">${statusIcon} ${displayStatus}</span>
      </div>
      <div style="color: #666; font-size: 14px; margin: 10px 0;">
        创建时间: ${createdTime}${completedTime}
        ${task.workflow_type ? `<br>类型: ${task.workflow_type}` : ''}
        <br>来源: ${displaySource}
      </div>
      ${resultPreview}
      ${task.error ? `<div style="color: #f44336; margin-top: 10px;">错误: ${task.error}</div>` : ''}
      <button onclick="viewTaskDetail('${task.task_id}')" style="margin-top: 10px; padding: 8px 20px; font-size: 14px;">
        查看详情
      </button>
    </div>
  `;
}

// 更新任务状态
function updateTaskStatus(taskId, status, result) {
  loadTasks(200, false); // 静默刷新列表
}

// 查看任务详情
async function viewTaskDetail(taskId) {
  const modal = document.getElementById('resultModal');
  const content = document.getElementById('modalContent');
  
  // 立即显示模态框和加载状态
  content.innerHTML = `
    <div style="text-align: center; padding: 50px; color: #666;">
      <div style="font-size: 40px; margin-bottom: 20px;">⏳</div>
      <div style="font-size: 16px;">正在加载任务详情...</div>
    </div>
  `;
  modal.classList.add('active');
  
  try {
    const response = await fetch(`/api/task/${taskId}`);
    const result = await response.json();
    
    // 处理统一响应格式
    const data = result.data || result;
    
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
          
          if (isVideoFile(filename)) {
            // 视频文件 - 修复URL构建
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
            
            if (isVideoFile(filename)) {
              // 修复URL构建：只在subfolder非空时才添加参数
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
        
        if (output.gifs && output.gifs.length > 0) {
          videosHtml += `<div style="margin: 10px 0;"><strong>节点 ${nodeId} (视频):</strong></div>`;
          output.gifs.forEach(video => {
            // 修复URL构建：只在subfolder非空时才添加参数
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
      
      const finalVideos = [];
      const segmentVideos = [];
      
      if (outputs.other && Array.isArray(outputs.other)) {
        outputs.other.forEach(item => {
          if (item.type === 'gifs' && item.data && Array.isArray(item.data)) {
            item.data.forEach(video => {
              const videoItem = {
                node_id: item.node_id || 'unknown',
                ...video
              };
              // 修复：空字符串也视为没有 subfolder，统一归类为输出视频
              // 实际上所有视频都应该显示，不区分最终/分段
              segmentVideos.push(videoItem);
            });
          }
        });
      }
      
      if (finalVideos.length > 0) {
        videosHtml += `<div style="margin: 15px 0; padding: 10px; background: #e3f2fd; border-radius: 8px;">
          <strong style="color: #1976d2;">🎬 最终合成视频</strong>
        </div>`;
        finalVideos.forEach(video => {
          // 修复URL构建：只在subfolder非空时才添加参数
          let videoUrl = `/api/video/${video.filename}?type=${video.type || 'output'}`;
          if (video.subfolder && video.subfolder.trim() !== '') {
            videoUrl += `&subfolder=${video.subfolder}`;
          }
          
          videosHtml += `
            <div style="margin: 10px 0;">
              <strong>节点 ${video.node_id} (${video.subfolder || '输出'}):</strong>
            </div>
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
      
      if (segmentVideos.length > 0) {
        videosHtml += `
          <div style="margin: 15px 0;">
            <div style="padding: 10px; background: #f5f5f5; border-radius: 8px; font-weight: bold; margin-bottom: 10px;">
              📹 生成的视频 (${segmentVideos.length}个)
            </div>
        `;
        segmentVideos.forEach((video, index) => {
          // 修复URL构建：只在subfolder非空时才添加参数
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
          
          // 测试视频URL
          testVideoUrl(videoUrl).then(result => {
            console.log(`视频 ${index + 1} URL测试结果:`, result);
            if (!result.success) {
              console.error(`视频 ${index + 1} URL不可访问!`);
            }
          });
          
          const videoId = `video_${video.node_id}_${index}`;
          
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
              <strong>节点 ${video.node_id}:</strong>
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
                <button onclick="testVideoUrl('${videoUrl}').then(r => alert(JSON.stringify(r, null, 2)))" style="padding: 6px 12px; background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); color: white; border: none; border-radius: 5px; font-size: 12px; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                  🔍 测试URL
                </button>
              </div>
            </div>
          `;
        });
        videosHtml += `
          </div>
        `;
      }
    }
    
    content.innerHTML = `
      <div style="margin: 20px 0;">
        <strong>任务ID:</strong> ${data.task_id}
      </div>
      <div style="margin: 20px 0;">
        <strong>状态:</strong> <span class="task-status status-${data.status}">${data.status}</span>
      </div>
      <div style="margin: 20px 0;">
        <strong>创建时间:</strong> ${formatDateTime(data.created_at)}
      </div>
      ${data.completed_at ? `<div style="margin: 20px 0;"><strong>完成时间:</strong> ${formatDateTime(data.completed_at)}</div>` : ''}
      ${imagesHtml ? `<div style="margin: 20px 0;"><strong>生成的图片:</strong>${imagesHtml}</div>` : ''}
      ${videosHtml ? `<div style="margin: 20px 0;"><strong>生成的视频:</strong>${videosHtml}</div>` : ''}
      ${data.result ? `
        <div style="margin: 20px 0;">
          <strong>完整结果数据:</strong>
          <div class="json-viewer" style="max-height: 400px; overflow-y: auto;">${JSON.stringify(data.result, null, 2)}</div>
        </div>
      ` : ''}
    `;
    
  } catch (error) {
    console.error('获取任务详情失败:', error);
    content.innerHTML = `
      <div style="text-align: center; padding: 50px; color: #f44336;">
        <div style="font-size: 40px; margin-bottom: 20px;">❌</div>
        <div style="font-size: 16px;">获取任务详情失败</div>
        <div style="font-size: 14px; margin-top: 10px; color: #999;">${error.message}</div>
      </div>
    `;
    showNotification('获取任务详情失败: ' + error.message, 'error');
  }
}

// 查看图片
function viewImage(url) {
  const modal = document.getElementById('resultModal');
  const content = document.getElementById('modalContent');
  
  content.innerHTML = `
    <div style="text-align: center;">
      <img src="${url}" style="max-width: 100%; height: auto; border-radius: 10px;">
    </div>
  `;
  
  modal.classList.add('active');
}

// 查看视频
function viewVideo(url, filename) {
  const modal = document.getElementById('resultModal');
  const content = document.getElementById('modalContent');
  
  content.innerHTML = `
    <div style="text-align: center;">
      <h3 style="margin-bottom: 15px; color: #333;">📹 ${filename}</h3>
      <video controls autoplay loop style="max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
        <source src="${url}" type="video/mp4">
        您的浏览器不支持视频播放
      </video>
      <div style="margin-top: 15px;">
        <a href="${url}" download="${filename}" style="display: inline-block; padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-size: 14px;">
          💾 下载视频
        </a>
      </div>
    </div>
  `;
  
  modal.classList.add('active');
}

// 关闭模态框
function closeModal() {
  document.getElementById('resultModal').classList.remove('active');
}

// 切换标签
function switchTab(tabName) {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.classList.remove('active');
    if (tab.textContent.includes(
      tabName === 'workflow' ? '工作流' : '任务列表'
    )) {
      tab.classList.add('active');
    }
  });
  
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
  });
  document.getElementById(`${tabName}Tab`).classList.add('active');
  
  if (tabName === 'tasks') {
    // 如果是首次加载任务标签，显示加载状态；否则静默更新
    if (allTasks.length === 0) {
      isFirstLoad = true;
      loadTasks(200, true);
    } else {
      loadTasks(200, false);
    }
  }
}

// 显示通知
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 10px;
    color: white;
    font-size: 14px;
    z-index: 10000;
    animation: slideIn 0.3s ease;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
  `;
  
  const colors = {
    info: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    success: 'linear-gradient(135deg, #4caf50 0%, #45a049 100%)',
    error: 'linear-gradient(135deg, #f44336 0%, #da190b 100%)',
    warning: 'linear-gradient(135deg, #ff9800 0%, #f57c00 100%)'
  };
  notification.style.background = colors[type] || colors.info;
  
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 3000);
}

