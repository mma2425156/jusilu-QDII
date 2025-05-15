/**
 * 集思录QDII数据助手 - 数据处理模块
 */

const DataModule = (function() {
  'use strict';
  
  // 私有变量
  let refreshCooldown = 0;
  let refreshCooldownInterval;
  
  /**
   * 初始化
   */
  function init() {
    // 绑定刷新数据事件
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', refreshData);
    }
    
    // 绑定筛选表单事件
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
      filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        applyFilters();
      });
    }
  }
  
  /**
   * 刷新数据
   */
  function refreshData() {
    if (refreshCooldown > 0) return;
    
    const btn = document.getElementById('refreshBtn');
    const spinner = document.getElementById('refreshSpinner');
    const text = document.getElementById('refreshText');
    
    if (!btn || !spinner || !text) return;
    
    btn.disabled = true;
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-secondary');
    text.textContent = '数据刷新中...';
    spinner.classList.remove('d-none');
    
    // 设置冷却时间
    refreshCooldown = 30;
    
    // 获取筛选参数
    const parameters = {
      premium_min: document.getElementById('premium_min').value,
      status_filter: document.getElementById('status_filter').value
    };
    
    // 发送刷新请求
    API.refreshData(parameters)
      .then(response => {
        // 显示刷新状态
        const statusAlert = document.getElementById('refreshStatus');
        const statusMessage = document.getElementById('statusMessage');
        const statusOutput = document.getElementById('statusOutput');
        
        if (statusAlert && statusMessage && statusOutput) {
          statusAlert.classList.remove('d-none', 'alert-danger');
          statusAlert.classList.add('alert-info');
          statusMessage.innerHTML = `<strong>${response.message}</strong> - ${response.timestamp}`;
          statusOutput.textContent = response.output || '无详细输出';
        }
        
        // 显示成功反馈
        app.showToast('刷新成功', `数据已成功更新，发现 ${response.data.length} 条符合条件的数据`, 'success');
        
        // 更新表格数据
        if (response.status === 'success') {
          updateTableData(response.data);
        }
        
        // 启动倒计时
        if (text) text.textContent = `请等待 ${refreshCooldown}秒`;
        refreshCooldownInterval = setInterval(updateRefreshButtonState, 1000);
      })
      .catch(error => {
        console.error('刷新数据错误:', error);
        
        // 显示错误状态
        const statusAlert = document.getElementById('refreshStatus');
        const statusMessage = document.getElementById('statusMessage');
        const statusOutput = document.getElementById('statusOutput');
        
        if (statusAlert && statusMessage && statusOutput) {
          statusAlert.classList.remove('d-none', 'alert-info');
          statusAlert.classList.add('alert-danger');
          statusMessage.innerHTML = `<strong>刷新失败</strong> - ${new Date().toLocaleString()}`;
          statusOutput.textContent = error.message || '未知错误';
        }
        
        // 显示错误反馈
        app.showToast('刷新失败', error.message, 'danger');
        
        // 启动倒计时
        if (text) text.textContent = `请等待 ${refreshCooldown}秒`;
        refreshCooldownInterval = setInterval(updateRefreshButtonState, 1000);
      });
  }
  
  /**
   * 更新刷新按钮状态
   */
  function updateRefreshButtonState() {
    const btn = document.getElementById('refreshBtn');
    const text = document.getElementById('refreshText');
    const spinner = document.getElementById('refreshSpinner');
    
    if (!btn || !text || !spinner) {
      clearInterval(refreshCooldownInterval);
      return;
    }
    
    if (refreshCooldown > 0) {
      btn.disabled = true;
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-secondary');
      text.textContent = `请等待 ${refreshCooldown}秒`;
      refreshCooldown--;
    } else {
      btn.disabled = false;
      btn.classList.remove('btn-secondary');
      btn.classList.add('btn-primary');
      text.textContent = '刷新数据';
      spinner.classList.add('d-none');
      clearInterval(refreshCooldownInterval);
    }
  }
  
  /**
   * 应用筛选条件
   */
  function applyFilters() {
    const premiumMin = document.getElementById('premium_min').value;
    const statusFilter = document.getElementById('status_filter').value;
    
    // 显示加载状态
    const tableBody = document.getElementById('dataTableBody');
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-2 text-secondary">正在应用筛选条件...</p>
          </td>
        </tr>
      `;
    }
    
    // 发送筛选请求
    fetch('/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        premium_min: premiumMin,
        status_filter: statusFilter
      })
    })
    .then(response => response.text())
    .then(html => {
      // 使用新HTML更新页面
      const parser = new DOMParser();
      const newDoc = parser.parseFromString(html, 'text/html');
      const newTableBody = newDoc.getElementById('dataTableBody');
      
      if (tableBody && newTableBody) {
        tableBody.innerHTML = newTableBody.innerHTML;
      }
      
      // 显示成功消息
      app.showToast('筛选完成', '数据已按条件筛选显示', 'success');
    })
    .catch(error => {
      console.error('筛选错误:', error);
      if (tableBody) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center py-4 text-danger">
              <i class="fas fa-exclamation-circle fa-2x mb-3"></i>
              <p>筛选失败，请稍后再试</p>
            </td>
          </tr>
        `;
      }
      
      // 显示错误消息
      app.showToast('筛选失败', '请检查筛选条件后重试', 'danger');
    });
  }
  
  /**
   * 更新表格数据
   */
  function updateTableData(data) {
    const tableBody = document.getElementById('dataTableBody');
    if (!tableBody) return;
    
    let html = '';
    
    data.forEach(item => {
      html += `
        <tr class="slide-in-up">
          <td>${item.来源}</td>
          <td>${item.代码}</td>
          <td>${item.名称}</td>
          <td>${item['T-1溢价率']}</td>
          <td>
            <span class="badge ${getStatusBadgeClass(item.申购状态)}">
              ${item.申购状态}
            </span>
          </td>
        </tr>
      `;
    });
    
    tableBody.innerHTML = html;
  }
  
  /**
   * 获取状态徽章样式类
   */
  function getStatusBadgeClass(status) {
    if (status === '开放申购') return 'badge-success';
    if (status === '限量申购') return 'badge-warning';
    if (status === '暂停申购') return 'badge-danger';
    return 'badge-secondary';
  }
  
  // 导出公共方法
  return {
    init,
    refreshData,
    applyFilters
  };
})();

// 将模块导出到全局作用域
window.DataModule = DataModule;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', DataModule.init); 