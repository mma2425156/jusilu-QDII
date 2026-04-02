"""
邮件配置模型（解决邮件配置不持久化问题）
"""
from datetime import datetime
from extensions import db
import config


class EmailConfigModel(db.Model):
    """
    邮件服务器配置，持久化到数据库。
    优先级：数据库配置 > 环境变量配置。
    """
    __tablename__ = "email_config"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    smtp_server = db.Column(db.String(200), nullable=False, comment="SMTP 服务器")
    smtp_port = db.Column(db.Integer, nullable=False, default=587, comment="SMTP 端口")
    smtp_username = db.Column(db.String(200), nullable=False, comment="SMTP 用户名")
    smtp_password = db.Column(db.String(200), nullable=False, comment="SMTP 密码（加密存储更佳）")
    sender_email = db.Column(db.String(200), nullable=False, comment="发件人地址")
    sender_name = db.Column(db.String(200), default="QDII基金监控系统", comment="发件人显示名")
    use_ssl = db.Column(db.Boolean, default=True, comment="是否使用 SSL")
    is_active = db.Column(db.Boolean, default=True, comment="是否启用")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def get_active(cls):
        """获取当前启用的邮件配置，数据库没有则回退到环境变量。"""
        cfg = cls.query.filter_by(is_active=True).first()
        if cfg:
            return cfg
        # 回退到环境变量
        if config.mail.SMTP_SERVER:
            return {
                "smtp_server": config.mail.SMTP_SERVER,
                "smtp_port": config.mail.SMTP_PORT,
                "smtp_username": config.mail.SMTP_USERNAME,
                "smtp_password": config.mail.SMTP_PASSWORD,
                "sender_email": config.mail.MAIL_SENDER,
                "sender_name": config.mail.MAIL_SENDER_NAME,
                "use_ssl": config.mail.SMTP_USE_SSL,
            }
        return None

    def to_dict(self, hide_password: bool = True) -> dict:
        return {
            "id": self.id,
            "smtp_server": self.smtp_server,
            "smtp_port": self.smtp_port,
            "smtp_username": self.smtp_username,
            "smtp_password": "******" if hide_password else self.smtp_password,
            "sender_email": self.sender_email,
            "sender_name": self.sender_name,
            "use_ssl": self.use_ssl,
            "is_active": self.is_active,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
