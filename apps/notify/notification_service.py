"""
统一通知服务
整合多渠道配置、模板渲染、统一发送接口。
"""
import logging
from datetime import datetime
from typing import Optional

from extensions import db
from models import NotifyChannel, NotifyTemplate
from .sendNotify import (
    send_notify,
    get_all_channels,
    CHANNEL_NAMES,
    cfg as notify_cfg,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    统一通知服务。

    负责：
    1. 从 DB 加载渠道配置（运行时覆盖 sendNotify 的 env 配置）
    2. 应用通知模板
    3. 触发多渠道发送
    """

    def __init__(self):
        pass

    def _load_channel_config_to_notify(self, channel_id: str, config: dict) -> None:
        """将 DB 配置映射到 sendNotify 的 ChannelConfig"""
        mapping = {
            "email": {
                "smtp_server": config.get("smtp_server"),
                "smtp_port": config.get("smtp_port", 587),
                "smtp_username": config.get("username") or config.get("smtp_username"),
                "smtp_password": config.get("password") or config.get("smtp_password"),
                "smtp_sender": config.get("sender_email") or config.get("smtp_username"),
                "smtp_use_ssl": config.get("use_ssl", True),
            },
            "dingtalk": {
                "dingtalk_token": config.get("token"),
                "dingtalk_secret": config.get("secret"),
            },
            "feishu": {
                "feishu_token": config.get("token"),
                "feishu_secret": config.get("secret"),
            },
            "wecom": {
                "wecom_corp_id": config.get("corp_id"),
                "wecom_agent_id": config.get("agent_id"),
                "wecom_corp_secret": config.get("corp_secret"),
            },
            "telegram": {
                "telegram_token": config.get("token"),
                "telegram_chat_id": config.get("chat_id"),
            },
            "pushplus": {
                "pushplus_token": config.get("token"),
            },
            "serverchan": {
                "serverchan_sckey": config.get("sckey"),
            },
            "bark": {
                "bark_key": config.get("key"),
            },
            "igot": {
                "igot_key": config.get("key"),
            },
            "webhook": {
                "custom_webhook": config.get("webhook_url"),
            },
        }
        if channel_id in mapping:
            for key, value in mapping[channel_id].items():
                if value:
                    setattr(notify_cfg, key, value)

    def _get_enabled_channels(self) -> list[str]:
        """获取所有已启用的渠道 ID 列表"""
        channels = NotifyChannel.get_active_channels()
        return [ch.channel for ch in channels]

    def send_qdii_report(
        self,
        funds: list[dict],
        conditions: dict,
        recipients: list[str] = None,
        show_changes: bool = True,
    ) -> dict:
        """
        发送 QDII 基金报告。

        参数:
            funds: 基金数据列表，每条包含 source/code/name/premium/status/change
            conditions: 筛选条件
            recipients: 邮件收件人列表
            show_changes: 是否显示溢价率变化

        返回: sendNotify 的结果字典
        """
        template = NotifyTemplate.get_default()
        if not template:
            return {"error": "未找到通知模板"}

        today = datetime.now().strftime("%Y-%m-%d")

        # 准备渲染变量
        count = len(funds)
        premium_min = conditions.get("premium_min", "?")
        status_filter = conditions.get("status_filter", "全部")

        # 渲染表格
        if show_changes:
            rows = [
                "| 市场 | 代码 | 名称 | 溢价率 | 变化 | 状态 |",
                "|------|------|------|--------|------|------|"
            ]
            for f in funds:
                change = f.get("change")
                change_icon = ""
                change_str = ""
                if change is not None:
                    if change > 0:
                        change_icon = "🔺"
                    elif change < 0:
                        change_icon = "🔻"
                    change_str = f"{change_icon}{change:+.2f}%"
                premium = f.get("premium_today") or f.get("premium")
                premium_str = f"{premium:.2f}%" if premium is not None else "N/A"
                rows.append(
                    f"|{f.get('source', '')}|{f.get('fund_code', '')}|"
                    f"{f.get('fund_name', '')}|{premium_str}|"
                    f"{change_str}|{f.get('status', '')}|"
                )
            table_md = "\n".join(rows)
        else:
            table_md = "\n".join([
                f"- **{f.get('fund_name')}** ({f.get('fund_code')}) "
                f"溢价率 {f.get('premium', 'N/A')}%，状态：{f.get('status', '')}"
                for f in funds
            ])

        variables = {
            "date": today,
            "count": count,
            "table": table_md,
            "premium_min": premium_min,
            "status_filter": status_filter,
        }

        title, content = template.render(variables)

        # 加载渠道配置并发送
        return self._send(
            title=title,
            content=content,
            channels=self._get_enabled_channels(),
            recipients=recipients,
        )

    def send_alert(
        self,
        title: str,
        content: str,
        recipients: list[str] = None,
    ) -> dict:
        """发送告警消息（任务失败/抓取失败等）"""
        return self._send(
            title=f"[QDII告警] {title}",
            content=content,
            channels=self._get_enabled_channels(),
            recipients=recipients,
        )

    def send_test(
        self,
        channel: str,
        recipients: list[str] = None,
    ) -> dict:
        """发送测试消息到指定渠道"""
        from flask import has_app_context

        channel_model = NotifyChannel.get_by_channel(channel)
        if not channel_model:
            return {"error": f"未找到渠道: {channel}"}

        # 加载该渠道配置
        self._load_channel_config_to_notify(channel, channel_model.get_config())

        test_content = (
            f"这是一条来自 QDII 基金监控系统的测试消息。\n"
            f"发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"渠道：{CHANNEL_NAMES.get(channel, channel)}\n"
            f"如果您收到此消息，说明配置正确！"
        )

        try:
            from .sendNotify import CHANNEL_HANDLERS
            handler = CHANNEL_HANDLERS.get(channel)
            if not handler:
                return {"error": f"未知渠道: {channel}"}

            if channel == "email":
                ok = handler(f"QDII 测试消息", test_content, recipients or [])
            else:
                ok = handler(f"QDII 测试消息", test_content)

            if ok:
                return {"success": True, "message": f"{CHANNEL_NAMES.get(channel)} 测试消息发送成功"}
            return {"error": f"{CHANNEL_NAMES.get(channel)} 发送失败，请检查配置"}
        except Exception as e:
            logger.error(f"测试消息发送异常 [{channel}]: {e}")
            return {"error": str(e)}

    def _send(
        self,
        title: str,
        content: str,
        channels: list[str],
        recipients: list[str] = None,
    ) -> dict:
        """内部发送逻辑"""
        # 为每个渠道加载配置
        for ch in channels:
            ch_model = NotifyChannel.get_by_channel(ch)
            if ch_model:
                self._load_channel_config_to_notify(ch, ch_model.get_config())

        try:
            result = send_notify(
                title=title,
                content=content,
                channels=channels,
                recipients=recipients,
            )
            success_names = [CHANNEL_NAMES.get(c, c) for c in result["success"]]
            failed_names = [CHANNEL_NAMES.get(c, c) for c in result["failed"]]
            msg = f"成功: {', '.join(success_names)}" if success_names else ""
            if failed_names:
                msg += f"；失败: {', '.join(failed_names)}"
            logger.info(f"通知发送结果: {msg}")
            return {
                "success": result["success"],
                "failed": result["failed"],
                "message": msg,
            }
        except Exception as e:
            logger.error(f"通知发送异常: {e}")
            return {"error": str(e)}


# 全局单例
notification_service = NotificationService()
