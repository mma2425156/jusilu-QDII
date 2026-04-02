"""
API 蓝图 - 统一路由层
"""
from flask import Blueprint, request, jsonify, Response
import time
import json
import logging

from extensions import db
from models import TaskSchedule, TaskLog, EmailConfigModel
from apps.notify import email_service

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)


# ═══════════════════════════════════════════════════════
# 通用响应工具
# ═══════════════════════════════════════════════════════
def ok(data: dict = None, **kwargs):
    payload = {"status": "success"}
    if data:
        payload.update(data)
    payload.update(kwargs)
    return jsonify(payload)


def err(msg: str, code: int = 500):
    return jsonify({"status": "error", "message": msg}), code


# ═══════════════════════════════════════════════════════
# 邮件配置
# ═══════════════════════════════════════════════════════
@api_bp.route("/mail/config", methods=["GET", "POST"])
def mail_config():
    """GET: 获取邮件配置 / POST: 更新邮件配置（持久化到数据库）"""
    if request.method == "GET":
        cfg = EmailConfigModel.get_active()
        if cfg is None:
            return ok(config=None)
        if isinstance(cfg, EmailConfigModel):
            return ok(config=cfg.to_dict())
        return ok(config=cfg)

    data = request.get_json()
    if not data:
        return err("请求体不能为空", 400)

    required = ["smtp_server", "smtp_port", "smtp_username", "smtp_password", "sender_email"]
    for field in required:
        if not data.get(field):
            return err(f"缺少必填字段: {field}", 400)

    # 禁用旧的，插入新的
    EmailConfigModel.query.update({"is_active": False})
    new_cfg = EmailConfigModel(
        smtp_server=data["smtp_server"],
        smtp_port=int(data["smtp_port"]),
        smtp_username=data["smtp_username"],
        smtp_password=data["smtp_password"],
        sender_email=data["sender_email"],
        sender_name=data.get("sender_name", "QDII基金监控系统"),
        use_ssl=data.get("use_ssl", True),
        is_active=True,
    )
    db.session.add(new_cfg)
    db.session.commit()
    logger.info("邮件配置已保存到数据库")
    return ok(message="邮件配置已保存")


@api_bp.route("/mail/test", methods=["POST"])
def test_mail():
    """发送测试邮件"""
    data = request.get_json()
    recipient = data.get("recipient")
    if not recipient:
        return err("缺少收件人地址", 400)
    try:
        email_service.send_test(recipient)
        return ok(message="测试邮件发送成功")
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════════════
# 定时任务 CRUD
# ═══════════════════════════════════════════════════════
@api_bp.route("/tasks", methods=["GET", "POST"])
def list_or_create_tasks():
    """GET: 列出所有任务 / POST: 创建新任务"""
    if request.method == "GET":
        tasks = TaskSchedule.query.order_by(TaskSchedule.created_at.desc()).all()
        return ok(tasks=[t.to_dict() for t in tasks])

    data = request.get_json()
    if not data:
        return err("请求体不能为空", 400)
    if not data.get("cron_expression"):
        return err("缺少 cron_expression", 400)
    if not data.get("recipients"):
        return err("缺少 recipients", 400)

    recipients = data["recipients"]
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]
    if not recipients:
        return err("收件人不能为空", 400)

    task = TaskSchedule(
        cron_expression=data["cron_expression"],
        recipients=",".join(recipients),
        conditions=json.dumps({
            "premium_min": data.get("premium_min", 0),
            "status_filter": data.get("status_filter", "all"),
        }, ensure_ascii=False),
    )
    db.session.add(task)
    db.session.commit()

    # 添加到调度器
    try:
        from flask import current_app

        current_app.scheduler.add_job(task)
    except Exception as e:
        logger.warning(f"任务已保存到 DB，但调度器添加失败: {e}")

    return ok(task_id=task.id, message="任务创建成功")


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """删除任务"""
    task = TaskSchedule.query.get(task_id)
    if not task:
        return err("任务不存在", 404)

    db.session.delete(task)
    db.session.commit()

    try:
        from flask import current_app

        current_app.scheduler.remove_job(task_id)
    except Exception:
        pass

    return ok(message="任务已删除")


@api_bp.route("/tasks/<int:task_id>/status", methods=["POST"])
def toggle_task_status(task_id):
    """启用/停用任务"""
    task = TaskSchedule.query.get(task_id)
    if not task:
        return err("任务不存在", 404)

    data = request.get_json()
    task.is_active = bool(data.get("is_active", True))
    db.session.commit()

    try:
        from flask import current_app

        if task.is_active:
            current_app.scheduler.add_job(task)
        else:
            current_app.scheduler.remove_job(task_id)
    except Exception as e:
        logger.warning(f"任务状态更新，但调度器操作失败: {e}")

    return ok(message=f"任务已{'启用' if task.is_active else '停用'}")


