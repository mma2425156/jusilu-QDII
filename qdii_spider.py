import os
import requests
import pandas as pd
import schedule
import time
import logging
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import numpy as np
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class SpiderSignals(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class QDIISpider:
    def __init__(self):
        self.signals = SpiderSignals()
        
    def fetch_with_progress(self):
        try:
            self.signals.progress.emit("开始抓取数据...")
            df, now_str = fetch_qdii_data_playwright()
            self.signals.progress.emit("数据抓取完成，开始清洗...")
            df_clean = clean_and_extract(df)
            self.signals.progress.emit("数据清洗完成，开始筛选...")
            df_filtered = filter_data(df_clean)
            if not df_filtered.empty:
                self.signals.finished.emit(df_filtered)
            else:
                self.signals.progress.emit("无符合条件数据")
        except Exception as e:
            self.signals.error.emit(f"发生错误: {str(e)}")

# 1. 数据抓取

def fetch_qdii_data():
    url = 'https://www.jisilu.cn/data/qdii/stock_list/?___jsl=LST___t'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.jisilu.cn/data/qdii/'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        rows = data.get('rows', [])
        df = pd.DataFrame([row['cell'] for row in rows])
        df.to_csv('qdii_raw.csv', index=False, encoding='utf-8-sig')
        logging.info('原始数据已保存')
        return df
    except Exception as e:
        logging.error(f'抓取数据失败: {e}')
        return pd.DataFrame()

def fetch_qdii_data_playwright():
    """使用Playwright抓取QDII数据"""
    import os
    import io
    now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    url_list = [
        ('https://www.jisilu.cn/data/qdii/#qdiie', ['欧美市场', '商品市场']),
        ('https://www.jisilu.cn/data/qdii/#qdiia', ['亚洲市场'])
    ]
    save_dir = 'qdii_tables'
    os.makedirs(save_dir, exist_ok=True)
    all_raw = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            for url, labels in url_list:
                page.goto(url)
                page.wait_for_selector('table')
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                tables = soup.find_all('table')
                if not tables:
                    logging.error(f'{url} 未找到表格')
                    continue
                for i, label in enumerate(labels):
                    if i >= len(tables):
                        break
                    df = pd.read_html(io.StringIO(str(tables[i])), header=1)[0]
                    df.insert(0, '来源', label)
                    all_raw.append(df)
            browser.close()
        # 合并所有原始表格
        if all_raw:
            df_raw = pd.concat(all_raw, ignore_index=True)
            raw_path = os.path.join(save_dir, f'qdii_all_raw_{now_str}.csv')
            df_raw.to_csv(raw_path, index=False, encoding='utf-8-sig')
            logging.info(f'所有原始表格已合并输出: {raw_path}')
            return df_raw, now_str
        else:
            return pd.DataFrame(), now_str
    except Exception as e:
        logging.error(f'Playwright抓取数据失败: {e}')
        return pd.DataFrame(), now_str

# 2. 数据清洗与提取

def clean_and_extract(df):
    """清洗和提取QDII数据"""
    if df.empty:
        return df
    # 自动查找包含目标字段的表头
    target_cols = ['代码', '名称', 'T-1溢价率', '申购状态']
    for i in range(min(5, len(df))):
        if all(col in df.iloc[i].values.tolist() for col in target_cols):
            df.columns = df.iloc[i].values.tolist()
            df = df.iloc[i+1:]
            break
    # 兼容动态渲染表格和API数据
    if 'T-1溢价率' in df.columns and '申购状态' in df.columns:
        # Playwright表格
        cols = ['代码', '名称', 'T-1溢价率', '申购状态']
        df = df[cols].copy()
        df['T-1溢价率'] = pd.to_numeric(df['T-1溢价率'].replace('-', np.nan).str.rstrip('%'), errors='coerce')
    elif 'fund_id' in df.columns:
        cols = ['fund_id', 'fund_nm', 'price_t-1', 'subscribe_status']
        df = df[cols].copy()
        df.columns = target_cols
        df['T-1溢价率'] = pd.to_numeric(df['T-1溢价率'], errors='coerce')
    else:
        logging.error('数据表头不兼容，无法清洗')
        return pd.DataFrame()
    df['申购状态'] = df['申购状态'].astype(str).str.strip()
    return df

# 3. 数据筛选

def filter_data(df, premium=3.5, status_kw='限100'):
    """筛选符合条件的QDII数据"""
    if df.empty:
        return df
    filtered = df[(df['T-1溢价率'] >= premium) & (df['申购状态'].str.contains(status_kw))]
    filtered_path = 'qdii_filtered.csv'
    filtered.to_csv(filtered_path, index=False, encoding='utf-8-sig')
    logging.info(f'筛选结果已保存到根目录: {filtered_path}')
    return filtered

# 4. 邮件发送（虚拟）

def send_email(subject, content, to_addr):
    """虚拟邮件发送功能，实际使用时需配置SMTP"""
    logging.info(f'虚拟发送邮件: {subject} -> {to_addr}\n内容预览:\n{content[:100]}...')
    logging.warning('注意: 当前为虚拟邮件发送，实际使用需配置SMTP服务器信息')

# 5. 主流程

def run_spider_workflow(premium=3.5, status_kw='限100'):
    """运行完整的爬虫工作流程"""
    df, now_str = fetch_qdii_data_playwright()
    df_clean = clean_and_extract(df)
    df_filtered = filter_data(df_clean, premium, status_kw)
    if not df_filtered.empty:
        content = df_filtered.to_string(index=False)
        send_email('QDII筛选结果', content, 'test@example.com')
    else:
        logging.info('无符合条件数据，无需发送邮件')
    return now_str, df_filtered

def batch_clean_tables(now_str):
    import os
    table_dir = 'qdii_tables'
    raw_path = os.path.join(table_dir, f'qdii_all_raw_{now_str}.csv')
    if not os.path.exists(raw_path):
        logging.error('未找到原始合并表格，无法清洗')
        return
    try:
        df = pd.read_csv(raw_path)
        # 自动查找包含目标字段的表头
        target_cols = ['代码', '名称', 'T-1溢价率', '申购状态']
        for i in range(min(5, len(df))):
            if all(col in df.iloc[i].values.tolist() for col in target_cols):
                df.columns = df.iloc[i].values.tolist()
                df = df.iloc[i+1:]
                break
        # 兼容动态渲染表格和API数据
        if 'T-1溢价率' in df.columns and '申购状态' in df.columns:
            cols = ['来源', '代码', '名称', 'T-1溢价率', '申购状态'] if '来源' in df.columns else ['代码', '名称', 'T-1溢价率', '申购状态']
            df = df[cols].copy()
            df['T-1溢价率'] = pd.to_numeric(df['T-1溢价率'].replace('-', np.nan).astype(str).str.rstrip('%'), errors='coerce')
        elif 'fund_id' in df.columns:
            cols = ['来源', 'fund_id', 'fund_nm', 'price_t-1', 'subscribe_status'] if '来源' in df.columns else ['fund_id', 'fund_nm', 'price_t-1', 'subscribe_status']
            df = df[cols].copy()
            df.columns = ['来源', '代码', '名称', 'T-1溢价率', '申购状态'] if '来源' in df.columns else target_cols
            df['T-1溢价率'] = pd.to_numeric(df['T-1溢价率'], errors='coerce')
        else:
            logging.error(f'{raw_path} 数据表头不兼容，无法清洗')
            return
        df['申购状态'] = df['申购状态'].astype(str).str.strip()
        clean_path = os.path.join(table_dir, f'qdii_all_clean_{now_str}.csv')
        df.to_csv(clean_path, index=False, encoding='utf-8-sig')
        logging.info(f'合并清洗后数据已保存: {clean_path}')
        
        # 保存到根目录
        root_path = os.path.join(os.path.dirname(os.path.dirname(table_dir)), 'qdii_all_clean.csv')
        df.to_csv(root_path, index=False, encoding='utf-8-sig')
        logging.info(f'最新数据已保存到根目录: {root_path}')
        # 筛选数据
        filtered = df[(pd.to_numeric(df['T-1溢价率'], errors='coerce') >= 0) & (df['申购状态'].str.contains('限'))]
        filtered_path = os.path.join(os.path.dirname(os.path.dirname(table_dir)), 'qdii_filtered.csv')
        filtered.to_csv(filtered_path, index=False, encoding='utf-8-sig')
        logging.info(f'筛选结果已保存到根目录: {filtered_path}，共{len(filtered)}条')
        # === END ===
    except Exception as e:
        logging.error(f'{raw_path} 清洗失败: {e}')

def merge_clean_tables(now_str):
    # 不再需要，留空
    pass

# 6. 定时任务（虚拟测试只运行一次）
if __name__ == '__main__':
    try:
        import playwright
        logging.info('开始运行测试...')
        now_str, _ = run_spider_workflow()
        batch_clean_tables(now_str)
        logging.info('测试运行完成')
    except ImportError:
        logging.error('缺少playwright依赖，请先安装: pip install playwright && playwright install')
