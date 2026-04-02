"""
任务调度模型
"""
from datetime import datetime
from extensions import db
import json


class TaskSchedule(db.Model):
    """定时任务配置"""
    __tablename__ = "task_schedule"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cron_expression = db.Column(db.String(100), nullable=False, comment="Cron 表达式，如 0 8 * * *")
    is_active = db.Column(db.Boolean, default=True, comment="是否启用")
    last_run = db.Column(db.DateTime, nullable=True, comment="上次执行时间")
    next_run = db.Column(db.DateTime, nullable=True, comment="下次执行时间")
    recipients = db.Column(db.String(500), nullable=False, comment="收件人，逗号分隔")
    # conditions 为 JSON: {"premium_min": 3.5, "status_filter": "限100"}
    conditions = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联日志
    logs = db.relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

    def get_conditions(self) -> dict:
        try:
            return json.loads(self.conditions)
        except Exception:
            return {}

    def set_conditions(self, data: dict):
        self.conditions = json.dumps(data, ensure_ascii=False)

    def get_recipients_list(self) -> list:
        return [r.strip() for r in self.recipients.split(",") if r.strip()]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cron_expression": self.cron_expression,
            "is_active": self.is_active,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "recipients": self.get_recipients_list(),
            "conditions": self.get_conditions(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
