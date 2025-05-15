/**
 * 集思录QDII数据助手 - API交互模块
 */

const API = (function() {
  'use strict';
  
  // 私有变量
  const cooldowns = {
    refresh: false,
    save: false,
    test: false,
    delete: false
  };
  
  // 冷却时间配置（毫秒）
  const cooldownTimes = {
    refresh: 30000, // 刷新操作冷却30秒
    save: 2000,     // 保存操作冷却2秒
    test: 3000,     // 测试操作冷却3秒
    delete: 1000    // 删除操作冷却1秒
  };
  
  /**
   * 设置冷却状态
   * @param {string} action - 操作类型
   * @returns {boolean} 如果已在冷却中返回true，否则返回false
   */
  function setCooldown(action) {
    if (cooldowns[action]) return true;
    
    cooldowns[action] = true;
    setTimeout(() => { 
      cooldowns[action] = false; 
    }, cooldownTimes[action]);
    
    return false;
  }
  
  /**
   * 处理API错误
   * @param {Error} error - 错误对象 
   * @returns {Object} 格式化的错误响应
   */
  function handleApiError(error) {
    console.error('API错误:', error);
    
    // 尝试解析错误消息
    let errorMessage = '操作失败，请稍后再试';
    
    if (error.message) {
      errorMessage = error.message;
    }
    
    if (typeof app !== 'undefined' && app.showToast) {
      app.showToast('操作失败', errorMessage, 'danger');
    }
    
    return {
      status: 'error',
      message: errorMessage
    };
  }
  
  // 公共方法
  return {
    /**
     * 加载邮件配置
     */
    loadMailConfig: function() {
      return fetch('/api/mail/config')
        .then(response => {
          if (!response.ok) {
            const error = new Error('加载配置失败');
            error.status = response.status;
            throw error;
          }
          return response.json();
        })
        .catch(handleApiError);
    },
    
    /**
     * 保存邮件配置
     */
    saveMailConfig: function(config) {
      if (setCooldown('save')) {
        return Promise.reject(new Error('操作过于频繁，请稍后再试'));
      }
      
      return fetch('/api/mail/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      })
      .then(response => {
        if (!response.ok) {
          const error = new Error('保存配置失败');
          error.status = response.status;
          throw error;
        }
        return response.json();
      })
      .catch(handleApiError);
    },
    
    /**
     * 测试邮件配置
     */
    testMailConfig: function(email) {
      if (setCooldown('test')) {
        return Promise.reject(new Error('操作过于频繁，请稍后再试'));
      }
      
      return fetch('/api/mail/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ recipient: email })
      })
      .then(response => {
        if (!response.ok) {
          const error = new Error('测试失败');
          error.status = response.status;
          throw error;
        }
        return response.json();
      })
      .catch(handleApiError);
    },
    
    /**
     * 加载任务列表
     */
    loadTasks: function() {
      return fetch('/api/tasks')
        .then(response => {
          if (!response.ok) {
            const error = new Error('加载任务失败');
            error.status = response.status;
            throw error;
          }
          return response.json();
        })
        .catch(handleApiError);
    },
    
    /**
     * 加载指定任务
     */
    loadTask: function(taskId) {
      return fetch(`/api/tasks?id=${taskId}`)
        .then(response => {
          if (!response.ok) {
            const error = new Error('加载任务失败');
            error.status = response.status;
            throw error;
          }
          return response.json();
        })
        .catch(handleApiError);
    },
    
    /**
     * 保存任务
     */
    saveTask: function(taskData) {
      if (setCooldown('save')) {
        return Promise.reject(new Error('操作过于频繁，请稍后再试'));
      }
      
      return fetch('/api/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(taskData)
      })
      .then(response => {
        if (!response.ok) {
          const error = new Error('保存任务失败');
          error.status = response.status;
          throw error;
        }
        return response.json();
      })
      .catch(handleApiError);
    },
    
    /**
     * 测试任务
     */
    testTask: function(taskData) {
      if (setCooldown('test')) {
        return Promise.reject(new Error('操作过于频繁，请稍后再试'));
      }
      
      return fetch('/api/tasks/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(taskData)
      })
      .then(response => {
        if (!response.ok) {
          const error = new Error('测试任务失败');
          error.status = response.status;
          throw error;
        }
        return response.json();
      })
      .catch(handleApiError);
    },
    
    /**
     * 切换任务状态
     */
    toggleTaskStatus: function(taskId, isActive) {
      if (setCooldown('save')) {
        return Promise.reject(new Error('操作过于频繁，请稍后再试'));
      }
      
      return fetch(`/api/tasks/${taskId}/status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_active: isActive })
      })
      .then(response => {
        if (!response.ok) {
          const error = new Error('更新任务状态失败');
          error.status = response.status;
          throw error;
        }
        return response.json();
      })
      .catch(handleApiError);
    },
    
    /**
     * 获取任务日志
     */
    getTaskLogs: function(taskId) {
      return fetch(`/api/tasks/${taskId}/logs`)
        .then(response => {
          if (!response.ok) {
            const error = new Error('获取日志失败');
            error.status = response.status;
            throw error;
          }
          return response.json();
        })
        .catch(handleApiError);
    },
    
    /**
     * 删除任务
     */
    deleteTask: function(taskId) {
      if (setCooldown('delete')) {
        return Promise.reject(new Error('操作过于频繁，请稍后再试'));
      }
      
      return fetch(`/api/tasks/${taskId}`, {
        method: 'DELETE'
      })
      .then(response => {
        if (!response.ok) {
          const error = new Error('删除任务失败');
          error.status = response.status;
          throw error;
        }
        return response.json();
      })
      .catch(handleApiError);
    },
    
    /**
     * 刷新数据
     */
    refreshData: function(parameters) {
      if (cooldowns.refresh) return Promise.reject(new Error('操作过于频繁，请稍后再试'));
      
      cooldowns.refresh = true;
      setTimeout(() => { cooldowns.refresh = false; }, 30000);
      
      const formData = new FormData();
      for (const key in parameters) {
        formData.append(key, parameters[key]);
      }
      
      return fetch('/refresh', {
        method: 'POST',
        body: formData
      })
      .then(response => {
        if (!response.ok) throw new Error('刷新数据失败');
        return response.json();
      });
    }
  };
})();

/**
 * 邮件相关功能
 */
const EmailModule = (function() {
  /**
   * 加载邮件配置
   */
  function loadMailConfig() {
    const mailForm = document.getElementById('mailConfigForm');
    if (!mailForm) return;
    
    // 显示加载状态
    mailForm.innerHTML = `
      <div class="text-center py-4">
        <div class="spinner-border text-primary mb-3" role="status">
          <span class="visually-hidden">加载中...</span>
        </div>
        <p class="text-muted">正在加载邮件配置...</p>
      </div>
    `;
    
    API.loadMailConfig()
      .then(response => {
        if (response.status === 'success') {
          renderMailConfigForm(response.config);
        } else {
          throw new Error(response.message || '加载失败');
        }
      })
      .catch(error => {
        console.error('加载邮件配置错误:', error);
        mailForm.innerHTML = `
          <div class="alert alert-danger">
            <i class="fas fa-exclamation-circle me-2"></i>加载邮件配置失败
            <button class="btn btn-sm btn-outline-danger ms-3" onclick="EmailModule.loadMailConfig()">重试</button>
          </div>
        `;
      });
  }
  
  /**
   * 渲染邮件配置表单
   */
  function renderMailConfigForm(config) {
    const mailForm = document.getElementById('mailConfigForm');
    if (!mailForm) return;
    
    mailForm.innerHTML = `
      <div class="mb-3">
        <label for="smtpServer" class="form-label">SMTP服务器</label>
        <input type="text" class="form-control" id="smtpServer" value="${config.smtp_server || ''}" required>
      </div>
      <div class="mb-3">
        <label for="smtpPort" class="form-label">SMTP端口</label>
        <input type="number" class="form-control" id="smtpPort" value="${config.smtp_port || '465'}" required>
      </div>
      <div class="mb-3">
        <label for="username" class="form-label">邮箱账号</label>
        <input type="email" class="form-control" id="username" value="${config.username || ''}" required>
        <div class="form-text">同时作为SMTP登录用户名和发件人邮箱</div>
      </div>
      <div class="mb-3">
        <label for="password" class="form-label">密码</label>
        <input type="password" class="form-control" id="password" value="${config.password ? '******' : ''}" required>
      </div>
      <div class="mb-3 form-check">
        <input type="checkbox" class="form-check-input" id="useSSL" ${config.use_ssl ? 'checked' : ''}>
        <label class="form-check-label" for="useSSL">使用SSL</label>
      </div>
    `;
  }
  
  /**
   * 保存邮件配置
   */
  function saveMailConfig() {
    const btn = document.getElementById('saveMailConfig');
    if (!btn) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>保存中...';
    btn.disabled = true;
    
    const config = {
      smtp_server: document.getElementById('smtpServer').value,
      smtp_port: parseInt(document.getElementById('smtpPort').value),
      username: document.getElementById('username').value,
      password: document.getElementById('password').value === '******' ? '' : document.getElementById('password').value,
      sender_email: document.getElementById('username').value,
      use_ssl: document.getElementById('useSSL').checked
    };
    
    API.saveMailConfig(config)
      .then(response => {
        if (response.status === 'success') {
          app.showToast('已保存', '邮件配置已成功保存', 'success');
          app.hideModal(document.getElementById('mailConfigModal'));
        } else {
          throw new Error(response.message || '保存失败');
        }
      })
      .catch(error => {
        console.error('保存邮件配置错误:', error);
        app.showToast('保存失败', error.message, 'danger');
      })
      .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      });
  }
  
  /**
   * 测试邮件配置
   */
  function testMailConfig() {
    const btn = document.getElementById('testMailConfig');
    if (!btn) return;
    
    const email = prompt('请输入测试收件人邮箱:');
    if (!email) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>测试中...';
    btn.disabled = true;
    
    API.testMailConfig(email)
      .then(response => {
        if (response.status === 'success') {
          // 创建测试成功模态框
          const modal = document.createElement('div');
          modal.className = 'modal';
          modal.id = 'mailTestModal';
          modal.innerHTML = `
            <div class="modal-dialog modal-sm">
              <div class="modal-content">
                <div class="modal-header bg-success text-white">
                  <h5 class="modal-title"><i class="fas fa-check-circle me-2"></i>发送成功</h5>
                  <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                  <p>测试邮件已发送至：</p>
                  <div class="alert alert-light mb-0">
                    ${email}
                  </div>
                  <p class="text-muted small mt-3 mb-0">请检查收件箱查看邮件内容</p>
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
        } else {
          throw new Error(response.message || '测试失败');
        }
      })
      .catch(error => {
        console.error('测试邮件配置错误:', error);
        app.showToast('测试失败', error.message, 'danger');
      })
      .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      });
  }
  
  // 公开方法
  return {
    loadMailConfig,
    saveMailConfig,
    testMailConfig
  };
})();

// 将模块导出到全局作用域
window.EmailModule = EmailModule; 