# QDII基金数据爬取与分析系统

## 项目简介
本项目用于从集思录网站抓取QDII基金数据，进行清洗和分析，并提供Web界面展示筛选结果。主要功能包括：
- 使用Playwright抓取QDII基金数据
- 数据清洗和筛选
- Web界面展示和交互

## 安装指南

### 0. 环境要求
- Python 3.12 (推荐)
- 最低要求: Python 3.10+
- 下载地址: [Python官网](https://www.python.org/downloads/)

### 1. 克隆项目
```bash
git clone https://github.com/mma2425156/jusilu-QDII
cd jisilu
```

### 2. 创建虚拟环境
```bash
python -m venv venv
```

### 3. 激活虚拟环境
Windows:
```bash
venv\Scripts\activate
```
Linux/Mac:
```bash
source venv/bin/activate
```

### 4. 安装依赖
```bash
pip install -r requirements.txt
playwright install
```

## 运行步骤

### 1. 启动项目
```bash
# 启动爬虫和Web服务
python main.py
```

### 2. 手动启动（开发模式）
```bash
# 启动爬虫
python qdii_spider.py

# 启动Web服务
python web_ui/app.py
```

### 3. 访问Web界面
浏览器打开: http://127.0.0.1:8866

## 功能说明

### 数据抓取
- 从集思录抓取QDII基金数据
- 支持欧美/亚洲/商品市场
- 自动保存原始数据到 qdii_tables/ 目录
- 清洗后的数据保存在 qdii_tables/ 目录

### 数据筛选
- 支持溢价率筛选（正负10%阈值）
- 支持申购状态筛选（开放/限购/暂停）
- 支持多条件组合筛选

### Web界面
- 实时展示最新数据
- 支持自定义筛选条件
- 提供数据可视化图表
- 支持手动刷新数据
- 提供数据导出功能

## 注意事项
1. 首次运行需要安装Playwright浏览器
   ```bash
   playwright install
   ```

2. 数据抓取频率限制为30秒一次
3. 建议在虚拟环境中运行
4. 爬虫数据保存路径: qdii_tables/
5. 数据文件命名格式: qdii_all_clean_YYYYMMDD_HHMMSS.csv (清洗后数据)
6. 项目结构说明:
   - main.py: 主入口，整合爬虫和Web服务
   - qdii_spider.py: 主爬虫逻辑
   - web_ui/app.py: Web服务逻辑
   - web_ui/templates/index.html: 前端模板
   - web_ui/config.db: SQLite数据库配置
   - requirements.txt: 依赖清单
   - qdii_tables/: 存储原始和清洗后的数据
