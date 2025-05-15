/**
 * 集思录QDII数据助手 - 主要脚本
 */

// 主应用对象
const app = (function() {
  'use strict';

  // 全局变量和配置
  const config = {
    refreshCooldown: 30, // 刷新冷却时间（秒）
    saveActionCooldown: 2, // 保存操作冷却时间（秒）
    testActionCooldown: 3, // 测试操作冷却时间（秒）
    toastDuration: 3000, // Toast显示时间（毫秒）
  };

  // 冷却时间计时器
  let refreshCooldownTimer = null;

  // DOM加载完成后初始化
  document.addEventListener('DOMContentLoaded', () => {
    // 初始化主题
    initTheme();
    
    // 初始化组件
    initComponents();
    
    // 初始化事件监听
    initEventListeners();
    
    // 初始化任务列表
    if (typeof TaskModule !== 'undefined' && TaskModule.loadTasks) {
      TaskModule.loadTasks();
    }
    
    // 初始化工具提示
    initTooltips();
  });

  /**
   * 初始化主题
   */
  function initTheme() {
    const themeSwitch = document.getElementById('themeSwitch');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // 检查本地存储中的主题偏好
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDarkScheme.matches)) {
      document.documentElement.setAttribute('data-theme', 'dark');
      if (themeSwitch) themeSwitch.checked = true;
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      if (themeSwitch) themeSwitch.checked = false;
    }
    
    // 监听主题切换
    if (themeSwitch) {
      themeSwitch.addEventListener('change', function() {
        if (this.checked) {
          document.documentElement.setAttribute('data-theme', 'dark');
          localStorage.setItem('theme', 'dark');
        } else {
          document.documentElement.setAttribute('data-theme', 'light');
          localStorage.setItem('theme', 'light');
        }
      });
    }
  }

  /**
   * 初始化事件监听
   */
  function initEventListeners() {
    // 筛选表单提交
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
      filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        applyFilters();
      });
    }
    
    // 刷新数据按钮
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', function() {
        if (this.disabled) return;
        refreshData();
      });
    }
    
    // 邮件配置表单
    const saveMailConfigBtn = document.getElementById('saveMailConfig');
    if (saveMailConfigBtn) {
      saveMailConfigBtn.addEventListener('click', saveMailConfig);
    }
    
    // 测试邮件配置
    const testMailConfigBtn = document.getElementById('testMailConfig');
    if (testMailConfigBtn) {
      testMailConfigBtn.addEventListener('click', testMailConfig);
    }
    
    // 保存任务配置
    const saveTaskConfigBtn = document.getElementById('saveTaskConfig');
    if (saveTaskConfigBtn) {
      saveTaskConfigBtn.addEventListener('click', saveTaskConfig);
    }
    
    // 测试任务配置
    const testTaskConfigBtn = document.getElementById('testTaskConfig');
    if (testTaskConfigBtn) {
      testTaskConfigBtn.addEventListener('click', testTaskConfig);
    }
    
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
          const allChecked = Array.from(document.querySelectorAll('input[name="weekdays"]')).every(c => c.checked);
          selectAllDays.checked = allChecked;
        });
      });
    }
    
    // 任务操作事件委托
    const taskTable = document.getElementById('taskTable');
    if (taskTable) {
      taskTable.addEventListener('click', function(e) {
        const target = e.target.closest('button');
        if (!target) return;
        
        const tr = target.closest('tr');
        if (!tr) return;
        
        const taskId = tr.dataset.taskId;
        
        if (target.classList.contains('start-task') || target.classList.contains('stop-task')) {
          toggleTaskStatus(target, taskId);
        } else if (target.classList.contains('edit-task')) {
          editTask(taskId);
        } else if (target.classList.contains('view-logs')) {
          viewTaskLogs(taskId);
        } else if (target.classList.contains('delete-task')) {
          deleteTask(target, taskId);
        }
      });
    }
    
    // 模态框初始化事件
    const mailConfigModal = document.getElementById('mailConfigModal');
    if (mailConfigModal) {
      mailConfigModal.addEventListener('show.bs.modal', function() {
        loadMailConfig();
      });
    }
  }
  
  /**
   * 初始化各种组件
   */
  function initComponents() {
    // 初始化Bootstrap组件
    initBootstrapComponents();
    
    // 初始化模态框关闭按钮
    document.querySelectorAll('[data-dismiss="modal"]').forEach(button => {
      button.addEventListener('click', function() {
        const modal = this.closest('.modal');
        hideModal(modal);
      });
    });
    
    // 初始化BS模态框触发器
    document.querySelectorAll('[data-bs-toggle="modal"]').forEach(button => {
      const targetModal = document.querySelector(button.getAttribute('data-bs-target'));
      if (targetModal) {
        button.addEventListener('click', function() {
          showModal(targetModal);
        });
      }
    });
  }
  
  /**
   * 初始化Bootstrap组件
   */
  function initBootstrapComponents() {
    // 这里可以添加任何需要手动初始化的Bootstrap组件
  }
  
  /**
   * 初始化工具提示
   */
  function initTooltips() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
      const title = el.getAttribute('title') || '';
      const tooltipContent = document.createElement('div');
      tooltipContent.classList.add('tooltip-content');
      tooltipContent.textContent = title;
      el.appendChild(tooltipContent);
      el.setAttribute('title', '');
    });
  }
  
  /**
   * 显示模态框
   */
  function showModal(modalElement) {
    if (!modalElement) return;
    
    // 创建backdrop
    const backdrop = document.createElement('div');
    backdrop.classList.add('modal-backdrop');
    document.body.appendChild(backdrop);
    
    // 显示模态框
    modalElement.style.display = 'block';
    modalElement.classList.add('show');
    document.body.classList.add('modal-open');
    
    // 触发显示事件
    const event = new Event('show.bs.modal');
    modalElement.dispatchEvent(event);
  }
  
  /**
   * 隐藏模态框
   */
  function hideModal(modalElement) {
    if (!modalElement) return;
    
    // 移除backdrop
    const backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) backdrop.remove();
    
    // 隐藏模态框
    modalElement.style.display = 'none';
    modalElement.classList.remove('show');
    document.body.classList.remove('modal-open');
    
    // 触发隐藏事件
    const event = new Event('hide.bs.modal');
    modalElement.dispatchEvent(event);
  }
  
  /**
   * 刷新数据
   */
  function refreshData() {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshText = document.getElementById('refreshText');
    const refreshSpinner = document.getElementById('refreshSpinner');
    
    if (!refreshBtn || refreshBtn.disabled) return;
    
    // 检查冷却时间
    if (refreshCooldownTimer) {
      showToast('操作频繁', `请等待${refreshCooldownTimer}秒后再试`, 'warning');
      return;
    }
    
    // 禁用按钮，显示加载状态
    refreshBtn.disabled = true;
    refreshText.textContent = '正在刷新...';
    refreshSpinner.classList.remove('d-none');
    
    // 显示状态区域
    const refreshStatus = document.getElementById('refreshStatus');
    const statusMessage = document.getElementById('statusMessage');
    const statusOutput = document.getElementById('statusOutput');
    
    if (refreshStatus) refreshStatus.classList.remove('d-none');
    if (statusMessage) statusMessage.innerHTML = '<span class="fw-bold">正在刷新数据...</span>';
    if (statusOutput) statusOutput.textContent = '准备开始爬取数据...';
    
    // 开始刷新
    let lastEventTime = Date.now();
    const eventSource = new EventSource('/refresh-status');
    
    // 定时检查连接状态
    const connectionCheckInterval = setInterval(() => {
      const now = Date.now();
      if (now - lastEventTime > 10000) { // 10秒无响应认为连接断开
        eventSource.close();
        clearInterval(connectionCheckInterval);
        
        // 更新状态
        if (statusMessage) statusMessage.innerHTML = '<span class="fw-bold text-danger">刷新失败：连接超时</span>';
        
        // 恢复按钮状态
        resetRefreshButton();
        
        // 启动冷却时间
        startRefreshCooldown();
      }
    }, 2000);
    
    eventSource.onmessage = function(event) {
      lastEventTime = Date.now();
      
      try {
        const data = JSON.parse(event.data);
        
        if (data.status === 'completed') {
          // 刷新完成，关闭事件源
          eventSource.close();
          clearInterval(connectionCheckInterval);
          
          // 更新状态
          if (statusMessage) statusMessage.innerHTML = '<span class="fw-bold text-success">数据刷新成功！</span>';
          if (statusOutput) statusOutput.textContent = data.message || '操作完成';
          
          // 完成后自动刷新页面
          setTimeout(() => {
            window.location.reload();
          }, 1500);
        } else if (data.status === 'error') {
          // 发生错误，关闭事件源
          eventSource.close();
          clearInterval(connectionCheckInterval);
          
          // 更新状态
          if (statusMessage) statusMessage.innerHTML = '<span class="fw-bold text-danger">刷新失败</span>';
          if (statusOutput) statusOutput.textContent = data.message || '未知错误';
          
          // 恢复按钮状态
          resetRefreshButton();
          
          // 启动冷却时间
          startRefreshCooldown();
        } else {
          // 更新进度
          if (statusOutput) {
            // 追加新消息，保持最近10条
            const lines = statusOutput.textContent.split('\n');
            lines.push(data.message);
            if (lines.length > 10) lines.shift();
            statusOutput.textContent = lines.join('\n');
            // 自动滚动到底部
            statusOutput.scrollTop = statusOutput.scrollHeight;
          }
        }
      } catch (error) {
        console.error('解析事件数据错误:', error);
      }
    };
    
    eventSource.onerror = function() {
      eventSource.close();
      clearInterval(connectionCheckInterval);
      
      // 更新状态
      if (statusMessage) statusMessage.innerHTML = '<span class="fw-bold text-danger">连接错误</span>';
      
      // 恢复按钮状态
      resetRefreshButton();
      
      // 启动冷却时间
      startRefreshCooldown();
    };
  }
  
  /**
   * 恢复刷新按钮状态
   */
  function resetRefreshButton() {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshText = document.getElementById('refreshText');
    const refreshSpinner = document.getElementById('refreshSpinner');
    
    if (refreshBtn) refreshBtn.disabled = false;
    if (refreshText) refreshText.textContent = '刷新数据';
    if (refreshSpinner) refreshSpinner.classList.add('d-none');
  }
  
  /**
   * 启动刷新按钮冷却时间
   */
  function startRefreshCooldown() {
    let countdown = config.refreshCooldown;
    
    refreshCooldownTimer = countdown;
    
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshText = document.getElementById('refreshText');
    
    if (refreshBtn) {
      refreshBtn.disabled = true;
      if (refreshText) refreshText.textContent = `冷却中 (${countdown}s)`;
    }
    
    const interval = setInterval(() => {
      countdown--;
      refreshCooldownTimer = countdown;
      
      if (refreshText) refreshText.textContent = `冷却中 (${countdown}s)`;
      
      if (countdown <= 0) {
        clearInterval(interval);
        refreshCooldownTimer = null;
        
        if (refreshBtn) refreshBtn.disabled = false;
        if (refreshText) refreshText.textContent = '刷新数据';
      }
    }, 1000);
  }
  
  /**
   * 显示Toast消息
   */
  function showToast(title, message, type = 'success') {
    // 创建toast容器
    let toastContainer = document.querySelector('.toast-container');
    
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.classList.add('toast-container');
      document.body.appendChild(toastContainer);
    }
    
    // 创建toast元素
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.classList.add('toast');
    toast.classList.add(`toast-${type}`);
    
    // 设置内容
    toast.innerHTML = `
      <div class="toast-header">
        <i class="fas fa-${type === 'success' ? 'check-circle' : 
                        type === 'warning' ? 'exclamation-triangle' : 
                        type === 'danger' ? 'times-circle' : 'info-circle'} me-2"></i>
        <strong class="me-auto">${title}</strong>
        <button type="button" class="btn-close" onclick="document.getElementById('${toastId}').remove()"></button>
      </div>
      <div class="toast-body">${message}</div>
    `;
    
    // 添加到容器
    toastContainer.appendChild(toast);
    
    // 显示toast
    setTimeout(() => {
      toast.classList.add('show');
    }, 10);
    
    // 自动移除
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        toast.remove();
      }, 300);
    }, config.toastDuration);
  }

  // 公开接口
  return {
    showToast,
    showModal,
    hideModal,
    refreshData
  };
})(); 