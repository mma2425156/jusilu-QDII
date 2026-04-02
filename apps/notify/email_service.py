"""
邮件服务 - 支持数据库持久化配置
优先级：数据库配置 > 环境变量
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """
    邮件发送服务。

    配置加载顺序：
    1. 数据库中的 email_config 表（优先）
    2. 环境变量 / config.mail（兜底）
    """

    def get_config(self) -> Optional[dict]:
        """
        获取当前邮件配置。
        优先从 DB 加载，若无则回退到环境变量。
        """
        # 延迟导入避免循环
        from flask import current_app, has_app_context
        from models.email_config import EmailConfigModel

        if has_app_context():
            cfg = EmailConfigModel.get_active()
            if cfg:
                if isinstance(cfg, EmailConfigModel):
                    return cfg.to_dict(hide_password=False)
                return cfg  # 环境变量字典
        return None

    def send(
        self,
        recipients: list[str] | str,
        subject: str,
        content: str,
        is_html: bool = False,
    ) -> bool:
        """
        发送邮件。

        参数:
            recipients: 收件人列表或逗号分隔字符串
            subject: 邮件主题
            content: 邮件正文
            is_html: 是否为 HTML 内容
        """
        cfg = self.get_config()
        if not cfg:
            raise Exception("邮件服务未配置，请先在设置页面配置 SMTP 信息")

        if isinstance(recipients, str):
            recipients = [r.strip() for r in recipients.split(",") if r.strip()]

        msg = MIMEMultipart()
        msg["From"] = f"{cfg.get('sender_name', 'QDII监控系统')} <{cfg['sender_email']}>"
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "html" if is_html else "plain"))

        try:
            if cfg.get("use_ssl", True):
                server = smtplib.SMTP_SSL(cfg["smtp_server"], cfg["smtp_port"])
            else:
                server = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"])
                server.starttls()

            server.login(cfg["smtp_username"], cfg["smtp_password"])
            server.send_message(msg)
            server.quit()

            logger.info(f"邮件发送成功: {subject} -> {recipients}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP 认证失败，请检查用户名和密码")
            raise Exception("SMTP 认证失败，请检查用户名和密码是否正确")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 发送失败: {e}")
            raise Exception(f"SMTP 发送失败: {e}")

    def send_qdii_report(
        self,
        recipients: list[str],
        df,
        conditions: dict,
        is_html: bool = True,
    ) -> bool:
        """
        发送 QDII 基金筛选报告邮件。

        参数:
            recipients: 收件人列表
            df: 筛选后的 Pandas DataFrame
            conditions: 筛选条件 dict
        """
        from datetime import datetime

        premium = conditions.get("premium_min", "?")
        status = conditions.get("status_filter", "全部")
        count = len(df)

        if is_html:
            table_rows = ""
            for _, row in df.iterrows():
                rate = f"{row['T-1溢价率']:.2f}%" if row["T-1溢价率"] is not None else "N/A"
                table_rows += f"""
                <tr>
                    <td>{row.get('来源', '')}</td>
                    <td>{row.get('代码', '')}</td>
                    <td>{row.get('名称', '')}</td>
                    <td>{rate}</td>
                    <td>{row.get('申购状态', '')}</td>
                </tr>"""

            content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333;">
<h2>QDII 基金监控报告</h2>
<p><strong>发送时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p><strong>筛选条件：</strong>溢价率 ≥ {premium}%，申购状态包含「{status}」</p>
<p><strong>命中数量：</strong>{count} 条</p>
<hr>
{('<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;">'
 + '<thead><tr><th>市场</th><th>代码</th><th>名称</th><th>T-1溢价率</th><th>申购状态</th></tr></thead>'
 + '<tbody>' + table_rows + '</tbody></table>') if table_rows else '<p>无符合条件的数据。</p>'}
<hr>
<p style="color:#888;font-size:12px;">本邮件由 QDII 基金监控系统自动发送</p>
</body>
</html>"""
        else:
            content = f"QDII 基金报告\n命中 {count} 条数据（溢价率≥{premium}%，状态含「{status}」）\n\n"
            content += df.to_string(index=False)

        return self.send(
            recipients=recipients,
            subject=f"QDII 基金报告 {datetime.now().strftime('%Y-%m-%d')}",
            content=content,
            is_html=is_html,
        )

    def send_test(self, recipient: str) -> bool:
        """发送测试邮件"""
        from datetime import datetime

        content = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
<h2>测试邮件</h2>
<p>这是一封来自 <strong>QDII 基金监控系统</strong> 的测试邮件。</p>
<p>发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>如果您收到此邮件，说明邮件配置正确！</p>
</body></html>"""

        return self.send(
            recipients=[recipient],
            subject="[QDII监控系统] 测试邮件",
            content=content,
            is_html=True,
        )


# 全局单例
email_service = EmailService()
