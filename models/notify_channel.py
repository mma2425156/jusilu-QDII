"""
通知渠道配置模型
每种渠道独立配置，持久化到数据库。
"""
from datetime import datetime
from extensions import db


class NotifyChannel(db.Model):
    """
    通知渠道配置。

    每个渠道独立一行，is_active=True 表示该渠道已启用。
    配置值以 JSON 形式存储（如 token、secret 等）。
    """
    __tablename__ = "notify_channels"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel = db.Column(db.String(50), nullable=False, unique=True, comment="渠道标识")
    name = db.Column(db.String(100), nullable=False, comment="渠道显示名")
    config = db.Column(db.Text, nullable=False, default="{}", comment="配置 JSON（token/secret等）")
    is_active = db.Column(db.Boolean, default=False, comment="是否启用")
    is_default = db.Column(db.Boolean, default=False, comment="是否默认渠道")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def get_config(self) -> dict:
        import json
        try:
            return json.loads(self.config)
        except Exception:
            return {}

    def set_config(self, data: dict):
        import json
        self.config = json.dumps(data, ensure_ascii=False)

    def to_dict(self, hide_sensitive: bool = True) -> dict:
        cfg = self.get_config()
        # 隐藏敏感信息
        sensitive_keys = ["password", "secret", "token", "sckey", "key"]
        if hide_sensitive:
            for key in sensitive_keys:
                if key in cfg and cfg[key]:
                    cfg[key] = "******"
        return {
            "id": self.id,
            "channel": self.channel,
            "name": self.name,
            "config": cfg,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_active_channels(cls) -> list:
        """获取所有已启用的渠道"""
        return cls.query.filter_by(is_active=True).all()

    @classmethod
    def get_by_channel(cls, channel: str):
        return cls.query.filter_by(channel=channel).first()


# ──────────────────────────────────────────
# 内置渠道定义（首次初始化时自动插入）
# ──────────────────────────────────────────
BUILTIN_CHANNELS = [
    {"channel": "email", "name": "邮件 SMTP"},
    {"channel": "dingtalk", "name": "钉钉机器人"},
    {"channel": "feishu", "name": "飞书机器人"},
    {"channel": "wecom", "name": "企业微信"},
    {"channel": "telegram", "name": "Telegram"},
    {"channel": "pushplus", "name": "PushPlus"},
    {"channel": "serverchan", "name": "Server酱"},
    {"channel": "bark", "name": "Bark"},
    {"channel": "igot", "name": "iGot"},
    {"channel": "webhook", "name": "自定义 Webhook"},
]


def init_builtin_channels():
    """初始化内置渠道（只插入，不覆盖已有配置）"""
    for ch in BUILTIN_CHANNELS:
        existing = NotifyChannel.get_by_channel(ch["channel"])
        if not existing:
            db.session.add(NotifyChannel(
                channel=ch["channel"],
                name=ch["name"],
                config="{}",
                is_active=False,
            ))
    db.session.commit()
