"""
任务调度器 - 基于 APScheduler
所有路径通过 config.spider 管理，无硬编码。
"""
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from extensions import db
from models import TaskSchedule, TaskLog
from apps.notify import notification_service

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    QDII 定时任务调度器。

    使用 APScheduler BackgroundScheduler，支持：
    - 从数据库加载已有任务
    - 动态添加/删除/启停任务
    - 执行时抓取数据 → 筛选 → 发送邮件
    """

    def __init__(self):
        self.scheduler: BackgroundScheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self.notify_svc = notification_service

    # ──────────────────────────────────────────
    # 生命周期
    # ──────────────────────────────────────────

    def init_scheduler(self, app) -> None:
        """
        在 Flask app context 中初始化调度器，加载数据库中的活跃任务。
        必须在 Flask 应用创建后调用。
        """
        with app.app_context():
            tasks = TaskSchedule.query.filter_by(is_active=True).all()
            for task in tasks:
                self.add_job(task)

            if tasks:
                self.scheduler.start()
                logger.info(f"调度器启动，已加载 {len(tasks)} 个活跃任务")
            else:
                logger.info("调度器初始化完成，当前无活跃任务")

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("调度器已关闭")

    # ──────────────────────────────────────────
    # 任务 CRUD
    # ──────────────────────────────────────────

    def add_job(self, task: TaskSchedule) -> Optional:
        """
        向调度器添加一个任务。

        参数:
            task: TaskSchedule 模型实例
        """
        try:
            trigger = CronTrigger.from_crontab(task.cron_expression)
        except Exception as e:
            logger.error(f"无效的 Cron 表达式 [{task.cron_expression}]: {e}")
            raise ValueError(f"无效的 Cron 表达式: {task.cron_expression}")

        job = self.scheduler.add_job(
            func=self._run_scheduled_report,
            trigger=trigger,
            args=[task.id],
            id=str(task.id),
            replace_existing=True,
        )
        logger.info(f"任务已添加: ID={task.id}, cron={task.cron_expression}")
        return job

    def remove_job(self, task_id: int) -> bool:
        """从调度器中移除任务"""
        try:
            self.scheduler.remove_job(str(task_id))
            logger.info(f"任务已移除: ID={task_id}")
            return True
        except Exception:
            return False

    # ──────────────────────────────────────────
    # 定时任务执行体
    # ──────────────────────────────────────────

    def _run_scheduled_report(self, task_id: int, is_test: bool = False) -> bool:
        """
        定时任务执行体：
        1. 抓取数据
        2. 保存历史快照
        3. 筛选数据
        4. 发送多渠道通知
        5. 记录日志
        """
        from flask import current_app, has_app_context

        logger.info(f"{'[测试]' if is_test else ''}开始执行任务 ID={task_id}")
        status = "success"
        error_msg = None
        filtered_count = 0

        try:
            if not has_app_context():
                logger.error("无 Flask app context，无法执行定时任务")
                return False

            task = TaskSchedule.query.get(task_id)
            if not task:
                logger.error(f"任务 ID={task_id} 不存在")
                return False

            recipients = task.get_recipients_list()
            conditions = task.get_conditions()

            # ── 步骤 1：抓取数据 ────────────────────────────
            import config

            max_retries = config.spider.MAX_RETRIES if not is_test else 1
            retry_interval = config.spider.RETRY_INTERVAL

            success = False
            for attempt in range(max_retries):
                try:
                    from apps.spider import run_workflow

                    df_filtered, _ = run_workflow(
                        premium_min=conditions.get("premium_min"),
                        status_filter=conditions.get("status_filter"),
                    )
                    success = True
                    break
                except Exception as e:
                    logger.warning(f"抓取失败（尝试 {attempt+1}/{max_retries}）: {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_interval)

            if not success:
                self._send_alert(
                    recipients=recipients,
                    title="数据抓取失败",
                    content=f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            "数据抓取失败，已重试多次，请检查系统日志。",
                )
                status = "failed"
                error_msg = "数据抓取失败"
                return False

            # ── 步骤 2：保存历史快照 ─────────────────────
            try:
                from models import FundSnapshot

                FundSnapshot.save_from_df(df_filtered)
                # 清理过期快照
                deleted = FundSnapshot.cleanup_old_snapshots(
                    config.snapshot_cfg.KEEP_DAYS
                )
                if deleted > 0:
                    logger.info(f"已清理 {deleted} 条过期快照")
            except Exception as e:
                logger.warning(f"快照保存失败（非致命）: {e}")

            # ── 步骤 3：发送通知 ─────────────────────────
            if not df_filtered.empty:
                filtered_count = len(df_filtered)

                # 获取带变化对比的数据
                try:
                    from models import FundSnapshot

                    fund_list = FundSnapshot.compare_today_vs_yesterday()
                    # 只取符合条件的基金
                    fund_codes = set(df_filtered["代码"].astype(str).tolist())
                    fund_list = [f for f in fund_list if f["fund_code"] in fund_codes]
                except Exception:
                    fund_list = df_filtered.to_dict("records")

                # 发送多渠道通知
                result = self.notify_svc.send_qdii_report(
                    funds=fund_list,
                    conditions=conditions,
                    recipients=recipients,
                    show_changes=True,
                )
                if "error" in result:
                    logger.error(f"通知发送失败: {result['error']}")
                else:
                    logger.info(f"通知发送结果: {result.get('message', '')}")
            else:
                logger.info("无符合条件数据，跳过通知发送")

            # ── 步骤 4：更新任务执行时间 ──────────────────
            task.last_run = datetime.now()
            db.session.commit()

        except Exception as e:
            logger.error(f"任务执行异常: {e}", exc_info=True)
            status = "error"
            error_msg = str(e)

        finally:
            if has_app_context():
                try:
                    from models import TaskLog

                    log = TaskLog(
                        task_id=task_id,
                        run_time=datetime.now(),
                        filtered_count=filtered_count,
                        status=status,
                        error_message=error_msg,
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception as e:
                    logger.error(f"日志写入失败: {e}")
                    db.session.rollback()

        return status == "success"

    def _send_alert(self, recipients: list, title: str, content: str):
        """发送告警通知"""
        try:
            self.notify_svc.send_alert(
                title=title,
                content=content,
                recipients=recipients,
            )
        except Exception as e:
            logger.error(f"告警发送失败: {e}")

    # ──────────────────────────────────────────
    # 手动触发（供 API 测试用）
    # ──────────────────────────────────────────

    def trigger_test(
        self,
        recipients: list[str],
        conditions: dict,
        task_id: int = -1,
    ) -> bool:
        """手动触发一次任务执行（用于测试）"""
        # 临时构造一个任务对象
        from apps.spider import run_workflow

        try:
            df_filtered, _ = run_workflow(
                premium_min=conditions.get("premium_min"),
                status_filter=conditions.get("status_filter"),
            )
            # 保存快照
            try:
                from models import FundSnapshot
                FundSnapshot.save_from_df(df_filtered)
            except Exception as e:
                logger.warning(f"快照保存失败: {e}")

            # 获取带变化对比的数据
            try:
                from models import FundSnapshot
                fund_list = FundSnapshot.compare_today_vs_yesterday()
                fund_codes = set(df_filtered["代码"].astype(str).tolist())
                fund_list = [f for f in fund_list if f["fund_code"] in fund_codes]
            except Exception:
                fund_list = df_filtered.to_dict("records")

            if not df_filtered.empty:
                self.notify_svc.send_qdii_report(
                    recipients=recipients,
                    funds=fund_list,
                    conditions=conditions,
                    show_changes=True,
                )
            else:
                self.notify_svc.send_alert(
                    title="QDII 测试 - 无符合条件数据",
                    content=f"执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            "本次执行未找到符合筛选条件的数据。",
                    recipients=recipients,
                )
            return True
        except Exception as e:
            logger.error(f"手动触发失败: {e}")
            raise
