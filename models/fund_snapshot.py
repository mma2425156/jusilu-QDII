"""
基金历史快照模型
每日抓取后存入快照，支持溢价率变化对比。
"""
from datetime import datetime
from extensions import db


class FundSnapshot(db.Model):
    """
    基金快照，按日期和代码唯一索引。

    用于：
    - 历史数据保留（默认保留 30 天）
    - 溢价率变化对比（今日 vs 昨日）
    """
    __tablename__ = "fund_snapshots"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    snapshot_date = db.Column(db.Date, nullable=False, comment="快照日期")
    source = db.Column(db.String(50), nullable=True, comment="市场来源：欧美市场/亚洲市场")
    fund_code = db.Column(db.String(20), nullable=False, comment="基金代码")
    fund_name = db.Column(db.String(200), nullable=False, comment="基金名称")
    premium = db.Column(db.Float, nullable=True, comment="T-1溢价率（%）")
    status = db.Column(db.String(50), nullable=True, comment="申购状态")
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 复合唯一索引
    __table_args__ = (
        db.UniqueConstraint("snapshot_date", "fund_code", name="uq_date_code"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "source": self.source,
            "fund_code": self.fund_code,
            "fund_name": self.fund_name,
            "premium": self.premium,
            "status": self.status,
        }

    @classmethod
    def get_latest(cls, date=None):
        """获取指定日期快照，默认最新日期"""
        if date is None:
            date = cls.query.order_by(cls.snapshot_date.desc()).first()
            return [] if not date else cls.query.filter_by(snapshot_date=date.snapshot_date).all()
        return cls.query.filter_by(snapshot_date=date).all()

    @classmethod
    def get_previous(cls, current_date, days=1):
        """获取当前日期之前 N 天的快照"""
        from datetime import timedelta
        target_date = current_date - timedelta(days=days)
        return {
            f.fund_code: f
            for f in cls.query.filter_by(snapshot_date=target_date).all()
        }

    @classmethod
    def save_from_df(cls, df, snapshot_date=None):
        """
        从 Pandas DataFrame 保存快照。

        DataFrame 须包含列：代码, 名称, 溢价率, 申购状态, 来源（可选）
        """
        if snapshot_date is None:
            snapshot_date = datetime.now().date()
        if isinstance(snapshot_date, str):
            from datetime import datetime as dt
            snapshot_date = dt.strptime(snapshot_date, "%Y-%m-%d").date()

        # 删除同日旧数据（支持重复抓取）
        cls.query.filter_by(snapshot_date=snapshot_date).delete()
        db.session.commit()

        records = []
        for _, row in df.iterrows():
            premium_val = row.get("溢价率")
            if premium_val is None:
                premium_val = row.get("T-1溢价率")
            records.append(cls(
                snapshot_date=snapshot_date,
                source=str(row.get("来源", "")),
                fund_code=str(row.get("代码", "")),
                fund_name=str(row.get("名称", "")),
                premium=float(premium_val) if premium_val is not None and premium_val != "" else None,
                status=str(row.get("申购状态", "")),
            ))

        if records:
            db.session.bulk_save_objects(records)
            db.session.commit()
        return len(records)

    @classmethod
    def compare_today_vs_yesterday(cls, today_date=None):
        """
        对比今日与昨日的溢价率变化。

        返回: list of {fund_code, fund_name, premium_today, premium_yesterday,
                       change, status_today}
        """
        from datetime import timedelta

        if today_date is None:
            today_date = datetime.now().date()

        today_snapshots = cls.get_latest(today_date)
        if not today_snapshots:
            return []

        yesterday_snapshots = cls.get_previous(today_date, days=1)
        today_by_code = {s.fund_code: s for s in today_snapshots}

        result = []
        for code, today_fund in today_by_code.items():
            yesterday_fund = yesterday_snapshots.get(code)
            change = None
            if yesterday_fund and yesterday_fund.premium is not None and today_fund.premium is not None:
                change = round(today_fund.premium - yesterday_fund.premium, 2)

            result.append({
                "source": today_fund.source,
                "fund_code": code,
                "fund_name": today_fund.fund_name,
                "premium_today": today_fund.premium,
                "premium_yesterday": yesterday_fund.premium if yesterday_fund else None,
                "change": change,
                "status": today_fund.status,
            })

        # 按溢价率降序排列
        result.sort(key=lambda x: x["premium_today"] or -999, reverse=True)
        return result

    @classmethod
    def cleanup_old_snapshots(cls, keep_days: int = 30):
        """清理超过保留期的快照"""
        from datetime import timedelta
        cutoff = datetime.now().date() - timedelta(days=keep_days)
        deleted = cls.query.filter(cls.snapshot_date < cutoff).delete()
        db.session.commit()
        return deleted
