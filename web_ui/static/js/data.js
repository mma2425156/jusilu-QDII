/**
 * 集思录QDII数据助手 - 数据处理模块（重构版）
 * 支持溢价率变化对比指标
 */

const DataModule = (function() {
  'use strict';

  let refreshCooldown = 0;
  let refreshCooldownInterval;

  function init() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', refreshData);
    }

    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
      filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        applyFilters();
      });
    }

    // 跳转按钮：邮件设置 → 定时任务
    const goToTaskBtn = document.getElementById('goToTaskConfig');
    if (goToTaskBtn) {
      goToTaskBtn.addEventListener('click', function() {
        const mailModal = bootstrap.Modal.getInstance(document.getElementById('mailConfigModal'));
        if (mailModal) mailModal.hide();
        setTimeout(function() {
          const taskModal = new bootstrap.Modal(document.getElementById('taskConfigModal'));
          taskModal.show();
        }, 300);
      });
    }
  }

  function refreshData() {
    if (refreshCooldown > 0) return;

    const btn = document.getElementById('refreshBtn');
    const spinner = document.getElementById('refreshSpinner');
    const text = document.getElementById('refreshText');
    if (!btn || !spinner || !text) return;

    btn.disabled = true;
    text.textContent = '数据刷新中...';
    spinner.classList.remove('d-none');

    const statusAlert = document.getElementById('refreshStatus');
    const statusMessage = document.getElementById('statusMessage');
    const statusOutput = document.getElementById('statusOutput');

    if (statusAlert) {
      statusAlert.classList.remove('d-none', 'alert-danger');
      statusAlert.classList.add('alert-info');
    }
    if (statusMessage) statusMessage.innerHTML = '<strong>正在刷新数据...</strong>';
    if (statusOutput) statusOutput.textContent = '准备开始抓取数据...';

    // SSE 方式实时获取进度
    const eventSource = new EventSource('/api/refresh-status');
    let lastEventTime = Date.now();

    const checkInterval = setInterval(function() {
      if (Date.now() - lastEventTime > 15000) {
        eventSource.close();
        clearInterval(checkInterval);
        if (statusMessage) statusMessage.innerHTML = '<strong class="text-danger">连接超时</strong>';
        resetButton();
      }
    }, 3000);

    eventSource.onmessage = function(event) {
      lastEventTime = Date.now();
      try {
        const data = JSON.parse(event.data);
        if (data.status === 'completed') {
          eventSource.close();
          clearInterval(checkInterval);
          if (statusMessage) statusMessage.innerHTML = '<strong class="text-success">刷新成功！</strong>';
          if (statusOutput) statusOutput.textContent = data.message;
          // 自动刷新页面
          setTimeout(function() { window.location.reload(); }, 1500);
        } else if (data.status === 'error') {
          eventSource.close();
          clearInterval(checkInterval);
          if (statusMessage) statusMessage.innerHTML = '<strong class="text-danger">刷新失败</strong>';
          if (statusOutput) statusOutput.textContent = data.message;
          startCooldown();
        } else {
          if (statusOutput) {
            const lines = statusOutput.textContent.split('\n');
            lines.push(data.message);
            if (lines.length > 10) lines.shift();
            statusOutput.textContent = lines.join('\n');
            statusOutput.scrollTop = statusOutput.scrollHeight;
          }
        }
      } catch(e) {}
    };

    eventSource.onerror = function() {
      eventSource.close();
      clearInterval(checkInterval);
      if (statusMessage) statusMessage.innerHTML = '<strong class="text-danger">连接错误</strong>';
      startCooldown();
    };
  }

  function applyFilters() {
    // 表单提交即可，页面会刷新
    document.getElementById('filterForm').submit();
  }

  function updateTableData(data) {
    const tbody = document.getElementById('dataTableBody');
    if (!tbody) return;

    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">暂无数据</td></tr>';
      return;
    }

    let html = '';
    data.forEach(function(item) {
      const premium = item.premium_today;
      const change = item.change;
      const status = item.status || '';

      // 溢价率颜色
      let premiumColor = 'text-success';
      let premiumText = 'N/A';
      if (premium !== null && premium !== undefined) {
        premiumText = premium.toFixed(2) + '%';
        if (premium >= 5) premiumColor = 'text-danger';
        else if (premium >= 3) premiumColor = 'text-warning';
      }

      // 变化颜色
      let changeColor = 'text-muted';
      let changeIcon = '';
      let changeText = '-';
      if (change !== null && change !== undefined) {
        if (change > 0) { changeColor = 'text-danger'; changeIcon = '↑'; }
        else if (change < 0) { changeColor = 'text-success'; changeIcon = '↓'; }
        changeText = changeIcon + change.toFixed(2) + '%';
      }

      // 状态徽章
      let badgeClass = 'bg-secondary';
      if (status.includes('开放')) badgeClass = 'bg-success';
      else if (status.includes('限')) badgeClass = 'bg-warning text-dark';
      else if (status.includes('暂停')) badgeClass = 'bg-danger';

      html += '<tr>' +
        '<td>' + (item.source || '') + '</td>' +
        '<td>' + (item.code || item.fund_code || '') + '</td>' +
        '<td>' + (item.name || item.fund_name || '') + '</td>' +
        '<td class="fw-bold ' + premiumColor + '">' + premiumText + '</td>' +
        '<td class="fw-bold ' + changeColor + '">' + changeText + '</td>' +
        '<td><span class="badge ' + badgeClass + '">' + status + '</span></td>' +
        '</tr>';
    });

    tbody.innerHTML = html;
  }

  function resetButton() {
    const btn = document.getElementById('refreshBtn');
    const spinner = document.getElementById('refreshSpinner');
    const text = document.getElementById('refreshText');
    if (btn) btn.disabled = false;
    if (text) text.textContent = '刷新数据';
    if (spinner) spinner.classList.add('d-none');
  }

  function startCooldown() {
    refreshCooldown = 30;
    resetButton();
    const text = document.getElementById('refreshText');
    if (text) text.textContent = '冷却中 (' + refreshCooldown + 's)';
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.disabled = true;

    refreshCooldownInterval = setInterval(function() {
      refreshCooldown--;
      if (text) text.textContent = '冷却中 (' + refreshCooldown + 's)';
      if (refreshCooldown <= 0) {
        clearInterval(refreshCooldownInterval);
        refreshCooldown = 0;
        resetButton();
      }
    }, 1000);
  }

  return { init, refreshData, applyFilters, updateTableData };
})();

document.addEventListener('DOMContentLoaded', DataModule.init);
