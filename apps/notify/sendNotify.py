"""
sendNotify - 多渠道通知模块
基于 QingLong sendNotify 设计，支持 10+ 通知渠道。

使用方式:
    from apps.notify.sendNotify import send_notify, notify

    # 发送文本消息
    send_notify('QDII 基金报告', '找到 5 只高溢价基金')
    notify('钉钉', '预警', '溢价率超过 5%')
"""
import os
import re
import json
import logging
import smtplib
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# 渠道配置（从环境变量读取，可被运行时配置覆盖）
# ──────────────────────────────────────────

class ChannelConfig:
    """通知渠道配置容器"""
    def __init__(self):
        self.dingtalk_token = os.getenv("DINGTALK_TOKEN", "")
        self.dingtalk_secret = os.getenv("DINGTALK_SECRET", "")
        self.feishu_token = os.getenv("FEISHU_TOKEN", "")
        self.feishu_secret = os.getenv("FEISHU_SECRET", "")
        self.wecom_corp_id = os.getenv("WECOM_CORP_ID", "")
        self.wecom_agent_id = os.getenv("WECOM_AGENT_ID", "")
        self.wecom_corp_secret = os.getenv("WECOM_CORP_SECRET", "")
        self.telegram_token = os.getenv("TELEGRAM_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.pushplus_token = os.getenv("PUSHPLUS_TOKEN", "")
        self.serverchan_sckey = os.getenv("SERVERCHAN_SCKEY", "")
        self.bark_key = os.getenv("BARK_KEY", "")
        self.igot_key = os.getenv("IGOT_KEY", "")
        self.smtp_server = os.getenv("SMTP_SERVER", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_sender = os.getenv("MAIL_SENDER", "")
        self.smtp_use_ssl = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
        self.custom_webhook = os.getenv("CUSTOM_WEBHOOK", "")

    def update(self, **kwargs):
        """运行时更新配置"""
        for key, value in kwargs.items():
            if hasattr(self, key) and value:
                setattr(self, key, value)


cfg = ChannelConfig()


# ──────────────────────────────────────────
# 通用工具
# ──────────────────────────────────────────

def is_empty(*values) -> bool:
    """检查是否有空值"""
    return all(bool(v) for v in values)


def http_post(url: str, data: dict = None,
              headers: dict = None, timeout: int = 10) -> dict:
    try:
        r = requests.post(url, data=data, headers=headers, timeout=timeout)
        return r.json()
    except Exception as e:
        logger.error(f"HTTP POST 失败 [{url}]: {e}")
        return {}


# ──────────────────────────────────────────
# 渠道 1：钉钉机器人
# ──────────────────────────────────────────

def send_dingtalk(title: str, content: str) -> bool:
    """
    发送钉钉机器人通知。

    配置方式（二选一）：
    1. 环境变量：DINGTALK_TOKEN（安全模式需同时设置 DINGTALK_SECRET）
    2. 运行时：notify('钉钉', title, content, dingtalk_token='xxx')
    """
    token = cfg.dingtalk_token
    secret = cfg.dingtalk_secret

    if not token:
        logger.warning("钉钉 token 未配置")
        return False

    url = f"https://oapi.dingtalk.com/robot/send?access_token={token}"

    # 安全模式：签名校验
    headers = {"Content-Type": "application/json"}
    if secret:
        import time, hmac, hashlib, base64
        timestamp = str(int(time.time() * 1000))
        sign_str = f"{timestamp}\n{secret}"
        sign = base64.b64encode(
            hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).digest()
        ).decode()
        url += f"&timestamp={timestamp}&sign={urllib.parse.quote(sign)}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"**{title}**\n\n{content.replace(chr(10), '  ' + chr(10))}"
        }
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        result = r.json()
        if result.get("errcode") == 0:
            logger.info(f"钉钉通知发送成功: {title}")
            return True
        else:
            logger.error(f"钉钉通知失败: {result.get('errmsg')}")
            return False
    except Exception as e:
        logger.error(f"钉钉通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 2：飞书机器人
# ──────────────────────────────────────────

def send_feishu(title: str, content: str) -> bool:
    """
    发送飞书机器人通知。

    配置：FEISHU_TOKEN（机器人 Webhook 地址中的 token 部分）
         FEISHU_SECRET（可选，加签密钥）
    """
    token = cfg.feishu_token
    if not token:
        logger.warning("飞书 token 未配置")
        return False

    # 获取 tenant_access_token
    url = f"https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    try:
        r = requests.post(url, json={"app_id": token, "app_secret": cfg.feishu_secret or ""}, timeout=10)
        resp = r.json()
        tenant_token = resp.get("tenant_access_token", "")
    except Exception as e:
        logger.error(f"飞书认证失败: {e}")
        return False

    headers = {"Authorization": f"Bearer {tenant_token}", "Content-Type": "application/json"}
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "purple"
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}}
            ]
        }
    }

    # 直接发卡片消息（简化版，不依赖复杂 webhook）
    try:
        webhook_url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{token}"
        r2 = requests.post(webhook_url, json={
            "msg_type": "text",
            "content": {"text": f"{title}\n{content}"}
        }, timeout=10)
        result = r2.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            logger.info(f"飞书通知发送成功: {title}")
            return True
        logger.error(f"飞书通知失败: {result}")
        return False
    except Exception as e:
        logger.error(f"飞书通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 3：企业微信
# ──────────────────────────────────────────

def send_wecom(title: str, content: str) -> bool:
    """
    发送企业微信应用通知。

    配置：WECOM_CORP_ID, WECOM_AGENT_ID, WECOM_CORP_SECRET
    """
    corp_id = cfg.wecom_corp_id
    agent_id = cfg.wecom_agent_id
    corp_secret = cfg.wecom_corp_secret

    if not all([corp_id, agent_id, corp_secret]):
        logger.warning("企业微信配置不完整")
        return False

    # 获取 access_token
    try:
        r = requests.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={"corpid": corp_id, "corpsecret": corp_secret},
            timeout=10
        )
        token_data = r.json()
        access_token = token_data.get("access_token")
        if not access_token:
            logger.error(f"企业微信获取 token 失败: {token_data}")
            return False
    except Exception as e:
        logger.error(f"企业微信认证异常: {e}")
        return False

    # 发送消息
    payload = {
        "touser": "@all",
        "msgtype": "textcard",
        "agentid": int(agent_id),
        "textcard": {
            "title": title,
            "description": content,
            "url": "https://github.com"
        }
    }

    try:
        r2 = requests.post(
            f"https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={"access_token": access_token},
            json=payload,
            timeout=10
        )
        result = r2.json()
        if result.get("errcode") == 0:
            logger.info(f"企业微信通知发送成功: {title}")
            return True
        logger.error(f"企业微信通知失败: {result}")
        return False
    except Exception as e:
        logger.error(f"企业微信通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 4：Telegram
# ──────────────────────────────────────────

def send_telegram(title: str, content: str) -> bool:
    """
    发送 Telegram Bot 通知。

    配置：TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    """
    token = cfg.telegram_token
    chat_id = cfg.telegram_chat_id

    if not all([token, chat_id]):
        logger.warning("Telegram 配置不完整")
        return False

    text = f"*{title}*\n\n{content}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
        result = r.json()
        if result.get("ok"):
            logger.info(f"Telegram 通知发送成功: {title}")
            return True
        logger.error(f"Telegram 通知失败: {result}")
        return False
    except Exception as e:
        logger.error(f"Telegram 通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 5：PushPlus（微信推送）
# ──────────────────────────────────────────

def send_pushplus(title: str, content: str) -> bool:
    """
    发送 PushPlus 微信推送。

    配置：PUSHPLUS_TOKEN
    """
    token = cfg.pushplus_token
    if not token:
        logger.warning("PushPlus token 未配置")
        return False

    try:
        r = requests.post(
            "http://www.pushplus.plus/send",
            data={
                "token": token,
                "title": title,
                "content": content,
                "template": "html"
            },
            timeout=10
        )
        result = r.json()
        if result.get("code") == 200:
            logger.info(f"PushPlus 通知发送成功: {title}")
            return True
        logger.error(f"PushPlus 通知失败: {result}")
        return False
    except Exception as e:
        logger.error(f"PushPlus 通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 6：Server酱（微信推送）
# ──────────────────────────────────────────

def send_serverchan(title: str, content: str) -> bool:
    """
    发送 Server酱 微信推送。

    配置：SERVERCHAN_SCKEY（GitHub SCKEY 或 Turbo SCKEY）
    """
    sckey = cfg.serverchan_sckey
    if not sckey:
        logger.warning("ServerChan SCKEY 未配置")
        return False

    # 判断是 Turbo 还是旧版
    if sckey.startswith("SCT"):
        url = f"https://sctapi.ftqq.com/{sckey}.send"
        data = {"title": title, "content": content}
    else:
        url = f"https://sc.ftqq.com/{sckey}.send"
        data = {"text": title, "desp": content}

    try:
        r = requests.post(url, data=data, timeout=10)
        result = r.json()
        if result.get("code") == 0 or result.get("errno") == 0:
            logger.info(f"ServerChan 通知发送成功: {title}")
            return True
        logger.error(f"ServerChan 通知失败: {result}")
        return False
    except Exception as e:
        logger.error(f"ServerChan 通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 7：Bark（iOS 推送）
# ──────────────────────────────────────────

def send_bark(title: str, content: str) -> bool:
    """
    发送 Bark iOS 推送。

    配置：BARK_KEY（Server URL，如 https://api.day.app/YOUR_KEY）
    """
    bark_key = cfg.bark_key
    if not bark_key:
        logger.warning("Bark key 未配置")
        return False

    # 自动补全 URL
    if not bark_key.startswith("http"):
        bark_key = f"https://api.day.app/{bark_key}"

    url = f"{bark_key}/{urllib.parse.quote(title)}/{urllib.parse.quote(content)}"

    try:
        r = requests.get(url, timeout=10)
        result = r.json()
        if result.get("code") == 200:
            logger.info(f"Bark 通知发送成功: {title}")
            return True
        logger.error(f"Bark 通知失败: {result}")
        return False
    except Exception as e:
        logger.error(f"Bark 通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 8：iGot
# ──────────────────────────────────────────

def send_igot(title: str, content: str) -> bool:
    """
    发送 iGot 推送。

    配置：IGOT_KEY
    """
    key = cfg.igot_key
    if not key:
        logger.warning("iGot key 未配置")
        return False

    try:
        r = requests.post(
            "https://push.hellyw.com/tokey",
            data={
                "title": title,
                "content": content,
                "tokey": key
            },
            timeout=10
        )
        if r.status_code == 200:
            logger.info(f"iGot 通知发送成功: {title}")
            return True
        logger.error(f"iGot 通知失败: {r.text}")
        return False
    except Exception as e:
        logger.error(f"iGot 通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 9：邮件 SMTP
# ──────────────────────────────────────────

def send_email(title: str, content: str, recipients: list = None) -> bool:
    """
    发送邮件通知。

    配置：SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
          MAIL_SENDER, SMTP_USE_SSL
    """
    if not all([cfg.smtp_server, cfg.smtp_username, cfg.smtp_password]):
        logger.warning("邮件 SMTP 配置不完整")
        return False

    if not recipients:
        recipients = [cfg.smtp_username]

    msg = MIMEMultipart()
    msg["From"] = f"{cfg.smtp_username}"
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = title

    # HTML 内容
    html_content = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; color: #333;">
    {content}
    <hr><p style="color:#888;font-size:12px;">来自 QDII 基金监控系统</p>
    </body></html>
    """
    msg.attach(MIMEText(html_content, "html"))

    try:
        if cfg.smtp_use_ssl:
            server = smtplib.SMTP_SSL(cfg.smtp_server, cfg.smtp_port)
        else:
            server = smtplib.SMTP(cfg.smtp_server, cfg.smtp_port)
            server.starttls()
        server.login(cfg.smtp_username, cfg.smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"邮件发送成功: {title} -> {recipients}")
        return True
    except Exception as e:
        logger.error(f"邮件发送异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道 10：自定义 Webhook
# ──────────────────────────────────────────

def send_webhook(title: str, content: str) -> bool:
    """
    发送自定义 Webhook（POST JSON）。

    配置：CUSTOM_WEBHOOK（URL）
    """
    webhook = cfg.custom_webhook
    if not webhook:
        logger.warning("自定义 Webhook 未配置")
        return False

    payload = {
        "title": title,
        "content": content,
        "time": __import__("datetime").datetime.now().isoformat()
    }

    try:
        r = requests.post(webhook, json=payload, timeout=10)
        if r.status_code < 400:
            logger.info(f"Webhook 通知发送成功: {title}")
            return True
        logger.error(f"Webhook 通知失败: {r.status_code} {r.text}")
        return False
    except Exception as e:
        logger.error(f"Webhook 通知异常: {e}")
        return False


# ──────────────────────────────────────────
# 渠道注册表
# ──────────────────────────────────────────

CHANNEL_HANDLERS = {
    "dingtalk": send_dingtalk,
    "feishu": send_feishu,
    "wecom": send_wecom,
    "telegram": send_telegram,
    "pushplus": send_pushplus,
    "serverchan": send_serverchan,
    "bark": send_bark,
    "igot": send_igot,
    "email": send_email,
    "webhook": send_webhook,
}

# 渠道中文名映射
CHANNEL_NAMES = {
    "dingtalk": "钉钉机器人",
    "feishu": "飞书机器人",
    "wecom": "企业微信",
    "telegram": "Telegram",
    "pushplus": "PushPlus",
    "serverchan": "Server酱",
    "bark": "Bark",
    "igot": "iGot",
    "email": "邮件",
    "webhook": "自定义 Webhook",
}


# ──────────────────────────────────────────
# 统一发送接口
# ──────────────────────────────────────────

def send_notify(
    title: str,
    content: str,
    channels: list = None,
    recipients: list = None,
    **channel_overrides,
) -> dict:
    """
    统一通知接口，发送给一个或多个渠道。

    参数:
        title: 通知标题
        content: 通知内容（支持 Markdown/HTML）
        channels: 要发送的渠道列表，如 ["email", "dingtalk", "pushplus"]
                  若为 None，则发送给所有已配置的渠道
        recipients: 邮件收件人列表（仅 email 渠道使用）
        **channel_overrides: 运行时覆盖渠道配置
                            如 dingtalk_token='xxx'

    返回:
        dict: {"success": ["email", "pushplus"], "failed": ["dingtalk"]}
    """
    # 更新运行时配置
    if channel_overrides:
        cfg.update(**channel_overrides)

    if channels is None:
        # 发送给所有已配置渠道
        channels = [
            name for name, handler in CHANNEL_HANDLERS.items()
            if _is_channel_configured(name)
        ]

    results = {"success": [], "failed": []}

    for channel in channels:
        handler = CHANNEL_HANDLERS.get(channel)
        if not handler:
            logger.warning(f"未知渠道: {channel}")
            results["failed"].append(channel)
            continue

        try:
            if channel == "email":
                ok = handler(title, content, recipients or [])
            else:
                ok = handler(title, content)
            if ok:
                results["success"].append(channel)
            else:
                results["failed"].append(channel)
        except Exception as e:
            logger.error(f"渠道 {channel} 发送异常: {e}")
            results["failed"].append(channel)

    return results


def _is_channel_configured(channel: str) -> bool:
    """检查渠道是否已配置"""
    config_map = {
        "dingtalk": cfg.dingtalk_token,
        "feishu": cfg.feishu_token,
        "wecom": cfg.wecom_corp_id,
        "telegram": cfg.telegram_token,
        "pushplus": cfg.pushplus_token,
        "serverchan": cfg.serverchan_sckey,
        "bark": cfg.bark_key,
        "igot": cfg.igot_key,
        "email": cfg.smtp_server,
        "webhook": cfg.custom_webhook,
    }
    return bool(config_map.get(channel))


def get_all_channels() -> list:
    """获取所有可用渠道及其配置状态"""
    return [
        {
            "id": channel_id,
            "name": CHANNEL_NAMES.get(channel_id, channel_id),
            "configured": _is_channel_configured(channel_id),
        }
        for channel_id in CHANNEL_HANDLERS
    ]


# 便捷别名
notify = send_notify
