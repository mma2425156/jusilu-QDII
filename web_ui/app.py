from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import subprocess
import pandas as pd
import datetime
import time

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'config.db')

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

last_refresh_time = 0

def run_spider():
    global last_refresh_time
    current_time = time.time()
    if current_time - last_refresh_time < 30:
        raise Exception("刷新太频繁，请等待30秒后再试")
    
    try:
        # 使用虚拟环境的Python运行爬虫脚本
        result = subprocess.run(
            [os.path.join('e:/Trae/jisilu', 'venv', 'Scripts', 'python.exe'), 
             'e:/Trae/jisilu/qdii_spider.py'],
            check=True,
            capture_output=True,
            text=True
        )
        last_refresh_time = current_time
        return result
    except subprocess.CalledProcessError as e:
        error_msg = f"爬虫执行失败: {e.stderr}"
        if "playwright" in error_msg.lower():
            error_msg += "\n请确保已安装Playwright浏览器(运行: playwright install)"
        elif "pyqt5" in error_msg.lower():
            error_msg += "\n请确保PyQt5已正确安装"
        raise Exception(error_msg)
    except FileNotFoundError:
        raise Exception("找不到爬虫脚本或Python解释器，请检查路径配置")

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        # 获取用户筛选条件
        premium_min = request.form.get('premium_min', default=0, type=float)
        status_filter = request.form.get('status_filter', default='all')
        
        # 获取数据更新时间
        update_time = datetime.datetime.fromtimestamp(os.path.getmtime('e:/Trae/jisilu/qdii_all_clean.csv')).strftime('%Y-%m-%d %H:%M:%S')
        
        # 读取根目录下的最新数据并根据条件筛选
        df = pd.read_csv('e:/Trae/jisilu/qdii_all_clean.csv')
        # 根据申购状态筛选
        if status_filter == 'all':
            filtered = df[df['T-1溢价率'] >= premium_min]
        elif status_filter == 'limited':
            filtered = df[(df['T-1溢价率'] >= premium_min) & (df['申购状态'].str.contains('限'))]
        elif status_filter == 'open':
            filtered = df[(df['T-1溢价率'] >= premium_min) & (df['申购状态'].str.contains('开放'))]
        elif status_filter == 'closed':
            filtered = df[(df['T-1溢价率'] >= premium_min) & (df['申购状态'].str.contains('暂停'))]
            
        qdii_data = filtered.to_dict('records')
        
        return render_template('index.html', 
                              qdii_data=qdii_data, 
                              premium_min=premium_min, 
                              status_filter=status_filter,
                              update_time=update_time)
    except Exception as e:
        app.logger.error(f'Error in index route: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/refresh', methods=['POST'])
def refresh_data():
    try:
        result = run_spider()
        # 读取根目录下的最新数据并应用当前筛选条件
        premium_min = request.form.get('premium_min', default=0, type=float)
        status_filter = request.form.get('status_filter', default='限')
        df = pd.read_csv('e:/Trae/jisilu/qdii_all_clean.csv')
        filtered = df[(df['T-1溢价率'] >= premium_min) & (df['申购状态'].str.contains(status_filter))]
        qdii_data = filtered.to_dict('records')
        return jsonify({
            'status': 'success', 
            'data': qdii_data,
            'message': '数据刷新成功',
            'output': result.stdout,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        app.logger.error(f'Error in refresh_data route: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8866, debug=True)
