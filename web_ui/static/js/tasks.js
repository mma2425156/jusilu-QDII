/**
 * 集思录QDII数据助手 - 任务管理模块
 */

const TaskModule = (function() {
  'use strict';
  
  /**
   * 加载任务列表
   */
  function loadTasks() {
    const taskTable = document.getElementById('taskTable');
    if (!taskTable) return;
    
    const tbody = taskTable.querySelector('tbody');
    if (!tbody) return;
    
    // 显示加载状态
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <p class="mt-2 text-secondary">正在加载任务列表...</p>
        </td>
      </tr>
    `;
    
    API.loadTasks()
      .then(data => {
        if (data.status === 'success') {
          renderTaskList(data.tasks);
        } else {
          throw new Error(data.message || '加载任务失败');
        }
      })
      .catch(error => {
        console.error('加载任务错误:', error);
        app.showToast('加载失败', error.message, 'danger');
        tbody.innerHTML = `
          <tr>
            <td colspan="4" class="text-center py-4 text-danger">
              <i class="fas fa-exclamation-circle fa-2x mb-3"></i>
              <p>加载失败，请稍后再试</p>
            </td>
          </tr>
        `;
      });
  }
  
  /**
   * 渲染任务列表
   */
  function renderTaskList(tasks) {
    const tbody = document.querySelector('#taskTable tbody');
    if (!tbody) return;
    
    // 更新任务计数
    const taskCountEl = document.getElementById('taskCount');
    if (taskCountEl) {
      taskCountEl.textContent = tasks.length;
    }
    
    if (tasks.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-4 text-secondary">
            <i class="fas fa-info-circle fa-2x mb-3"></i>
            <p>暂无保存的任务</p>
          </td>
        </tr>
      `;
      return;
    }
    
    let html = '';
    
    tasks.forEach(task => {
      const conditions = JSON.parse(task.conditions);
      
      // 格式化执行时间，更易读
      const displayTime = formatCronExpression(task.cron_expression);
      
      // 截断收件人，如果太长就显示部分并加省略号
      const recipientsList = task.recipients.split(',');
      let recipientsDisplay = '';
      
      if (recipientsList.length > 2) {
        recipientsDisplay = `${recipientsList[0].trim()} 等 ${recipientsList.length} 个收件人`;
      } else {
        recipientsDisplay = task.recipients;
      }
      
      html += `
        <tr data-task-id="${task.id}" class="slide-in-up">
          <td>
            <div class="fw-medium">${displayTime}</div>
          </td>
          <td>
            <div class="small text-secondary" title="${task.recipients}">${recipientsDisplay}</div>
          </td>
          <td>
            <div class="small">
              <span class="badge ${getStatusBadgeClass(conditions.status_filter)} mb-1">
                ${getStatusText(conditions.status_filter)}
              </span>
              <div>溢价率 ≥ ${conditions.premium_min}</div>
            </div>
          </td>
          <td>
            <span class="badge ${task.is_active ? 'badge-success' : 'badge-secondary'}">
              ${task.is_active ? '运行中' : '已停止'}
            </span>
          </td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              <button class="btn btn-sm ${task.is_active ? 'btn-warning stop-task' : 'btn-success start-task'}" 
                      data-bs-toggle="tooltip" title="${task.is_active ? '停止任务' : '启动任务'}">
                <i class="fas fa-${task.is_active ? 'pause' : 'play'}"></i>
              </button>
              <button class="btn btn-sm btn-primary edit-task" data-bs-toggle="tooltip" title="编辑任务">
                <i class="fas fa-edit"></i>
              </button>
              <button class="btn btn-sm btn-info view-logs" data-bs-toggle="tooltip" title="查看日志">
                <i class="fas fa-list"></i>
              </button>
              <button class="btn btn-sm btn-danger delete-task" data-bs-toggle="tooltip" title="删除任务"
                      data-task-name="${displayTime}">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    });
    
    tbody.innerHTML = html;
    
    // 初始化工具提示
    initTooltips();
  }
  
  /**
   * 初始化工具提示
   */
  function initTooltips() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
      const title = el.getAttribute('title') || '';
      
      // 如果已经有工具提示内容，则不再添加
      if (el.querySelector('.tooltip-content')) return;
      
      const tooltipContent = document.createElement('div');
      tooltipContent.classList.add('tooltip-content');
      tooltipContent.textContent = title;
      el.appendChild(tooltipContent);
      el.setAttribute('title', '');
    });
  }
  
  /**
   * 切换任务状态
   */
  function toggleTaskStatus(button, taskId) {
    if (!button || !taskId) return;
    
    const isStart = button.classList.contains('start-task');
    const originalHtml = button.innerHTML;
    
    // 显示加载状态
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    button.disabled = true;
    
    API.toggleTaskStatus(taskId, isStart)
      .then(response => {
        if (response.status === 'success') {
          // 显示成功消息
          app.showToast('操作成功', `任务已${isStart ? '启动' : '停止'}`, isStart ? 'success' : 'warning');
          // 重新加载任务列表
          loadTasks();
        } else {
          throw new Error(response.message || '操作失败');
        }
      })
      .catch(error => {
        console.error('切换任务状态错误:', error);
        app.showToast('操作失败', error.message, 'danger');
        // 恢复按钮状态
        button.innerHTML = originalHtml;
        button.disabled = false;
      });
  }
  
  /**
   * 编辑任务
   */
  function editTask(taskId) {
    if (!taskId) return;
    
    const taskForm = document.getElementById('taskConfigForm');
    if (!taskForm) return;
    
    // 重置表单
    resetTaskForm();
    
    // 显示加载状态
    taskForm.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-primary mb-3" role="status">
          <span class="visually-hidden">加载中...</span>
        </div>
        <p class="text-muted">正在加载任务信息...</p>
      </div>
    `;
    
    // 显示模态框
    app.showModal(document.getElementById('taskConfigModal'));
    
    // 加载任务数据
    API.loadTask(taskId)
      .then(data => {
        if (data.status === 'success' && data.tasks && data.tasks.length > 0) {
          const task = data.tasks[0];
          renderTaskForm(task);
        } else {
          throw new Error(data.message || '任务不存在');
        }
      })
      .catch(error => {
        console.error('加载任务错误:', error);
        app.showToast('加载失败', error.message, 'danger');
        app.hideModal(document.getElementById('taskConfigModal'));
      });
  }
  
  /**
   * 重置任务表单
   */
  function resetTaskForm() {
    const taskForm = document.getElementById('taskConfigForm');
    if (!taskForm) return;
    
    // 重置表单内容
    taskForm.innerHTML = `
      <div class="mb-3">
        <label class="form-label fw-medium">执行时间</label>
        <div class="mb-3">
          <div class="d-flex gap-2 align-items-center mb-2">
            <input type="time" class="form-control" id="executionTime" value="09:00" required>
            <span>每</span>
          </div>
          <div class="btn-group d-flex flex-wrap" role="group">
            <input type="checkbox" class="btn-check" id="weekday1" name="weekdays" value="1" autocomplete="off">
            <label class="btn btn-outline-primary btn-sm" for="weekday1">周一</label>
            
            <input type="checkbox" class="btn-check" id="weekday2" name="weekdays" value="2" autocomplete="off">
            <label class="btn btn-outline-primary btn-sm" for="weekday2">周二</label>
            
            <input type="checkbox" class="btn-check" id="weekday3" name="weekdays" value="3" autocomplete="off">
            <label class="btn btn-outline-primary btn-sm" for="weekday3">周三</label>
            
            <input type="checkbox" class="btn-check" id="weekday4" name="weekdays" value="4" autocomplete="off">
            <label class="btn btn-outline-primary btn-sm" for="weekday4">周四</label>
            
            <input type="checkbox" class="btn-check" id="weekday5" name="weekdays" value="5" autocomplete="off">
            <label class="btn btn-outline-primary btn-sm" for="weekday5">周五</label>
            
            <input type="checkbox" class="btn-check" id="weekday6" name="weekdays" value="6" autocomplete="off">
            <label class="btn btn-outline-primary btn-sm" for="weekday6">周六</label>
            
            <input type="checkbox" class="btn-check" id="weekday0" name="weekdays" value="0" autocomplete="off">
            <label class="btn btn-outline-primary btn-sm" for="weekday0">周日</label>
          </div>
          <div class="mt-2">
            <input type="checkbox" class="btn-check" id="selectAllDays" autocomplete="off">
            <label class="btn btn-outline-primary btn-sm" for="selectAllDays">每天</label>
          </div>
        </div>
      </div>
      
      <div class="mb-3">
        <label for="recipients" class="form-label fw-medium">收件人邮箱</label>
        <textarea class="form-control" id="recipients" rows="2" 
          placeholder="例如: user1@example.com, user2@example.com (多个邮箱用英文逗号分隔)" required></textarea>
        <div class="form-text small">多个邮箱请用英文逗号分隔</div>
      </div>
      
      <div class="mb-4">
        <label class="form-label fw-medium">数据筛选条件</label>
        <div class="row">
          <div class="col-md-6 mb-3">
            <label for="taskPremiumMin" class="form-label">T-1溢价率 ≥</label>
            <input type="number" step="0.01" class="form-control" id="taskPremiumMin" value="0" required>
          </div>
          <div class="col-md-6 mb-3">
            <label for="taskStatusFilter" class="form-label">申购状态</label>
            <select class="form-select" id="taskStatusFilter" required>
              <option value="all">全部</option>
              <option value="open">开放申购</option>
              <option value="closed">暂停申购</option>
              <option value="limited">限量申购</option>
            </select>
          </div>
        </div>
      </div>
    `;
    
    // 重新绑定事件
    bindFormEvents();
  }
  
  /**
   * 渲染任务表单
   */
  function renderTaskForm(task) {
    if (!task) return;
    
    // 解析任务数据
    const conditions = JSON.parse(task.conditions);
    const cronParts = task.cron_expression.split(' ');
    const minutes = cronParts[0];
    const hours = cronParts[1];
    const days = cronParts[4];
    
    // 设置表单值
    document.getElementById('executionTime').value = `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}`;
    document.getElementById('recipients').value = task.recipients;
    document.getElementById('taskPremiumMin').value = conditions.premium_min;
    document.getElementById('taskStatusFilter').value = conditions.status_filter;
    
    // 设置星期选择
    if (days === '*') {
      document.getElementById('selectAllDays').checked = true;
      document.querySelectorAll('input[name="weekdays"]').forEach(checkbox => {
        checkbox.checked = true;
      });
    } else {
      const selectedDays = days.split(',');
      selectedDays.forEach(day => {
        const checkbox = document.getElementById(`weekday${day}`);
        if (checkbox) checkbox.checked = true;
      });
      
      // 检查是否所有天都被选中
      updateSelectAllState();
    }
    
    // 添加任务ID到表单，用于更新操作
    const taskForm = document.getElementById('taskConfigForm');
    if (taskForm) {
      taskForm.dataset.taskId = task.id;
    }
  }
  
  /**
   * 保存任务
   */
  function saveTask() {
    const btn = document.getElementById('saveTaskConfig');
    if (!btn) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>保存中...';
    btn.disabled = true;
    
    // 生成cron表达式
    const taskData = buildTaskData();
    if (!taskData) {
      btn.innerHTML = originalText;
      btn.disabled = false;
      return;
    }
    
    // 添加任务ID（如果是编辑现有任务）
    const taskForm = document.getElementById('taskConfigForm');
    if (taskForm && taskForm.dataset.taskId) {
      taskData.id = taskForm.dataset.taskId;
    }
    
    API.saveTask(taskData)
      .then(response => {
        if (response.status === 'success') {
          app.showToast('已保存', '任务配置已成功保存', 'success');
          app.hideModal(document.getElementById('taskConfigModal'));
          // 重新加载任务列表
          loadTasks();
        } else {
          throw new Error(response.message || '保存失败');
        }
      })
      .catch(error => {
        console.error('保存任务错误:', error);
        app.showToast('保存失败', error.message, 'danger');
      })
      .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      });
  }
  
  /**
   * 测试任务
   */
  function testTask() {
    const btn = document.getElementById('testTaskConfig');
    if (!btn) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>测试中...';
    btn.disabled = true;
    
    // 构建任务数据
    const taskData = buildTaskData();
    if (!taskData) {
      btn.innerHTML = originalText;
      btn.disabled = false;
      return;
    }
    
    API.testTask(taskData)
      .then(response => {
        if (response.status === 'success') {
          showTestResultModal(taskData, response);
        } else {
          throw new Error(response.message || '测试失败');
        }
      })
      .catch(error => {
        console.error('测试任务错误:', error);
        app.showToast('测试失败', error.message, 'danger');
      })
      .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      });
  }
  
  /**
   * 显示测试结果模态框
   */
  function showTestResultModal(taskData, response) {
    // 创建模态框
    const modal = document.createElement('div');
    modal.id = 'testResultModal';
    modal.className = 'modal fade-in';
    
    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header bg-success text-white">
            <h5 class="modal-title"><i class="fas fa-check-circle me-2"></i>测试成功</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <p>已成功发送测试邮件至：</p>
            <div class="alert alert-light">
              ${taskData.recipients.join('<br>')}
            </div>
            <p>筛选结果：找到 <strong>${response.filtered_count}</strong> 条符合条件的数据</p>
            <p class="text-muted small mt-3">请检查收件箱查看邮件内容</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    app.showModal(modal);
    
    // 添加关闭事件
    modal.querySelector('[data-bs-dismiss="modal"]').addEventListener('click', function() {
      app.hideModal(modal);
      setTimeout(() => modal.remove(), 300);
    });
  }
  
  /**
   * 构建任务数据
   */
  function buildTaskData() {
    // 获取执行时间
    const executionTime = document.getElementById('executionTime').value;
    if (!executionTime) {
      app.showToast('表单错误', '请设置执行时间', 'warning');
      return null;
    }
    
    const timeParts = executionTime.split(':');
    const hours = timeParts[0];
    const minutes = timeParts[1];
    
    // 获取执行星期
    const weekdays = [];
    document.querySelectorAll('input[name="weekdays"]:checked').forEach(checkbox => {
      if (checkbox.id !== 'selectAllDays') {
        weekdays.push(checkbox.value);
      }
    });
    
    // 生成cron表达式
    let cronExpression;
    if (document.getElementById('selectAllDays').checked || weekdays.length === 7) {
      cronExpression = `${minutes} ${hours} * * *`;
    } else if (weekdays.length > 0) {
      cronExpression = `${minutes} ${hours} * * ${weekdays.join(',')}`;
    } else {
      app.showToast('表单错误', '请至少选择一天', 'warning');
      return null;
    }
    
    // 处理收件人
    const recipients = document.getElementById('recipients').value
      .split(',')
      .map(email => email.trim())
      .filter(email => email);
    
    if (recipients.length === 0) {
      app.showToast('表单错误', '请至少添加一个收件人邮箱', 'warning');
      return null;
    }
    
    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const invalidEmails = recipients.filter(email => !emailRegex.test(email));
    if (invalidEmails.length > 0) {
      app.showToast('表单错误', `以下邮箱格式不正确: ${invalidEmails.join(', ')}`, 'warning');
      return null;
    }
    
    // 溢价率检查
    const premiumMin = parseFloat(document.getElementById('taskPremiumMin').value);
    if (isNaN(premiumMin) || premiumMin < 0) {
      app.showToast('表单错误', '请输入有效的溢价率最小值', 'warning');
      return null;
    }
    
    // 构建任务条件
    const conditions = {
      premium_min: premiumMin,
      status_filter: document.getElementById('taskStatusFilter').value
    };
    
    return {
      cron_expression: cronExpression,
      recipients: recipients.join(', '),
      conditions: JSON.stringify(conditions)
    };
  }
  
  /**
   * 查看任务日志
   */
  function viewTaskLogs(taskId) {
    if (!taskId) return;
    
    const logModal = document.getElementById('logModal');
    const logContent = document.getElementById('logContent');
    
    if (!logModal || !logContent) return;
    
    // 显示加载中
    logContent.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-primary mb-3" role="status">
          <span class="visually-hidden">加载中...</span>
        </div>
        <p class="text-muted">正在加载日志数据...</p>
      </div>
    `;
    
    app.showModal(logModal);
    
    API.getTaskLogs(taskId)
      .then(data => {
        if (data.status === 'success') {
          if (data.logs.length === 0) {
            logContent.innerHTML = `
              <div class="text-center py-5">
                <i class="fas fa-info-circle text-info fa-3x mb-3"></i>
                <p class="text-muted">暂无执行日志记录</p>
              </div>
            `;
          } else {
            renderTaskLogs(data.logs);
          }
        } else {
          throw new Error(data.message || '获取日志失败');
        }
      })
      .catch(error => {
        console.error('获取任务日志错误:', error);
        logContent.innerHTML = `
          <div class="alert alert-danger">
            <i class="fas fa-exclamation-circle me-2"></i>加载日志失败: ${error.message}
          </div>
        `;
      });
  }
  
  /**
   * 渲染任务日志
   */
  function renderTaskLogs(logs) {
    const logContent = document.getElementById('logContent');
    if (!logContent) return;
    
    let html = `
      <table class="table table-hover">
        <thead>
          <tr class="table-light">
            <th>执行时间</th>
            <th>状态</th>
            <th>筛选结果</th>
          </tr>
        </thead>
        <tbody>
    `;
    
    logs.forEach(log => {
      // 格式化时间
      const time = new Date(log.run_time);
      const formattedTime = time.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
      
      html += `
        <tr>
          <td>${formattedTime}</td>
          <td>
            <span class="badge ${log.status === 'executed' ? 'badge-success' : 'badge-danger'}">
              ${log.status === 'executed' ? '执行成功' : '执行失败'}
            </span>
          </td>
          <td>${log.filtered_count}条数据</td>
        </tr>
      `;
    });
    
    html += '</tbody></table>';
    
    logContent.innerHTML = html;
  }
  
  /**
   * 删除任务
   */
  function deleteTask(button, taskId) {
    if (!button || !taskId) return;
    
    // 获取任务名称用于确认
    const taskName = button.getAttribute('data-task-name') || '此任务';
    
    // 显示确认对话框
    if (!confirm(`确认要删除 ${taskName} 吗？此操作不可恢复!`)) {
      return;
    }
    
    const originalHtml = button.innerHTML;
    
    // 显示加载状态
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    button.disabled = true;
    
    API.deleteTask(taskId)
      .then(response => {
        if (response.status === 'success') {
          // 显示成功消息
          app.showToast('删除成功', '任务已删除', 'success');
          
          // 重新加载任务列表
          loadTasks();
        } else {
          throw new Error(response.message || '删除失败');
        }
      })
      .catch(error => {
        console.error('删除任务错误:', error);
        app.showToast('删除失败', error.message, 'danger');
        
        // 恢复按钮状态
        button.innerHTML = originalHtml;
        button.disabled = false;
      });
  }
  
  /**
   * 绑定表单事件
   */
  function bindFormEvents() {
    // 全选/取消全选星期
    const selectAllDays = document.getElementById('selectAllDays');
    if (selectAllDays) {
      selectAllDays.addEventListener('change', function() {
        const weekdays = document.querySelectorAll('input[name="weekdays"]');
        weekdays.forEach(checkbox => {
          checkbox.checked = this.checked;
        });
      });
      
      // 监听每个星期的变化
      document.querySelectorAll('input[name="weekdays"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
          updateSelectAllState();
        });
      });
    }
  }
  
  /**
   * 更新全选状态
   */
  function updateSelectAllState() {
    const checkboxes = document.querySelectorAll('input[name="weekdays"]');
    const selectAll = document.getElementById('selectAllDays');
    
    if (!selectAll) return;
    
    const allChecked = Array.from(checkboxes).every(c => c.checked);
    selectAll.checked = allChecked;
  }
  
  /**
   * 格式化cron表达式为易读格式
   * @param {string} cronExpression - cron表达式，格式为：分 时 * * 日(0-6)
   * @returns {string} 格式化后的文本
   */
  function formatCronExpression(cronExpression) {
    if (!cronExpression) return '无效时间';
    
    // 解析cron表达式
    const parts = cronExpression.split(' ');
    if (parts.length < 5) return cronExpression;
    
    const minute = parts[0];
    const hour = parts[1];
    const dayOfWeek = parts[4]; // 0-6，0表示周日
    
    // 格式化时间
    const timeStr = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
    
    // 解析星期几
    const weekdays = [];
    const weekdayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    
    if (dayOfWeek === '*') {
      return `每天 ${timeStr}`;
    } else {
      const days = dayOfWeek.split(',');
      days.forEach(day => {
        if (day >= 0 && day <= 6) {
          weekdays.push(weekdayNames[day]);
        }
      });
      
      if (weekdays.length === 7) {
        return `每天 ${timeStr}`;
      } else if (weekdays.length === 0) {
        return `${timeStr}`;
      } else if (weekdays.length <= 3) {
        return `每${weekdays.join('、')} ${timeStr}`;
      } else {
        return `每${weekdays.slice(0, 2).join('、')}等 ${timeStr}`;
      }
    }
  }
  
  /**
   * 获取状态文本
   */
  function getStatusText(statusFilter) {
    const statusMap = {
      'all': '全部状态',
      'open': '开放申购',
      'limited': '限量申购',
      'closed': '暂停申购'
    };
    return statusMap[statusFilter] || statusFilter;
  }
  
  /**
   * 获取状态徽章样式类
   */
  function getStatusBadgeClass(statusFilter) {
    const classMap = {
      'all': 'badge-secondary',
      'open': 'badge-success',
      'limited': 'badge-warning',
      'closed': 'badge-danger'
    };
    return classMap[statusFilter] || 'badge-secondary';
  }
  
  // 导出公共方法
  return {
    loadTasks,
    saveTask,
    testTask,
    toggleTaskStatus,
    editTask,
    viewTaskLogs,
    deleteTask,
    resetTaskForm
  };
})();

// 将模块导出到全局作用域
window.TaskModule = TaskModule; 