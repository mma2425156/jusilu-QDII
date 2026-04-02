"""
任务执行日志模型
"""
from datetime import datetime
from extensions import db


class TaskLog(db.Model):
    """定时任务执行日志"""
    __tablename__ = "task_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task_schedule.id"), nullable=False, comment="关联任务ID")
    run_time = db.Column(db.DateTime, default=datetime.now, nullable=False, comment="执行时间")
    filtered_count = db.Column(db.Integer, default=0, comment="筛选命中数量")
    status = db.Column(db.String(50), nullable=False, default="executed", comment="执行状态")
    error_message = db.Column(db.Text, nullable=True, comment="错误信息")

    # 关联任务
    task = db.relationship("TaskSchedule", back_populates="logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "run_time": self.run_time.isoformat() if self.run_time else None,
            "filtered_count": self.filtered_count,
            "status": self.status,
            "error_message": self.error_message,
        }