@api_bp.route("/tasks/<int:task_id>/logs", methods=["GET"])
def get_task_logs(task_id):
    """获取任务执行日志"""
    logs = (
        TaskLog.query.filter_by(task_id=task_id)
        .order_by(TaskLog.run_time.desc())
        .limit(50)
        .all()
    )
    return ok(logs=[log.to_dict() for log in logs])


@api_bp.route("/tasks/test", methods=["POST"])
def test_task():
    """手动触发一次任务执行（测试用）"""
    data = request.get_json()
    if not data:
        return err("请求体不能为空", 400)

    recipients = data.get("recipients", [])
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]
    conditions = {
        "premium_min": data.get("premium_min", 0),
        "status_filter": data.get("status_filter", "all"),
    }

    try:
        from flask import current_app

        current_app.scheduler.trigger_test(
            recipients=recipients,
            conditions=conditions,
        )
        return ok(message="测试任务执行完成")
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════════════
# 数据刷新（SSE 进度推送）
# ═══════════════════════════════════════════════════════
@api_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    POST 方式刷新数据（兼容旧版前端 data.js）。
    返回 JSON 格式的筛选后数据（含溢价率变化对比）。
    """
    from flask import request
    import pandas as pd
    import config
    from models import FundSnapshot

    premium_min = request.form.get("premium_min", default=0.0, type=float)
    status_filter = request.form.get("status_filter", default="all")

    # 尝试从快照获取带变化的数据
    all_funds = []
    try:
        all_funds = FundSnapshot.compare_today_vs_yesterday()
    except Exception:
        pass

    # 若无快照，降级到 CSV
    if not all_funds:
        data_path = config.spider.output_clean_path
        if not data_path.exists():
            return jsonify({"status": "error", "message": "暂无数据，请先刷新"}), 404
        df = pd.read_csv(data_path)
        col_map = {"来源": "source", "代码": "code", "名称": "name",
                   "T-1溢价率": "premium_today", "申购状态": "status"}
        df = df.rename(columns=col_map)
        df["source"] = df.get("source", "")
        df["change"] = None
        all_funds = df.to_dict("records")

    # 筛选
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

    filtered.sort(key=lambda x: x.get("premium_today") or -999, reverse=True)

    from datetime import datetime
    return jsonify({
        "status": "success",
        "data": filtered,
        "message": f"共 {len(filtered)} 条",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


_refresh_lock_time = 0


@api_bp.route("/refresh-status")
def refresh_status():
    """SSE 端点：实时推送数据刷新进度"""
    global _refresh_lock_time

    def generate():
        global _refresh_lock_time
        try:
            yield f"data: {json.dumps({'status': 'processing', 'message': '准备抓取数据...'})}\n\n"
            time.sleep(0.3)

            # 冷却时间检查
            now = time.time()
            if now - _refresh_lock_time < 30:
                cooldown = int(30 - (now - _refresh_lock_time))
                yield f"data: {json.dumps({'status': 'error', 'message': f'刷新太频繁，请等待 {cooldown} 秒'})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'processing', 'message': '正在抓取数据...'})}\n\n"

            # 直接调用爬虫模块（不走 subprocess）
            from apps.spider import run_workflow
            import config

            df, _ = run_workflow(
                premium_min=config.filter_cfg.PREMIUM_THRESHOLD,
                status_filter=None,
            )
            _refresh_lock_time = now

            yield f"data: {json.dumps({'status': 'completed', 'message': f'抓取完成，共 {len(df)} 条数据，正在刷新页面...'})}\n\n"

        except Exception as e:
            logger.error(f"刷新出错: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ═══════════════════════════════════════════════════════
# 通知渠道管理
# ═══════════════════════════════════════════════════════
@api_bp.route("/notify/channels", methods=["GET"])
def list_channels():
    """获取所有通知渠道及其状态"""
    from models import NotifyChannel
    from apps.notify import get_all_channels

    # 合并 DB 中的自定义名称和启用状态
    all_channels = get_all_channels()
    for ch in all_channels:
        db_ch = NotifyChannel.get_by_channel(ch["id"])
        if db_ch:
            ch["name"] = db_ch.name
            ch["is_active"] = db_ch.is_active
            ch["is_default"] = db_ch.is_default
            ch["configured"] = bool(db_ch.get_config())

    return ok(channels=all_channels)


@api_bp.route("/notify/channels/<channel_id>", methods=["GET"])
def get_channel(channel_id):
    """获取指定渠道配置"""
    from models import NotifyChannel

    ch = NotifyChannel.get_by_channel(channel_id)
    if not ch:
        return err("渠道不存在", 404)
    return ok(channel=ch.to_dict())


@api_bp.route("/notify/channels/<channel_id>", methods=["POST"])
def save_channel(channel_id):
    """保存/更新渠道配置"""
    from models import NotifyChannel

    data = request.get_json()
    if not data:
        return err("请求体不能为空", 400)

    ch = NotifyChannel.get_by_channel(channel_id)
    if not ch:
        return err(f"未知渠道: {channel_id}", 404)

    # 更新配置
    config_data = ch.get_config()
    for key in ["token", "secret", "password", "smtp_server", "smtp_port",
                "username", "corp_id", "agent_id", "corp_secret", "chat_id",
                "sckey", "key", "webhook_url", "use_ssl", "sender_email"]:
        if key in data:
            config_data[key] = data[key]

    ch.set_config(config_data)
    ch.is_active = bool(data.get("is_active", ch.is_active))
    db.session.commit()

    return ok(message=f"{ch.name} 配置已保存")


@api_bp.route("/notify/channels/<channel_id>/test", methods=["POST"])
def test_channel(channel_id):
    """测试指定渠道是否配置正确"""
    from apps.notify import notification_service

    data = request.get_json() or {}
    recipients = data.get("recipients", [])

    result = notification_service.send_test(channel_id, recipients)
    if "error" in result:
        return err(result["error"])
    return ok(**result)


# ═══════════════════════════════════════════════════════
# 通知模板管理
# ═══════════════════════════════════════════════════════
@api_bp.route("/notify/templates", methods=["GET"])
def list_templates():
    """获取所有通知模板"""
    from models import NotifyTemplate

    templates = NotifyTemplate.query.order_by(NotifyTemplate.is_default.desc()).all()
    return ok(templates=[t.to_dict() for t in templates])


@api_bp.route("/notify/templates/<int:template_id>", methods=["GET"])
def get_template(template_id):
    """获取指定模板"""
    from models import NotifyTemplate

    t = NotifyTemplate.query.get(template_id)
    if not t:
        return err("模板不存在", 404)
    return ok(template=t.to_dict())


@api_bp.route("/notify/templates", methods=["POST"])
def create_template():
    """创建新模板"""
    from models import NotifyTemplate

    data = request.get_json()
    if not data or not data.get("name"):
        return err("模板名称不能为空", 400)

    if data.get("is_default"):
        NotifyTemplate.query.update({"is_default": False})

    t = NotifyTemplate(
        name=data["name"],
        title_template=data.get("title_template", "QDII基金报告 {{date}}"),
        content_template=data.get("content_template", "找到 **{{count}}** 条数据\n\n{{table}}"),
        is_default=bool(data.get("is_default")),
    )
    db.session.add(t)
    db.session.commit()
    return ok(message="模板已创建", template_id=t.id)


@api_bp.route("/notify/templates/<int:template_id>", methods=["PUT"])
def update_template(template_id):
    """更新模板"""
    from models import NotifyTemplate

    data = request.get_json()
    t = NotifyTemplate.query.get(template_id)
    if not t:
        return err("模板不存在", 404)

    if data.get("is_default"):
        NotifyTemplate.query.update({"is_default": False})

    for field in ["name", "title_template", "content_template", "is_default"]:
        if field in data:
            setattr(t, field, data[field])

    db.session.commit()
    return ok(message="模板已更新")


@api_bp.route("/notify/templates/<int:template_id>", methods=["DELETE"])
def delete_template(template_id):
    """删除模板"""
    from models import NotifyTemplate

    t = NotifyTemplate.query.get(template_id)
    if not t:
        return err("模板不存在", 404)
    if t.is_default:
        return err("不能删除默认模板", 400)

    db.session.delete(t)
    db.session.commit()
    return ok(message="模板已删除")


# ═══════════════════════════════════════════════════════
# 历史数据 API
# ═══════════════════════════════════════════════════════
@api_bp.route("/history/today", methods=["GET"])
def get_today_with_changes():
    """
    获取今日数据（带溢价率变化对比）。
    """
    from models import FundSnapshot

    changes = FundSnapshot.compare_today_vs_yesterday()
    return ok(
        funds=changes,
        total=len(changes),
        has_history=bool(changes and any(f["change"] is not None for f in changes)),
    )


@api_bp.route("/history/snapshot", methods=["POST"])
def save_snapshot():
    """
    保存当前清洗数据为快照（手动保存或定时任务调用）。
    """
    from models import FundSnapshot
    import pandas as pd
    import config

    data_path = config.spider.output_clean_path
    if not data_path.exists():
        return err("暂无数据可保存")

    df = pd.read_csv(data_path)
    # 标准化列名（兼容 API 格式）
    col_map = {
        "来源": "来源",
        "fund_id": "代码",
        "fund_nm": "名称",
        "price_t-1": "T-1溢价率",
        "subscribe_status": "申购状态",
    }
    # 映射列名
    for old, new in {"fund_id": "代码", "fund_nm": "名称"}.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    count = FundSnapshot.save_from_df(df)
    return ok(message=f"快照已保存，共 {count} 条数据")


@api_bp.route("/history/cleanup", methods=["POST"])
def cleanup_history():
    """
    清理过期快照数据。
    """
    from models import FundSnapshot

    data = request.get_json() or {}
    keep_days = int(data.get("keep_days", 30))
    deleted = FundSnapshot.cleanup_old_snapshots(keep_days)
    return ok(message=f"已清理 {deleted} 条过期快照")
