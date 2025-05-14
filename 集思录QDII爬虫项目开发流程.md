# 集思录QDII爬虫项目开发流程

## 1. 环境搭建与依赖安装

- 安装 Python 3。
- 创建并激活虚拟环境（推荐）：
  - Windows:
    ```
    python -m venv venv
    .\venv\Scripts\activate
    ```
  - macOS/Linux:
    ```
    python3 -m venv venv
    source venv/bin/activate
    ```
- 安装必要库：✅ (大部分已在 `requirements.txt` 和代码中体现)
  ```
  pip install requests beautifulsoup4 pandas playwright schedule
  # aiohttp (异步请求) - 当前主要使用同步Playwright
  # configparser / pyyaml (配置文件解析) - 建议用于管理配置
  ```
  > logging、smtplib、email 为 Python 内置库，已在代码中使用。

## 2. 目标网页分析

- 访问目标网页：
  - https://www.jisilu.cn/data/qdii/#qdiie
  - https://www.jisilu.cn/data/qdii/#qdiia
- 使用开发者工具分析 HTML 结构，定位目标数据元素。✅
- 判断数据加载方式（静态/动态），重点关注 T-1 溢价率。✅
- 优先分析 XHR/Fetch 请求，寻找 API 接口。 (当前采用Playwright直接解析页面) ✅
- 如为动态加载，考虑使用 Playwright/Selenium。✅ (已使用 Playwright)

## 3. 编写爬虫代码

- 导入所需库: ✅ (requests, BeautifulSoup, pandas, os, playwright, smtplib, email, schedule, time, logging 已在 `qdii_spider.py` 中使用)。
- （可选）编写配置文件加载、日志配置函数: 日志配置 ✅; 配置文件加载 ⚠️ (建议加强，目前配置项硬编码较多)。
- 若有 API 接口: (当前主要通过 Playwright 解析 HTML) N/A。
- 若为内嵌 JSON: N/A。
- 若需动态渲染: ✅ (已通过 Playwright 实现)。
- 实现异常处理与重试机制: ✅ (基本实现，可进一步增强)。
- （可选）实现用户代理池: ❌ (未实现)。
- 数据整理为 pandas DataFrame，保存为 CSV: ✅ (原始数据和清洗后数据均有保存)。

## 4. 数据清洗与提取

- 加载 CSV，清洗数据（去空格、类型转换、标准化申购状态等）。✅ (`clean_and_extract` 函数实现)
- 提取目标列（代码、名称、T-1溢价率、申购状态），保存新 CSV。✅

## 5. 数据筛选

- （可选）从配置文件加载筛选条件。⚠️ (当前硬编码，建议配置化)
- 设定筛选条件（如 T-1溢价率≥0.00%，申购状态含“限”字）。✅ (`filter_data` 函数实现)
- 筛选并保存结果。✅ (`qdii_filtered.csv`)

## 6. 邮件发送功能

- （推荐）从配置文件加载邮箱信息。⚠️ (当前为虚拟发送，未配置)
- 配置发件人、收件人、SMTP 服务器等。❌ (未实现实际发送逻辑)
- 构建邮件内容（文本或 HTML），发送邮件并处理异常。⚠️ (当前为虚拟发送，邮件内容为DataFrame字符串)
- 在主流程结束后发送报告。⚠️ (虚拟发送)

## 7. 脚本定时运行

- 使用 schedule、time 库。✅ (`schedule_job` 函数实现)
- （推荐）从配置文件加载运行时间。⚠️ (当前硬编码，建议配置化)
- 设置定时任务，主循环中调用爬虫主函数和 schedule.run_pending()。✅

## 8. 本地运行与测试

- 激活虚拟环境，运行脚本：🔄
  ```
  python qdii_spider.py 
  python qdii_gui.py (如果运行GUI)
  ```
- 检查数据爬取、保存、清洗、筛选功能。✅
- 邮件发送功能。⚠️ (虚拟发送，待完善)
- 定时任务等功能。✅
- 验证数据准确性和邮件发送效果。🔄 (数据准确性部分验证，邮件实际效果待测)
- 检查日志记录（如启用）。✅

## 9. 代码封装与部署（后期）

- 生成 requirements.txt：✅ (已存在 `requirements.txt`)
  ```
  pip freeze > requirements.txt 
  ```
- 可考虑使用 PyInstaller/cx_Freeze 打包 (GUI)，或编写 Dockerfile 部署 (Web UI/爬虫)。❌ (未开始)
- 数据量大时可用数据库存储。 (当前使用CSV) ❌
- 复杂任务可用容器编排工具。❌

## 10. 监控与告警（进阶）

## 11. GUI 界面开发 (PyQt5)
- 状态: 🔄 (部分实现 `qdii_gui.py`)
- 已有功能: 基本界面布局（控制面板、参数输入、日志显示、数据表格）。
- 待办事项:
  - 实现 "开始爬取" 逻辑，集成 `QDIISpider` 并处理信号 (`progress`, `finished`, `error`) 更新UI。
  - 实现 "停止爬取" 逻辑 (可能较复杂，需研究Playwright的终止方式)。
  - 实现 "导出数据" 功能。
  - 完善错误处理和用户反馈。

## 12. Web UI 界面开发 (Flask)
- 状态: 🔄 (初步搭建 `web_ui/` 目录及 `app.py`)
- 已有功能: 基本Flask应用结构，`index.html` 模板。
- 待办事项:
  - 明确Web UI的功能定位 (例如：展示数据、触发爬虫、配置参数等)。
  - 开发后端API接口与前端页面交互。
  - 集成爬虫数据展示。

## 13. 后续优化与建议 
- **完善邮件发送**: 实现真实的邮件发送功能，包括SMTP配置、认证、邮件内容格式化。
- **配置管理**: 将硬编码的参数（如URL、筛选条件、邮箱配置、定时任务时间）移至配置文件 (`config.ini` 或 `config.yaml`)。
- **代码健壮性**: 增强错误处理，例如网络异常、页面结构变化等，添加更全面的重试逻辑。
- **单元测试与集成测试**: 为核心模块编写测试用例。
- **文档完善**: 补充代码注释，更新项目README，包括详细的安装、配置和使用说明。
- **用户体验**: 优化GUI和Web UI的交互和视觉效果。
- **部署方案**: 考虑GUI的打包 (PyInstaller) 和Web服务的部署 (Docker, Gunicorn等)。

- 记录运行时间、成功/失败次数等。 (通过日志部分实现) ⚠️
- 实现异常告警（如邮件通知）。 (邮件功能完善后可集成) ❌