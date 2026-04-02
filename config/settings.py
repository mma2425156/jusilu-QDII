"""
配置管理模块
所有配置通过环境变量管理，无硬编码路径。
"""
from pathlib import Path
from dotenv import load_dotenv
import os

# 加载 .env 文件（从 config/ 目录加载）
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ──────────────────────────────────────────
# 项目根目录（自动计算）
# ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def _env_path(key: str, default: str) -> Path:
    """返回环境变量指定的路径（相对项目根目录），若不存在则创建。"""
    rel = os.getenv(key, default)
    p = PROJECT_ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ──────────────────────────────────────────
# Flask 配置
# ──────────────────────────────────────────
class FlaskConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT = int(os.getenv("FLASK_PORT", "8866"))

    # 模板/静态文件路径（兼容旧 web_ui/ 结构）
    TEMPLATES = PROJECT_ROOT / "web_ui" / "templates"
    STATICS = PROJECT_ROOT / "web_ui" / "static"


# ──────────────────────────────────────────
# 数据库配置
# ──────────────────────────────────────────
class DBConfig:
    _default_path = PROJECT_ROOT / "instance" / "app.db"
    # SQLite 绝对路径需要 4 个斜杠：sqlite:////absolute/path
    URL = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{_default_path.as_posix()}",
    )
    # 备份保留天数
    BACKUP_DAYS = int(os.getenv("DB_BACKUP_DAYS", "7"))


# ──────────────────────────────────────────
# 爬虫 / 数据文件配置
# ──────────────────────────────────────────
class SpiderConfig:
    # 原始数据存储目录
    DATA_DIR = _env_path("DATA_DIR", "qdii_tables")
    # 清洗后数据输出文件（相对 DATA_DIR）
    OUTPUT_CLEAN = os.getenv("OUTPUT_CLEAN", "qdii_all_clean.csv")
    OUTPUT_FILTERED = os.getenv("OUTPUT_FILTERED", "qdii_filtered.csv")

    # 抓取 URLs
    JISILU_URLS = [
        ("https://www.jisilu.cn/data/qdii/#qdiie", ["欧美市场", "商品市场"]),
        ("https://www.jisilu.cn/data/qdii/#qdiia", ["亚洲市场"]),
    ]

    # 重试配置
    MAX_RETRIES = int(os.getenv("SPIDER_MAX_RETRIES", "3"))
    RETRY_INTERVAL = int(os.getenv("SPIDER_RETRY_INTERVAL", "30"))

    @property
    def output_clean_path(self) -> Path:
        return self.DATA_DIR / self.OUTPUT_CLEAN

    @property
    def output_filtered_path(self) -> Path:
        return self.DATA_DIR / self.OUTPUT_FILTERED


# ──────────────────────────────────────────
# 邮件配置
# ──────────────────────────────────────────
class MailConfig:
    SMTP_SERVER = os.getenv("SMTP_SERVER", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    MAIL_SENDER = os.getenv("MAIL_SENDER", "")
    MAIL_SENDER_NAME = os.getenv("MAIL_SENDER_NAME", "QDII基金监控系统")
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"


# ──────────────────────────────────────────
# 数据筛选默认配置
# ──────────────────────────────────────────
class FilterConfig:
    PREMIUM_THRESHOLD = float(os.getenv("PREMIUM_THRESHOLD", "3.5"))
    DEFAULT_STATUS_FILTER = os.getenv("DEFAULT_STATUS_FILTER", "all")
    REFRESH_COOLDOWN = int(os.getenv("REFRESH_COOLDOWN", "30"))


# ──────────────────────────────────────────
# 快照保留配置
# ──────────────────────────────────────────
class SnapshotConfig:
    KEEP_DAYS = int(os.getenv("SNAPSHOT_KEEP_DAYS", "30"))


# ──────────────────────────────────────────
# 日志配置
# ──────────────────────────────────────────
class LogConfig:
    LEVEL = os.getenv("LOG_LEVEL", "INFO")
    FILE = _env_path("LOG_FILE", "logs/qdii.log")


# ──────────────────────────────────────────
# 便捷导出
# ──────────────────────────────────────────
flask = FlaskConfig()
db = DBConfig()
spider = SpiderConfig()
mail = MailConfig()
filter_cfg = FilterConfig()
log_cfg = LogConfig()
snapshot_cfg = SnapshotConfig()
