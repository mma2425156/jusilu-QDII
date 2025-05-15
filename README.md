# 🚀 QDII基金数据助手

## 🌟 项目简介
一个简单易用的QDII基金数据工具，帮助您轻松获取和分析海外基金信息，无需编程基础也能快速上手！

主要功能：
- 一键获取最新QDII基金数据
- 智能筛选优质基金
- 直观的网页界面操作

## 🛠️ 超详细安装指南

### 第1步：安装Python
1. 访问[Python官网](https://www.python.org/downloads/)
2. 下载最新版Python(3.10+)
3. 安装时务必勾选"Add Python to PATH"选项
   ![Python安装截图](https://example.com/python_install.png)

### 第2步：获取项目代码
1. 下载项目压缩包（右上角"Code"→"Download ZIP"）
2. 解压到任意文件夹
   *或使用Git（高级用户）：*
   ```bash
   git clone https://github.com/mma2425156/jusilu-QDII
   cd jisilu
   ```

### 第3步：安装方式选择

#### 方案A：虚拟环境安装（推荐）
1. 创建虚拟环境：
   ```bash
   python -m venv venv
   ```
2. 激活虚拟环境：
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Mac/Linux:
     ```bash
     source venv/bin/activate
     ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 安装浏览器驱动：
   ```bash
   playwright install
   ```

#### 方案B：一键安装（适合新手）
- **Windows用户**：
  1. 双击运行 `install_deps.bat`
  2. 脚本会自动检测并使用虚拟环境中的Python(如果存在venv文件夹)
  3. 如果没有虚拟环境，会使用系统Python并显示警告
  4. 等待安装完成（约3-5分钟）
  
- **Mac/Linux用户**：
  1. 右键点击 `install_deps.py` → 选择"打开方式" → Python
  2. 或终端运行：
     ```bash
     python scripts/install_deps.py
     ```

### 第4步：配置环境变量

#### 1. 创建配置文件
```bash
# Windows
ren .env.example .env

# Mac/Linux 
mv .env.example .env
```

#### 2. 详细配置说明
用文本编辑器打开`.env`文件，按以下分类配置：

##### 📧 邮件通知设置
```ini
# 发件人邮箱地址（必须支持SMTP服务）
MAIL_SENDER=your_email@example.com
# 发件人显示名称
MAIL_SENDER_NAME=QDII基金监控系统
# SMTP服务器地址
SMTP_SERVER=smtp.example.com
# SMTP端口（SSL通常为465/587）
SMTP_PORT=587
# SMTP登录用户名（通常是邮箱地址）
SMTP_USERNAME=your_email@example.com
# SMTP登录密码（可能是邮箱密码或专用应用密码）
SMTP_PASSWORD=your_password
# 是否使用SSL加密（true/false）
SMTP_USE_SSL=true
```

##### 🔍 数据筛选设置
```ini
# 溢价率默认筛选阈值（0-10）
PREMIUM_THRESHOLD=5.0
# 默认申购状态筛选（all/open/limited/closed）
DEFAULT_STATUS_FILTER=open
# 数据刷新间隔（秒，最小30）
REFRESH_INTERVAL=60
```

##### 🗃️ 数据库配置
```ini
# 数据库文件路径（SQLite）
DB_PATH=web_ui/config.db
# 数据库备份保留天数
DB_BACKUP_DAYS=7
```

##### 🌐 Web服务设置
```ini
# 服务监听端口
FLASK_PORT=8866
# 服务监听地址（0.0.0.0表示允许外部访问）
FLASK_HOST=0.0.0.0
# 调试模式（开发环境设为true，生产环境必须设为false）
FLASK_DEBUG=false
# 密钥（用于会话加密，建议修改为随机字符串）
SECRET_KEY=your_secret_key_here
```

#### 3. 配置示例
```ini
# 邮件配置示例（QQ邮箱）
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USERNAME=123456@qq.com
SMTP_PASSWORD=xxxxxxxxxxxxxx  # 需使用QQ邮箱授权码
SMTP_USE_SSL=true

# 筛选设置示例
PREMIUM_THRESHOLD=3.5  # 筛选溢价率>3.5%的基金
DEFAULT_STATUS_FILTER=open  # 默认只显示开放申购的基金
```

#### 4. 注意事项
1. 所有密码类配置**不要**包含`#`和空格等特殊字符
2. 修改配置后需要**重启服务**才能生效
3. 生产环境务必设置`FLASK_DEBUG=false`
4. 建议定期备份`.env`文件

### 第5步：启动程序
1. 双击 `run.bat` (Windows) 或运行：
   ```bash
   python main.py
   ```
2. 自动打开浏览器访问：http://localhost:8866

## 🖥️ 使用教程

### 基础操作
1. 在网页中设置筛选条件：
   - 溢价率范围（推荐0-10%）
   - 申购状态（开放/限购）
2. 点击"刷新数据"获取最新结果
3. 点击基金名称查看详情

![操作界面截图](https://example.com/ui_demo.png)

## ❓ 常见问题

### 安装问题
1. **报错"python不是内部命令"**：
   - 重新安装Python并勾选"Add to PATH"
2. **脚本运行闪退**：
   - 右键以管理员身份运行
   - 或查看 `error.log` 文件

### 使用问题
1. **数据不更新？**
   - 确保网络连接正常
   - 等待30秒后重试（有访问频率限制）
2. **浏览器打不开？**
   - 手动访问 http://localhost:8866


## 🔧 高级设置
如需自定义配置，请修改 `.env` 文件：
```
# 邮件通知设置
EMAIL=your@email.com
# 筛选阈值
PREMIUM_THRESHOLD=5.0
```


