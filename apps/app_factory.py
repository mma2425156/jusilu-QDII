"""
Flask 应用工厂 - 重构版
路径全部由 config 管理，无硬编码。
"""
from pathlib import Path

from flask import Flask
from flask_cors import CORS

import config
from extensions import db, csrf


def create_app(test_config: dict = None) -> Flask:
    """
    创建并配置 Flask 应用。

    参数:
        test_config: 测试配置字典（用于单元测试）
    """
    app = Flask(
        __name__,
        template_folder=str(config.flask.TEMPLATES),
        static_folder=str(config.flask.STATICS),
    )

    # ── Flask 基础配置 ──────────────────────────────────
    app.config["SECRET_KEY"] = config.flask.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = config.db.URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["WTF_CSRF_ENABLED"] = True

    # 合并测试配置
    if test_config:
        app.config.update(test_config)

    # ── 确保必要目录存在 ─────────────────────────────────
    db_url = config.db.URL
    db_path_str = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    db_path = Path(db_path_str) if db_path_str else Path("instance") / "app.db"
    for path in [
        config.flask.TEMPLATES,
        config.flask.STATICS,
        db_path.parent,
        config.spider.DATA_DIR,
    ]:
        if isinstance(path, Path) and str(path):
            path.mkdir(parents=True, exist_ok=True)
        elif isinstance(path, str) and not path.startswith("sqlite"):
            Path(path).mkdir(parents=True, exist_ok=True)

    # ── 初始化扩展 ───────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    csrf.init_app(app)

    # ── 注册蓝图 ─────────────────────────────────────────
    with app.app_context():
        from apps.api.routes import api_bp

        app.register_blueprint(api_bp, url_prefix="/api")
        app.register_blueprint(create_page_bp())

        # 创建数据库表
        db.create_all()

        # 初始化内置渠道
        from models import init_builtin_channels, NotifyTemplate

        init_builtin_channels()

        # 初始化默认通知模板（若不存在）
        if not NotifyTemplate.query.first():
            db.session.add(
                NotifyTemplate(
                    name="默认模板",
                    title_template="QDII基金报告 {{date}}",
                    content_template=(
                        "找到 **{{count}}** 条符合条件的数据：\n\n"
                        "{{table}}\n\n"
                        "筛选条件：溢价率 >= {{premium_min}}%，状态包含「{{status_filter}}」\n"
                        "来源：集思录 | QDII监控系统"
                    ),
                    is_default=True,
                )
            )
            db.session.commit()

        # 初始化调度器
        _init_scheduler(app)

    return app


def create_page_bp():
    """页面路由蓝图"""
    from flask import Blueprint, render_template, request

    import pandas as pd

    import config

    bp = Blueprint("pages", __name__)

    @bp.route("/", methods=["GET", "POST"])
    def index():
        premium_min = request.form.get("premium_min", default=0.0, type=float)
        status_filter = request.form.get("status_filter", default="all")

        # 优先使用带变化的快照数据
        try:
            from models import FundSnapshot

            all_funds = FundSnapshot.compare_today_vs_yesterday()
        except Exception:
            all_funds = []

        # 若无快照数据，尝试从 CSV 读取
        if not all_funds:
            data_path = config.spider.output_clean_path
            if data_path.exists():
                df = pd.read_csv(data_path)
                # 标准化列名
                col_map = {
                    "来源": "source",
                    "代码": "code",
                    "名称": "name",
                    "溢价率": "premium_today",
                    "申购状态": "status",
                }
                df = df.rename(columns=col_map)
                df["source"] = df.get("source", "")
                df["change"] = None
                all_funds = df.to_dict("records")
            else:
                all_funds = []

        # 应用筛选
        filtered = []
        for f in all_funds:
            premium = f.get("premium_today")
            if premium is None:
                continue
            if premium < premium_min:
                continue
            status = f.get("status", "")
            if status_filter == "limited" and "限" not in str(status):
                continue
            elif status_filter == "open" and "开放" not in str(status):
                continue
            elif status_filter == "closed" and "暂停" not in str(status):
                continue
            filtered.append(f)

        # 按溢价率降序
        filtered.sort(key=lambda x: x.get("premium_today") or -999, reverse=True)

        # 更新时间
        update_time = None
        try:
            data_path = config.spider.output_clean_path
            if data_path.exists():
                update_time = pd.Timestamp(data_path.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        except Exception:
            pass

        return render_template(
            "index_new.html",
            qdii_data=filtered,
            premium_min=premium_min,
            status_filter=status_filter,
            update_time=update_time,
        )

    return bp


def _init_scheduler(app):
    """Initialize scheduler in app context."""
    import logging

    logger = logging.getLogger(__name__)
    try:
        from apps.scheduler import TaskScheduler

        scheduler = TaskScheduler()
        scheduler.init_scheduler(app)
        app.scheduler = scheduler
        logger.info("Scheduler initialized successfully")
    except Exception as e:
        logger.error("Scheduler init failed: %s", e)
