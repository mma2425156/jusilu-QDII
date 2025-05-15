from flask import render_template, request, jsonify
import sqlite3
import json
import os
import subprocess
import pandas as pd
import datetime
import time
import atexit
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from web_ui.factory import create_app
from web_ui.mail_service import MailService
from web_ui.scheduler import TaskScheduler
from web_ui.miniprogram import create_miniprogram_blueprint

# 创建Flask应用
app = create_app()

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    
    # 初始化数据库表
    with conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS task_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cron_expression TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            last_run TIMESTAMP,
            next_run TIMESTAMP,
            recipients TEXT NOT NULL,
            conditions TEXT NOT NULL,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            email_notifications BOOLEAN DEFAULT 1,
            notification_threshold REAL DEFAULT 0.05,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            run_time TIMESTAMP NOT NULL,
            filtered_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES task_schedule(id)
        );
    ''')
    return conn

# 初始化数据库连接
with app.app_context():
    get_db()  # 确保数据库表已创建

# 注册小程序蓝图
miniprogram = create_miniprogram_blueprint()
app.register_blueprint(miniprogram)

# 初始化任务调度器
task_scheduler = TaskScheduler()
task_scheduler.init_scheduler(app)

# 确保应用退出时关闭调度器
atexit.register(lambda: task_scheduler.scheduler.shutdown())

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
        # 初始化filtered为完整数据集
        filtered = df[df['T-1溢价率'] >= premium_min]
        # 根据申购状态筛选
        if status_filter == 'limited':
            filtered = filtered[filtered['申购状态'].str.contains('限')]
        elif status_filter == 'open':
            filtered = filtered[filtered['申购状态'].str.contains('开放')]
        elif status_filter == 'closed':
            filtered = filtered[filtered['申购状态'].str.contains('暂停')]
            
        qdii_data = filtered.to_dict('records')
        
        return render_template('index.html', 
                              qdii_data=qdii_data, 
                              premium_min=premium_min, 
                              status_filter=status_filter,
                              update_time=update_time)
    except Exception as e:
        app.logger.error(f'Error in index route: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

mail_service = MailService()

@app.route('/api/mail/config', methods=['GET', 'POST'])
def mail_config():
    if request.method == 'GET':
        try:
            config = mail_service.get_mail_config()
            # 隐藏敏感信息
            if 'password' in config:
                config['password'] = '******'
            return jsonify({'status': 'success', 'config': config})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        try:
            data = request.get_json()
            # 优先使用环境变量密码
            password = os.getenv('EMAIL_PASSWORD') or data.get('password', '')
            mail_service.update_mail_config(
                smtp_server=data['smtp_server'],
                smtp_port=data['smtp_port'],
                username=data['username'],
                password=password,
                sender_email=data['sender_email'],
                use_ssl=data.get('use_ssl', True)
            )
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks', methods=['GET', 'POST', 'DELETE'])
def manage_tasks():
    try:
        app.logger.info(f'处理/api/tasks请求，方法: {request.method}')
        app.logger.info(f'请求头: {dict(request.headers)}')
        app.logger.info(f'请求内容类型: {request.content_type}')
        raw_data = request.get_data()
        app.logger.info(f'原始请求数据: {raw_data}')
        
        if request.method == 'GET':
            result = handle_get_tasks()
        elif request.method == 'POST':
            app.logger.info('开始处理POST请求')
            if not request.is_json:
                app.logger.error('请求不是JSON格式')
                return jsonify({'status': 'error', 'message': '请求必须是JSON格式'}), 400
            
            try:
                data = request.get_json()
                app.logger.info(f'解析后的JSON数据: {data}')
                result = handle_create_task()
                if result is None:
                    app.logger.error('handle_create_task返回None')
                    return jsonify({'status': 'error', 'message': '内部服务器错误'}), 500
            except Exception as e:
                app.logger.error(f'JSON解析失败: {str(e)}')
                return jsonify({'status': 'error', 'message': '无效的JSON数据'}), 400
                
            app.logger.info('POST请求处理完成')
        elif request.method == 'DELETE':
            result = handle_delete_task()
        else:
            result = jsonify({'status': 'error', 'message': 'Method not allowed'}), 405
        
        app.logger.info(f'请求处理完成，返回结果: {result}')
        return result
    except Exception as e:
        app.logger.error(f'处理/api/tasks请求时发生异常: {str(e)}', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

def handle_get_tasks():
    try:
        conn = get_db()
        tasks = conn.execute("SELECT * FROM task_schedule").fetchall()
        return jsonify({
            'status': 'success',
            'tasks': [dict(task) for task in tasks]
        })
    except Exception as e:
        app.logger.error(f'获取任务列表失败: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

def handle_create_task():
    try:
        app.logger.info('开始处理任务创建请求')
        data = request.get_json()
        app.logger.info(f'接收到的JSON数据: {data}')
        
        if not data:
            app.logger.error('请求体为空')
            return jsonify({'status': 'error', 'message': '请求体不能为空'}), 400
            
        # 验证必要字段
        if not data.get('cron_expression'):
            app.logger.error('缺少cron_expression字段')
            return jsonify({'status': 'error', 'message': '缺少必填字段: cron_expression'}), 400
        if not data.get('recipients'):
            app.logger.error('缺少recipients字段')
            return jsonify({'status': 'error', 'message': '缺少必填字段: recipients'}), 400
            
        app.logger.info('开始数据库操作')
        conn = get_db()
        conditions = {
            'premium_min': data.get('premium_min', 0),
            'status_filter': data.get('status_filter', 'all')
        }
        app.logger.info(f'任务条件: {conditions}')
        
        cursor = conn.execute(
            "INSERT INTO task_schedule (cron_expression, recipients, conditions) "
            "VALUES (?, ?, ?) RETURNING id",
            (data['cron_expression'], 
             ','.join(data['recipients']), json.dumps(conditions))
        )
        task_id = cursor.fetchone()['id']
        conn.commit()
        app.logger.info(f'任务创建成功，ID: {task_id}')
        
        # 添加定时任务
        app.logger.info('开始添加定时任务')
        task_scheduler.add_job(
            task_id=task_id,
            cron_expression=data['cron_expression'],
            recipients=data['recipients'],
            conditions=conditions
        )
        app.logger.info('定时任务添加成功')
        
        result = jsonify({'status': 'success', 'task_id': task_id})
        app.logger.info(f'返回结果: {result}')
        return result
    except Exception as e:
        app.logger.error(f'任务创建失败: {str(e)}', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

def handle_delete_task():
    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'status': 'error', 'message': '缺少task_id参数'}), 400
            
        conn = get_db()
        conn.execute("DELETE FROM task_schedule WHERE id = ?", (task_id,))
        conn.commit()
        
        # 移除定时任务
        task_scheduler.remove_job(task_id)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
            
@app.route('/api/tasks/<int:task_id>/status', methods=['POST'])
def update_task_status(task_id):
    try:
        data = request.get_json()
        new_status = data.get('is_active', True)
        
        conn = get_db()
        conn.execute(
            "UPDATE task_schedule SET is_active = ? WHERE id = ?",
            (1 if new_status else 0, task_id)
        )
        conn.commit()
        
        # 更新定时任务状态
        if new_status:
            task = conn.execute("SELECT * FROM task_schedule WHERE id = ?", (task_id,)).fetchone()
            task_scheduler.add_job(
                task_id=task['id'],
                cron_expression=task['cron_expression'],
                recipients=task['recipients'].split(','),
                conditions=task['conditions']
            )
        else:
            task_scheduler.remove_job(task_id)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks/test', methods=['POST'])
def test_task():
    try:
        data = request.get_json()
        # 调用任务调度器的测试逻辑
        task_scheduler._send_scheduled_report(
            recipients=data['recipients'],
            conditions={
                'premium_min': data.get('premium_min', 0),
                'status_filter': data.get('status_filter', 'all')
            },
            task_id=-1,  # 测试任务使用特殊ID
            is_test=True
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/logs', methods=['GET'])
def get_task_logs(task_id):
    try:
        conn = get_db()
        logs = conn.execute(
            "SELECT * FROM task_logs WHERE task_id = ? ORDER BY run_time DESC LIMIT 50",
            (task_id,)
        ).fetchall()
        return jsonify({
            'status': 'success',
            'logs': [dict(log) for log in logs]
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/mail/test', methods=['POST'])
def test_mail():
    try:
        data = request.get_json()
        mail_service.send_email(
            recipients=data['recipient'],
            subject="测试邮件 - QDII基金监控系统",
            content="这是一封测试邮件，用于验证您的邮件配置是否正确。"
        )
        return jsonify({'status': 'success'})
    except Exception as e:
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
    import os
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python路径: {os.sys.path}")
    app.run(host='0.0.0.0', port=8866, debug=False)
