"""
QDII 基金监控系统 - 入口脚本

用法:
  python main.py                     # 直接启动 Web 服务
  python main.py --crawl            # 仅运行爬虫并退出
  python main.py --snapshot         # 抓取数据并保存历史快照
  python main.py --help              # 查看帮助
"""
import sys
import argparse
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_crawl(save_snapshot: bool = True):
    """
    运行爬虫并可选保存历史快照。
    Snapshot 模式保存全部数据（不过滤溢价率）。
    """
    from apps.spider import run_workflow
    from models import FundSnapshot
    import config

    # Snapshot 保存全部数据；普通抓取走默认筛选门槛
    premium_min = None if save_snapshot else config.filter_cfg.PREMIUM_THRESHOLD

    logger.info("开始抓取 QDII 数据...")
    df, now_str = run_workflow(premium_min=premium_min)
    logger.info(f"抓取完成，共 {len(df)} 条数据（时间戳: {now_str}）")

    if save_snapshot and not df.empty:
        # 需要 Flask 应用上下文来访问数据库
        from apps.app_factory import create_app
        app = create_app()
        with app.app_context():
            saved = FundSnapshot.save_from_df(df)
            logger.info(f"历史快照已保存: {saved} 条")


def run_web():
    """启动 Web 服务"""
    from apps.app_factory import create_app
    import config

    app = create_app()
    logger.info(
        f"启动 Web 服务: http://{config.flask.HOST}:{config.flask.PORT}"
    )
    app.run(
        host=config.flask.HOST,
        port=config.flask.PORT,
        debug=config.flask.DEBUG,
        use_reloader=False,
    )


def main():
    parser = argparse.ArgumentParser(description="QDII 基金监控系统")
    parser.add_argument(
        "--crawl",
        action="store_true",
        help="仅运行爬虫，不启动 Web 服务",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="抓取数据并保存历史快照，然后退出",
    )
    args = parser.parse_args()

    if args.crawl:
        run_crawl(save_snapshot=False)
    elif args.snapshot:
        run_crawl(save_snapshot=True)
    else:
        run_web()


if __name__ == "__main__":
    main()
