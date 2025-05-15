from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import sqlite3
import logging
import time
import subprocess
import os
from flask import current_app
from .mail_service import MailService

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.mail_service = MailService()
        self.logger = logging.getLogger(__name__)
        self.jobs = {}

    def init_scheduler(self, app):
        """初始化调度器并加载数据库中的任务"""
        with app.app_context():
            conn = sqlite3.connect(current_app.config['DATABASE'])
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM task_schedule WHERE is_active = 1")
                tasks = cursor.fetchall()
                
                for task in tasks:
                    self.add_job(
                        task_id=task['id'],
                        cron_expression=task['cron_expression'],
                        recipients=task['recipients'].split(','),
                        conditions=task['conditions']
                    )
                
                if tasks:
                    self.scheduler.start()
                    self.logger.info("定时任务调度器已启动")
            finally:
                conn.close()

    def add_job(self, task_id, cron_expression, recipients, conditions):
        """添加定时任务"""
        trigger = CronTrigger.from_crontab(cron_expression)
        
        job = self.scheduler.add_job(
            self._send_scheduled_report,
            trigger=trigger,
            args=[recipients, conditions, task_id, False],  # is_test=False
            id=str(task_id)
        )
        
        self.jobs[str(task_id)] = job
        self.logger.info(f"已添加定时任务 ID:{task_id}, 表达式:{cron_expression}")
        return job

    def remove_job(self, task_id):
        """移除定时任务"""
        if str(task_id) in self.jobs:
            self.scheduler.remove_job(str(task_id))
            del self.jobs[str(task_id)]
            self.logger.info(f"已移除定时任务 ID:{task_id}")
            return True
        return False

    def _run_spider_with_retry(self, max_retries=5, retry_interval=30):
        """运行爬虫脚本并支持重试"""
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    [os.path.join('e:/Trae/jisilu', 'venv', 'Scripts', 'python.exe'), 
                     'e:/Trae/jisilu/qdii_spider.py'],
                    check=True,
                    capture_output=True,
                    text=True
                )
                return True, result
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"爬虫执行失败(尝试 {attempt+1}/{max_retries}): {e.stderr}")
                if attempt < max_retries - 1:
                    time.sleep(retry_interval)
                continue
        return False, None

    def _send_scheduled_report(self, recipients, conditions, task_id, is_test=False):
        """发送报告的核心逻辑"""
        self.logger.info(f"正在执行{'测试' if is_test else '定时'}任务，发送报告至: {recipients}")
        try:
            import json
            import pandas as pd
            from flask import current_app
            
            # 解析条件
            if isinstance(conditions, str):
                conditions = json.loads(conditions)
                
            premium_min = conditions.get('premium_min', 0)
            status_filter = conditions.get('status_filter', 'all')
            
            # 先执行爬虫获取最新数据
            if is_test:
                # 手动测试立即报告失败
                success, _ = self._run_spider_with_retry(max_retries=1)
                if not success:
                    self.mail_service.send_email(
                        recipients=recipients,
                        subject="QDII数据获取失败",
                        content=f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n爬虫执行失败，请检查系统日志",
                        is_html=False
                    )
                    return False
            else:
                # 定时任务重试5次
                success, _ = self._run_spider_with_retry()
                if not success:
                    self.mail_service.send_email(
                        recipients=recipients,
                        subject="QDII数据获取失败",
                        content=f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n爬虫执行失败，已重试5次",
                        is_html=False
                    )
                    return False
            
            # 读取并筛选数据
            df = pd.read_csv('qdii_all_clean.csv')
            
            if status_filter == 'all':
                filtered = df[df['T-1溢价率'] >= premium_min]
            elif status_filter == 'limited':
                filtered = df[(df['T-1溢价率'] >= premium_min) & 
                             (df['申购状态'].str.contains('限'))]
            elif status_filter == 'open':
                filtered = df[(df['T-1溢价率'] >= premium_min) & 
                             (df['申购状态'].str.contains('开放'))]
            elif status_filter == 'closed':
                filtered = df[(df['T-1溢价率'] >= premium_min) & 
                             (df['申购状态'].str.contains('暂停'))]
            
            # 仅当有符合条件的数据时才发送邮件
            if len(filtered) > 0:
                # 生成HTML表格内容
                table_content = """
                <table border="1" cellpadding="5" style="border-collapse: collapse;">
                    <tr>
                        <th>代码</th>
                        <th>名称</th>
                        <th>T-1溢价率</th>
                        <th>申购状态</th>
                    </tr>
                """
                for _, row in filtered.iterrows():
                    table_content += f"""
                    <tr>
                        <td>{row['代码']}</td>
                        <td>{row['名称']}</td>
                        <td>{row['T-1溢价率']}</td>
                        <td>{row['申购状态']}</td>
                    </tr>
                    """
                table_content += "</table>"
                
                self.mail_service.send_email(
                    recipients=recipients,
                    subject=f"QDII基金报告 {datetime.now().strftime('%Y-%m-%d')}",
                    content=f"""
                    <p>找到 {len(filtered)} 条符合条件的数据：</p>
                    {table_content}
                    <p>筛选条件：T-1溢价率 ≥ {premium_min}, 申购状态: {status_filter}</p>
                    """,
                    is_html=True
                )
            
            # 记录执行日志
            conn = sqlite3.connect(current_app.config['DATABASE'])
            try:
                conn.execute(
                    "INSERT INTO task_logs (task_id, run_time, filtered_count, status) VALUES (?, ?, ?, ?)",
                    (task_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), len(filtered), 'executed')
                )
                conn.commit()
            finally:
                conn.close()
            
            return True
        except Exception as e:
            self.logger.error(f"定时任务执行失败: {str(e)}")
            return False

    def _update_last_run_time(self, recipients):
        """更新任务最后执行时间"""
        conn = sqlite3.connect(current_app.config['DATABASE'])
        try:
            conn.execute(
                "UPDATE task_schedule SET last_run = ? WHERE recipients = ?",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ','.join(recipients))
            )
            conn.commit()
        finally:
            conn.close()
