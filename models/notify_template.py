"""
通知模板模型
"""
from datetime import datetime
from extensions import db


class NotifyTemplate(db.Model):
    """
    通知模板，定义推送内容格式。

    变量占位符格式：{{fund_name}}, {{premium}}, {{change}}, {{date}}
    """
    __tablename__ = "notify_templates"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, comment="模板名称")
    title_template = db.Column(db.String(500), default="QDII基金报告 {{date}}", comment="标题模板")
    # content_template 支持 Markdown/HTML
    content_template = db.Column(db.Text, nullable=False,
        default="找到 **{{count}}** 条符合条件的数据：\n\n{{table}}", comment="内容模板")
    is_default = db.Column(db.Boolean, default=False, comment="是否默认模板")
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "title_template": self.title_template,
            "content_template": self.content_template,
            "is_default": self.is_default,
        }

    def render(self, variables: dict) -> tuple[str, str]:
        """
        渲染模板，返回 (title, content)。

        变量示例：
        {
            "date": "2026-04-02",
            "count": 5,
            "table": "<table>...</table>",
            "funds": [{"name": "xxx", "premium": "5.2%", "change": "+1.5%"}, ...],
        }
        """
        title = self.title_template
        content = self.content_template

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            # funds 特殊处理
            if key == "table" and isinstance(value, list):
                # 渲染 Markdown 表格
                rows = ["| 市场 | 代码 | 名称 | 溢价率 | 变化 | 状态 |",
                        "|------|------|------|--------|------|------|"]
                for f in value:
                    change = f.get("change", "")
                    change_icon = ""
                    if change.startswith("+"):
                        change_icon = "🔺"
                    elif change.startswith("-"):
                        change_icon = "🔻"
                    rows.append(
                        f"|{f.get('source', '')}|{f.get('code', '')}|"
                        f"{f.get('name', '')}|{f.get('premium', '')}|"
                        f"{change_icon}{change}|{f.get('status', '')}|"
                    )
                value = "\n".join(rows)
            title = title.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))

        return title, content

    @classmethod
    def get_default(cls) -> "NotifyTemplate":
        t = cls.query.filter_by(is_default=True).first()
        if not t:
            t = cls.query.first()
        return t or None
