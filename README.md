# 🚀 QDII基金数据助手

## 🌟 项目简介
一个简单易用的QDII基金数据工具，帮助您轻松获取和分析海外基金信息，无需编程基础也能快速上手！

主要功能：
- 一键获取最新QDII基金数据（溢价率、净值、申赎状态等）
- 智能筛选高溢价基金，支持历史快照对比
- 多渠道通知（钉钉、飞书、邮件等10种推送方式）
- 直观的网页界面操作，支持定时自动抓取

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

### 第4步：配置集思录登录（重要！）

集思录的溢价率数据需要登录才能查看。系统支持两种登录方式：

#### 方式一：导出 Cookie（推荐，稳定可靠）

1. **用 Chrome/Edge 登录集思录**
   - 打开浏览器，访问 https://www.jisilu.cn
   - 点击右上角"登录"，使用账号密码登录

2. **打开开发者工具**
   - 按 `F12` 或 `Ctrl+Shift+I`
   - 切换到 **Network（网络）** 标签页

3. **刷新页面触发请求**
   - 在地址栏回车刷新页面
   - 在 Network 中找到任意一条请求（URL 包含 `jisilu.cn`）
   - 点击该请求，在 **Request Headers** 中找到 `Cookie:` 字段

4. **复制 Cookie 内容**
   - 复制整个 `Cookie:` 后面的全部内容（很长，以分号分隔）
   - 形如：`kbzw__Session=xxxxx; uid=xxxxx; ...`

5. **写入 Cookie 文件**
   - 运行以下命令（会自动写入到 `qdii_tables/.jisilu_cookies.pkl`）：
   ```python
   import pickle
   from pathlib import Path

   # 替换下面 cookies 列表中的 value 为你复制的 Cookie 值
   cookies = [
       {'name': 'kbzw__Session', 'value': '这里填你复制的Cookie', 'domain': 'www.jisilu.cn', 'path': '/'},
   ]
   Path('qdii_tables/.jisilu_cookies.pkl').write_bytes(pickle.dumps(cookies))
   print('Cookie 写入成功')
   ```

   或者直接用浏览器插件（更简单）：
   - 安装 **EditThisCookie** 或 **Cookie Editor** 插件
   - 登录集思录后，点击插件图标
   - 导出全部 Cookie，保存为 JSON
   - 把 JSON 内容发给我，我帮你转成 pickle 格式

6. **验证 Cookie 有效**
   ```bash
   python main.py --crawl
   ```
   看到 "欧美市场 XX 条" 等日志即表示成功。

> **Cookie 有效期**：约 1 个月，过期后重新导出即可。

#### 方式二：填写用户名密码（备用）

> 注意：集思录可能会触发图形验证码，自动登录的成功率不稳定。
> 如果 Cookie 方式正常工作，建议优先使用方式一。

1. 编辑 `config/.env` 文件，取消注释并填写：
   ```ini
   JISILU_USERNAME=你的集思录用户名
   JISILU_PASSWORD=你的集思录密码
   ```

2. 运行 `python main.py --crawl` 测试。如果提示"登录失败"，请使用方式一导出 Cookie。

---

### 第5步：配置其他选项（如需要）

#### 📧 邮件通知（可选）
```ini
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USERNAME=你的邮箱
SMTP_PASSWORD=邮箱授权码（不是登录密码）
```
> QQ 邮箱授权码获取：QQ邮箱 → 设置 → 账户 → POP3/IMAP → 生成授权码

#### 💬 通知渠道（可选，任选一种）
- **钉钉机器人**：填 `DINGTALK_TOKEN` 和 `DINGTALK_SECRET`
- **飞书机器人**：填 `FEISHU_TOKEN` 和 `FEISHU_SECRET`
- **Telegram Bot**：填 `TELEGRAM_TOKEN` 和 `TELEGRAM_CHAT_ID`
- **企业微信**：填 `WECOM_CORP_ID`、`WECOM_AGENT_ID`、`WECOM_CORP_SECRET`
- **PushPlus**：填 `PUSHPLUS_TOKEN`
- **Server酱**：填 `SERVERCHAN_SCKEY`

#### 📊 数据筛选设置
```ini
# 溢价率下限（默认 3.5）
PREMIUM_THRESHOLD=3.5
# 申赎状态筛选（all/限/开放/暂停）
DEFAULT_STATUS_FILTER=all
```

### 第6步：启动程序
```bash
python main.py
```
- 直接运行：启动 Web 服务（访问 http://localhost:8866）
- `python main.py --crawl`：仅抓取数据并退出
- `python main.py --snapshot`：抓取数据并保存历史快照

## 🖥️ 使用教程

### 基础操作
1. 打开浏览器访问 http://localhost:8866
2. 设置溢价率下限（默认 3.5%，目前 QDII 多为折价状态，可设为负值如 -1%）
3. 选择申赎状态筛选条件
4. 点击"刷新数据"获取最新结果
5. 查看基金详情：溢价率、净值日期、申赎状态等

### 查看溢价率变化（需要多次抓取）
```bash
# 每天运行一次，保存历史快照
python main.py --snapshot
```
多次快照后，WebUI 会显示今日 vs 昨日的溢价率变化。

### 定时自动推送
在 WebUI 中创建定时任务，配置通知渠道和推送模板，系统会自动按设定时间抓取并推送。

## ❓ 常见问题

### 安装问题
1. **报错"python不是内部命令"**：
   - 重新安装Python并勾选"Add to PATH"
2. **playwright install 失败**：
   ```bash
   pip install playwright
   playwright install chromium
   ```

### 使用问题
1. **抓取数据为 0 条？**
   - 确认已配置集思录 Cookie 或用户名密码
   - 运行 `python main.py --crawl` 查看日志
   - Cookie 过期，重新导出
2. **数据不更新？**
   - 集思录有访问频率限制，等待 30 秒后重试
3. **浏览器打不开？**
   - 手动访问 http://localhost:8866

### 集思录登录问题
1. **Cookie 怎么获取？**
   - 见上方"第4步：配置集思录登录"的详细图解
2. **Cookie 多久过期？**
   - 通常 1 个月左右，过期后重新登录集思录并导出
3. **可以用账号密码登录吗？**
   - 可以，但集思录可能触发验证码，成功率不稳定
   - 建议优先使用 Cookie 方式


## 🔧 高级设置
