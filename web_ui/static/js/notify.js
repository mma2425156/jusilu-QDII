/**
 * 通知渠道配置模块
 * 管理多渠道配置：钉钉/飞书/企业微信/Telegram/PushPlus/Server酱/Bark/iGot/Webhook
 */

const NotifyModule = (function() {
  'use strict';

  // 当前正在配置的渠道
  let currentChannel = null;

  // 渠道配置表单字段定义
  const CHANNEL_FIELDS = {
    email: [
      { key: 'smtp_server', label: 'SMTP 服务器', type: 'text', placeholder: 'smtp.qq.com', required: true },
      { key: 'smtp_port', label: 'SMTP 端口', type: 'number', placeholder: '465', default: '465', required: true },
      { key: 'username', label: '邮箱账号', type: 'email', placeholder: 'your@email.com', required: true },
      { key: 'password', label: '密码/授权码', type: 'password', placeholder: '邮箱密码或授权码', required: true },
      { key: 'sender_email', label: '发件人地址', type: 'email', placeholder: 'your@email.com', required: true },
      { key: 'use_ssl', label: '使用 SSL', type: 'checkbox', default: true },
    ],
    dingtalk: [
      { key: 'token', label: 'Robot Token', type: 'text', placeholder: '钉钉机器人的 access_token', required: true },
      { key: 'secret', label: '加签密钥（可选）', type: 'text', placeholder: '密钥，用于加签模式' },
    ],
    feishu: [
      { key: 'token', label: '机器人 Token', type: 'text', placeholder: '飞书机器人 webhook 中的 token', required: true },
      { key: 'secret', label: '加签密钥（可选）', type: 'text', placeholder: '用于签名校验' },
    ],
    wecom: [
      { key: 'corp_id', label: '企业 ID', type: 'text', placeholder: '企业微信的企业 ID', required: true },
      { key: 'agent_id', label: '应用 AgentId', type: 'text', placeholder: '应用的 AgentId', required: true },
      { key: 'corp_secret', label: '应用 Secret', type: 'text', placeholder: '应用的 Secret', required: true },
    ],
    telegram: [
      { key: 'token', label: 'Bot Token', type: 'text', placeholder: '从 @BotFather 获取的 Token', required: true },
      { key: 'chat_id', label: 'Chat ID', type: 'text', placeholder: '接收消息的 Chat ID', required: true },
    ],
    pushplus: [
      { key: 'token', label: 'PushPlus Token', type: 'text', placeholder: '从 pushplus.plus 获取的 Token', required: true },
    ],
    serverchan: [
      { key: 'sckey', label: 'ServerChan SCKEY', type: 'text', placeholder: 'SCT 开头（Turbo）或 SCU 开头（旧版）', required: true },
    ],
    bark: [
      { key: 'key', label: 'Bark Key', type: 'text', placeholder: 'Bark 服务端 URL 或 Key', required: true },
    ],
    igot: [
      { key: 'key', label: 'iGot Key', type: 'text', placeholder: 'iGot 的 tokey', required: true },
    ],
    webhook: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'url', placeholder: 'https://your-webhook-url.com/notify', required: true },
    ],
  };

  const CHANNEL_ICONS = {
    email: 'fa-envelope',
    dingtalk: 'fa-comment-dots',
    feishu: 'fa-paper-plane',
    wecom: 'fa-weixin',
    telegram: 'fa-telegram',
    pushplus: 'fa-mobile-alt',
    serverchan: 'fa-bell',
    bark: 'fa-mobile-alt',
    igot: 'fa-bell',
    webhook: 'fa-link',
  };

  // ──────────────────────────────────────────
  // 初始化
  // ──────────────────────────────────────────
  function init() {
    loadChannels();
    bindEvents();
  }

  function bindEvents() {
    // 设置按钮
    const settingsBtn = document.getElementById('settingsBtn');
    if (settingsBtn) {
      settingsBtn.addEventListener('click', loadChannels);
    }

    // 保存渠道按钮
    const saveBtn = document.getElementById('saveChannelBtn');
    if (saveBtn) {
      saveBtn.addEventListener('click', saveCurrentChannel);
    }

    // 测试渠道按钮
    const testBtn = document.getElementById('testChannelBtn');
    if (testBtn) {
      testBtn.addEventListener('click', testCurrentChannel);
    }
  }

  // ──────────────────────────────────────────
  // 加载渠道列表
  // ──────────────────────────────────────────
  function loadChannels() {
    fetch('/api/notify/channels')
      .then(function(r) { return r.json(); })
      .then(function(resp) {
        if (resp.status === 'success') {
          renderChannelList(resp.channels);
        }
      })
      .catch(function(e) { console.error('加载渠道失败:', e); });
  }

  function renderChannelList(channels) {
    const list = document.getElementById('channelList');
    if (!list) return;

    if (!channels || channels.length === 0) {
      list.innerHTML = '<div class="text-muted text-center py-3">暂无可用渠道</div>';
      return;
    }

    let html = '';
    channels.forEach(function(ch) {
      const icon = CHANNEL_ICONS[ch.id] || 'fa-bell';
      const statusBadge = ch.is_active
        ? '<span class="badge bg-success ms-2">已启用</span>'
        : '<span class="badge bg-secondary ms-2">未启用</span>';
      const configured = ch.configured
        ? '<span class="badge bg-info ms-1">已配置</span>'
        : '<span class="badge bg-warning text-dark ms-1">未配置</span>';

      html += '<div class="channel-item d-flex align-items-center justify-content-between p-3 rounded mb-2"' +
        ' data-channel="' + ch.id + '" style="cursor:pointer; background:var(--bs-body-bg); border:1px solid var(--bs-border-color);">' +
        '<div class="d-flex align-items-center gap-3">' +
        '<i class="fas ' + icon + ' fa-lg" style="width:24px; text-align:center;"></i>' +
        '<div>' +
        '<div class="fw-medium">' + ch.name + '</div>' +
        '<div class="small text-muted">' + (ch.is_active ? '已启用' : '已禁用') + configured + '</div>' +
        '</div></div>' +
        '<div class="form-check form-switch">' +
        '<input class="form-check-input" type="checkbox" role="switch"' +
        (ch.is_active ? ' checked' : '') + ' data-channel-toggle="' + ch.id + '">' +
        '</div></div>';
    });

    list.innerHTML = html;

    // 绑定点击事件（打开配置面板）
    list.querySelectorAll('.channel-item').forEach(function(item) {
      item.addEventListener('click', function(e) {
        if (e.target.classList.contains('form-check-input')) return;
        openChannelConfig(item.dataset.channel);
      });
    });

    // 绑定开关事件
    list.querySelectorAll('[data-channel-toggle]').forEach(function(toggle) {
      toggle.addEventListener('change', function(e) {
        e.stopPropagation();
        toggleChannel(toggle.dataset.channelToggle, toggle.checked);
      });
    });
  }

  // ──────────────────────────────────────────
  // 打开渠道配置面板
  // ──────────────────────────────────────────
  function openChannelConfig(channelId) {
    currentChannel = channelId;

    fetch('/api/notify/channels/' + channelId)
      .then(function(r) { return r.json(); })
      .then(function(resp) {
        if (resp.status === 'success') {
          renderChannelForm(resp.channel);
          openConfigModal(channelId);
        }
      })
      .catch(function(e) { console.error('加载渠道配置失败:', e); });
  }

  function renderChannelForm(channel) {
    const formContainer = document.getElementById('channelFormContainer');
    if (!formContainer) return;

    const fields = CHANNEL_FIELDS[channel.channel] || [];
    const config = channel.config || {};

    let html = '<input type="hidden" id="channelIdInput" value="' + channel.channel + '">';
    html += '<p class="text-muted small mb-3">填写完配置后点击「保存」，然后点击「测试」验证是否可用。</p>';

    fields.forEach(function(field) {
      var value = config[field.key] !== undefined ? config[field.key] : (field.default || '');
      var required = field.required ? ' required' : '';

      if (field.type === 'checkbox') {
        html += '<div class="mb-3 form-check">' +
          '<input type="checkbox" class="form-check-input" id="ch_' + field.key + '"' +
          (value ? ' checked' : '') + '>' +
          '<label class="form-check-label" for="ch_' + field.key + '">' + field.label + '</label>' +
          '</div>';
      } else {
        html += '<div class="mb-3">' +
          '<label for="ch_' + field.key + '" class="form-label">' + field.label + '</label>' +
          '<input type="' + field.type + '" class="form-control" id="ch_' + field.key + '"' +
          ' placeholder="' + (field.placeholder || '') + '"' +
          ' value="' + (field.type === 'password' && value ? '' : value) + '"' + required + '>' +
          '</div>';
      }
    });

    // 帮助提示
    html += getChannelHelp(channel.channel);
    html += '<div id="channelSaveStatus" class="mt-2 small"></div>';

    formContainer.innerHTML = html;
  }

  function getChannelHelp(channel) {
    const helps = {
      email: '<div class="alert alert-info mt-3 small">QQ邮箱示例：SMTP服务器 <b>smtp.qq.com</b>，端口 <b>465</b>，密码用<b>授权码</b>而非登录密码。</div>',
      dingtalk: '<div class="alert alert-info mt-3 small">钉钉群 → 群设置 → 智能群助手 → 添加机器人 → 选择「加签」模式，复制 Token 和 Secret。</div>',
      feishu: '<div class="alert alert-info mt-3 small">飞书群 → 群设置 → 群机器人 → 添加机器人 → 自定义机器人，复制 Token 和 Secret。</div>',
      pushplus: '<div class="alert alert-info mt-3 small">访问 <a href="http://www.pushplus.plus" target="_blank">pushplus.plus</a> 登录后复制你的 Token，免费使用。</div>',
      serverchan: '<div class="alert alert-info mt-3 small">访问 <a href="https://sct.ftqq.com" target="_blank">sct.ftqq.com</a> 登录后复制 SCKEY（Turbo 版用 SCT 开头）。</div>',
      bark: '<div class="alert alert-info mt-3 small">安装 Bark iOS App，复制服务端地址或 Key 填入。</div>',
      wecom: '<div class="alert alert-info mt-3 small">企业微信后台 → 应用管理 → 创建应用 → 复制 AgentId 和 Secret，再到「我的企业」复制 CorpId。</div>',
      telegram: '<div class="alert alert-info mt-3 small">1. 在 Telegram 找 @BotFather 创建 Bot 获取 Token<br>2. 找 @userinfobot 或 @getidsbot 获取你的 Chat ID</div>',
    };
    return helps[channel] || '';
  }

  function openConfigModal(channelId) {
    const modal = new bootstrap.Modal(document.getElementById('channelConfigModal'));
    const title = document.getElementById('channelConfigModalLabel');
    if (title) {
      const names = {email:'邮件SMTP',dingtalk:'钉钉机器人',feishu:'飞书机器人',
        wecom:'企业微信',telegram:'Telegram',pushplus:'PushPlus',
        serverchan:'Server酱',bark:'Bark',igot:'iGot',webhook:'自定义Webhook'};
      title.innerHTML = '<i class="fas fa-bell me-2"></i>配置 ' + (names[channelId] || channelId);
    }
    modal.show();
  }

  // ──────────────────────────────────────────
  // 保存渠道配置
  // ──────────────────────────────────────────
  function saveCurrentChannel() {
    if (!currentChannel) return;

    var channelIdInput = document.getElementById('channelIdInput');
    var chId = channelIdInput ? channelIdInput.value : currentChannel;
    var fields = CHANNEL_FIELDS[chId] || [];
    var config = {};
    var isActive = false;

    fields.forEach(function(field) {
      var el = document.getElementById('ch_' + field.key);
      if (!el) return;
      if (field.type === 'checkbox') {
        config[field.key] = el.checked;
      } else {
        var val = el.value.trim();
        if (val) config[field.key] = val;
      }
    });

    // 获取启用状态（从列表中的开关）
    var toggle = document.querySelector('[data-channel-toggle="' + chId + '"]');
    isActive = toggle ? toggle.checked : false;

    var saveBtn = document.getElementById('saveChannelBtn');
    var origText = saveBtn ? saveBtn.innerHTML : '';
    if (saveBtn) { saveBtn.disabled = true; saveBtn.innerHTML = '保存中...'; }

    fetch('/api/notify/channels/' + chId, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({}, config, { is_active: isActive })),
    })
    .then(function(r) { return r.json(); })
    .then(function(resp) {
      var status = document.getElementById('channelSaveStatus');
      if (resp.status === 'success') {
        status.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> ' + resp.message + '</span>';
        loadChannels();
      } else {
        status.innerHTML = '<span class="text-danger"><i class="fas fa-times-circle"></i> ' + resp.message + '</span>';
      }
      setTimeout(function() { if (status) status.innerHTML = ''; }, 4000);
    })
    .catch(function(e) {
      var status = document.getElementById('channelSaveStatus');
      if (status) status.innerHTML = '<span class="text-danger">保存失败: ' + e + '</span>';
    })
    .finally(function() {
      if (saveBtn) { saveBtn.disabled = false; saveBtn.innerHTML = origText; }
    });
  }

  // ──────────────────────────────────────────
  // 测试渠道
  // ──────────────────────────────────────────
  function testCurrentChannel() {
    if (!currentChannel) return;

    var testBtn = document.getElementById('testChannelBtn');
    var origText = testBtn ? testBtn.innerHTML : '';
    if (testBtn) { testBtn.disabled = true; testBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>测试中...'; }

    // 先保存配置再测试
    saveCurrentChannel();

    setTimeout(function() {
      var recipients = [];
      var emailInput = document.getElementById('ch_username');
      if (emailInput && emailInput.value) recipients.push(emailInput.value);

      fetch('/api/notify/channels/' + currentChannel + '/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recipients: recipients }),
      })
      .then(function(r) { return r.json(); })
      .then(function(resp) {
        var status = document.getElementById('channelSaveStatus');
        if (resp.status === 'success' || resp.success) {
          var msg = resp.message || resp.Message || '测试消息发送成功';
          if (status) status.innerHTML = '<span class="text-success"><i class="fas fa-check-circle"></i> ' + msg + '</span>';
        } else {
          var errMsg = resp.message || resp.error || '发送失败';
          if (status) status.innerHTML = '<span class="text-danger"><i class="fas fa-times-circle"></i> ' + errMsg + '</span>';
        }
        setTimeout(function() { if (status) status.innerHTML = ''; }, 6000);
      })
      .catch(function(e) {
        var status = document.getElementById('channelSaveStatus');
        if (status) status.innerHTML = '<span class="text-danger">测试失败: ' + e + '</span>';
      })
      .finally(function() {
        if (testBtn) { testBtn.disabled = false; testBtn.innerHTML = origText; }
      });
    }, 500);
  }

  // ──────────────────────────────────────────
  // 启用/停用渠道
  // ──────────────────────────────────────────
  function toggleChannel(channelId, isActive) {
    fetch('/api/notify/channels/' + channelId + '/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    .catch(function() {});

    fetch('/api/notify/channels/' + channelId, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: isActive }),
    })
    .then(function(r) { return r.json(); })
    .then(function(resp) {
      if (resp.status === 'success') {
        loadChannels();
      }
    })
    .catch(function(e) { console.error('切换渠道状态失败:', e); });
  }

  return { init, loadChannels, openChannelConfig };
})();

document.addEventListener('DOMContentLoaded', NotifyModule.init);
