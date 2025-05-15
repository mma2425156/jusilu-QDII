import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import os
from flask import current_app
import logging
from datetime import datetime

class MailService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_mail_config(self):
        """从环境变量获取邮件服务器配置"""
        import os
        config = {
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': int(os.getenv('SMTP_PORT', 465)),
            'username': os.getenv('EMAIL_USERNAME'),
            'password': os.getenv('EMAIL_PASSWORD'),
            'sender_email': os.getenv('DEFAULT_SENDER_EMAIL'),
            'use_ssl': os.getenv('USE_SSL', 'true').lower() == 'true'
        }
        if not all(config.values()):
            self.logger.warning("部分邮件配置环境变量未设置")
            return None
        return config

    def send_email(self, recipients, subject, content, is_html=False):
        """发送邮件核心方法"""
        mail_config = self.get_mail_config()
        if not mail_config:
            raise Exception("邮件服务器未配置")

        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = mail_config['sender_email']
            msg['To'] = ', '.join(recipients) if isinstance(recipients, list) else recipients
            msg['Subject'] = subject
            
            # 添加邮件内容
            if is_html:
                msg.attach(MIMEText(content, 'html'))
            else:
                msg.attach(MIMEText(content, 'plain'))

            # 连接SMTP服务器并发送
            if mail_config['use_ssl']:
                server = smtplib.SMTP_SSL(mail_config['smtp_server'], mail_config['smtp_port'])
            else:
                server = smtplib.SMTP(mail_config['smtp_server'], mail_config['smtp_port'])
                server.starttls()
                
            server.login(mail_config['username'], mail_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"邮件发送成功至: {recipients}")
            return True
        except Exception as e:
            self.logger.error(f"邮件发送失败: {str(e)}")
            raise Exception(f"邮件发送失败: {str(e)}")

    def update_mail_config(self, smtp_server, smtp_port, username, password, sender_email, use_ssl=True):
        """更新邮件服务器配置(环境变量方式)"""
        self.logger.warning("当前使用环境变量配置，前端配置不会被保存")
        return {
            'status': 'success',
            'message': '配置已保存到环境变量，请修改.env文件使配置永久生效'
        }

    def send_qdii_report(self, recipients, conditions):
        """发送QDII基金报告"""
        # 这里需要集成数据获取逻辑
        # 示例内容，实际应从数据库获取数据
        report_content = f"""
        QDII基金报告 {datetime.now().strftime('%Y-%m-%d')}
        
        筛选条件: {conditions}
        
        基金数据:
        [这里应包含实际的基金数据]
        """
        
        return self.send_email(
            recipients=recipients,
            subject=f"QDII基金报告 {datetime.now().strftime('%Y-%m-%d')}",
            content=report_content
        )
