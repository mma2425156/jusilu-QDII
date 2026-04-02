# QDII 基金监控系统 - 部署文档

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp config/.env.example .env

# 编辑 .env，填入实际配置（参考下方各渠道配置说明）
```

### 3. 启动

```bash
# 启动 Web 服务（开发）
python main.py

# 启动 Web 服务（生产）
gunicorn --bind 0.0.0.0:8866 --workers 4 --threads 2 "apps.app_factory:create_app"

# 仅运行爬虫（手动抓取一次）
python main.py --crawl

# 抓取 + 保存历史快照
python main.py --snapshot
```

### 4. Docker 部署

```bash
docker-compose up -d
# 服务运行在 http://localhost:8866
```

---

## 各通知渠道配置说明

### 邮件 SMTP（最通用）

```env
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USERNAME=123456@qq.com
SMTP_PASSWORD=xxxx  # QQ邮箱使用「授权码」而非登录密码
MAIL_SENDER=123456@qq.com
SMTP_USE_SSL=true
```

> QQ 邮箱授权码：QQ 邮箱网页 → 设置 → 账户 → POP3/SMTP服务 → 生成授权码

---

### 钉钉机器人

1. 群聊 → 群设置 → 智能群助手 → 添加机器人
2. 选择「自定义机器人」
3. 安全设置选「加签」，复制 Token 和 Secret

```env
DINGTALK_TOKEN=你的token
DINGTALK_SECRET=你的secret
```

---

### 飞书机器人

1. 群聊 → 设置 → 群机器人 → 添加机器人 → 自定义机器人
2. 填写机器人名称，复制 Webhook URL 中的 token 部分

```env
FEISHU_TOKEN=你的token
FEISHU_SECRET=你的secret（可选）
```

---

### 企业微信

1. 企业微信后台 → 应用管理 → 创建应用
2. 复制 AgentId 和 Secret
3. 「我的企业」→ 企业信息 → 复制 CorpId

```env
WECOM_CORP_ID=wwxxxx
WECOM_AGENT_ID=1000001
WECOM_CORP_SECRET=你的secret
```

---

### Telegram

1. Telegram 搜索 `@BotFather` → `/newbot` → 创建机器人，复制 Token
2. 搜索 `@userinfobot` 或 `@getidsbot` → 获取你的 Chat ID

```env
TELEGRAM_TOKEN=123456:ABC-xxxx
TELEGRAM_CHAT_ID=你的chat_id
```

---

### PushPlus（微信推送，无需服务器）

1. 访问 [pushplus.plus](http://www.pushplus.plus)
2. 登录后复制 Token

```env
PUSHPLUS_TOKEN=你的token
```

---

### Server酱（微信推送）

1. 访问 [sct.ftqq.com](https://sct.ftqq.com)
2. 登录后复制 SCKEY（Turbo 版用 SCT 开头）

```env
SERVERCHAN_SCKEY=SCTxxxx（Turbo）或 SCUxxxx（旧版）
```

---

### Bark（iOS 推送）

1. iOS App Store 安装 Bark
2. 打开 Bark，复制服务端地址或 Key

```env
BARK_KEY=你的key或完整URL
```

---

## 定时任务使用指南

### Cron 表达式示例

| 表达式 | 含义 |
|--------|------|
| `0 8 * * *` | 每天早上 8:00 |
| `0 9 * * 1-5` | 工作日早上 9:00 |
| `30 22 * * *` | 每天晚上 22:30 |
| `0 */4 * * *` | 每 4 小时一次 |

### WebUI 配置步骤

1. 点击顶部「**通知设置**」→ 选择渠道 → 填配置 → 保存 → 测试
2. 点击顶部「**刷新数据**」→ 等待抓取完成
3. 在定时任务中配置筛选条件（溢价率下限、申购状态）和收件人

---

## 目录结构

```
jusilu-QDII/
├── config/               # 配置层
│   ├── settings.py      # 环境变量加载
│   └── .env.example     # 环境变量模板
├── models/              # 数据模型
│   ├── task.py          # 定时任务
│   ├── fund_snapshot.py # 历史快照
│   ├── notify_channel.py # 通知渠道
│   └── notify_template.py # 通知模板
├── apps/
│   ├── spider/           # 爬虫模块
│   ├── notify/           # 多渠道通知
│   │   ├── sendNotify.py # 10+渠道发送
│   │   └── notification_service.py
│   ├── scheduler/        # APScheduler 调度
│   └── api/              # Flask API 路由
├── web_ui/
│   ├── templates/        # HTML 模板
│   └── static/js/        # 前端 JS
├── main.py               # 入口脚本
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 常见问题

**Q: 抓取失败，提示 Playwright 错误？**
```bash
playwright install chromium
```

**Q: 钉钉/飞书收不到消息？**
- 检查 Token 是否正确
- 钉钉加签模式需同时填 Secret
- 企业微信需确认应用可见范围包含自己

**Q: 如何查看详细日志？**
```bash
# 启动时指定日志文件
python main.py > logs/app.log 2>&1
```

**Q: 迁移旧架构的数据？**
旧 CSV 文件保留不动，新架构优先从 SQLite 快照读取。首次运行会自动初始化数据库表。
