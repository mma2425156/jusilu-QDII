"""
数据抓取器 - Playwright 浏览器自动化
所有路径通过 config.spider 管理，无硬编码。
"""
import io
import logging
import os
import pickle
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

import config

logger = logging.getLogger(__name__)

# Cookie 缓存文件路径
_COOKIE_FILE = config.spider.DATA_DIR / ".jisilu_cookies.pkl"


def _get_login_credentials() -> tuple[str, str] | None:
    """从环境变量获取登录凭证。"""
    username = os.getenv("JISILU_USERNAME", "").strip()
    password = os.getenv("JISILU_PASSWORD", "").strip()
    if username and password:
        return username, password
    return None


def _load_cached_cookies(context) -> bool:
    """尝试加载缓存的登录 Cookie 到指定 context。"""
    if _COOKIE_FILE.exists():
        try:
            cookies = pickle.loads(_COOKIE_FILE.read_bytes())
            # 设置正确的 cookie domain
            for cookie in cookies:
                if "domain" not in cookie or not cookie["domain"]:
                    cookie["domain"] = ".jisilu.cn"
            context.add_cookies(cookies)
            logger.info("已加载缓存的登录 Cookie")
            return True
        except Exception as e:
            logger.warning(f"加载 Cookie 失败，将重新登录: {e}")
    return False


def _save_cookies(context) -> None:
    """保存登录 Cookie 到缓存文件。"""
    try:
        cookies = context.cookies()
        _COOKIE_FILE.write_bytes(pickle.dumps(cookies))
        logger.info("登录 Cookie 已缓存")
    except Exception as e:
        logger.warning(f"保存 Cookie 失败: {e}")


def _is_logged_in(context) -> bool:
    """检查是否已登录（检查页面是否包含用户信息元素）。"""
    try:
        page = context.new_page()
        page.goto("https://www.jisilu.cn/home/profile", timeout=10000)
        page.wait_for_load_state("networkidle", timeout=5000)
        html = page.content()
        page.close()
        # 已登录用户会看到用户信息
        return 'class="user-avatar"' in html or 'data-menu="user"' in html
    except Exception:
        return False


def _login(context) -> bool:
    """
    登录 jisilu.cn。
    返回是否登录成功。
    """
    creds = _get_login_credentials()
    if not creds:
        logger.warning("未配置 JISILU_USERNAME/JISILU_PASSWORD，无法自动登录")
        return False

    username, password = creds

    try:
        page = context.new_page()
        page.goto("https://www.jisilu.cn/login/", timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1000)  # 等待表单渲染

        # 找到登录表单并填写
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)

        # 提交登录
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=10000)

        logged_in = _is_logged_in(context)
        page.close()

        if logged_in:
            _save_cookies(context)
            logger.info("jisilu.cn 登录成功")
            return True
        else:
            logger.error("jisilu.cn 登录失败，请检查用户名密码")
            return False
    except Exception as e:
        logger.error(f"jisilu.cn 登录过程出错: {e}")
        return False


def fetch_qdii_data() -> pd.DataFrame:
    """
    使用 Playwright 抓取 jisilu.cn QDII 基金数据。
    返回合并后的原始 DataFrame。

    路径由 config.spider.DATA_DIR 控制，格式如 {PROJECT_ROOT}/qdii_tables/
    """
    # 确保数据目录存在
    config.spider.DATA_DIR.mkdir(parents=True, exist_ok=True)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_raw = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # 尝试使用缓存 Cookie，未登录则尝试自动登录
            if not _load_cached_cookies(context) and not _is_logged_in(context):
                if not _login(context):
                    logger.warning("未登录状态抓取，部分数据可能需要登录才能查看")

            for url, labels in config.spider.JISILU_URLS:
                page.goto(url, wait_until="networkidle")
                page.wait_for_selector("table", timeout=15000)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                tables = soup.find_all("table")

                if not tables:
                    logger.warning(f"{url} 未找到表格，跳过")
                    continue

                for i, label in enumerate(labels):
                    if i >= len(tables):
                        break
                    df = pd.read_html(io.StringIO(str(tables[i])), header=1)[0]
                    df.insert(0, "来源", label)
                    all_raw.append(df)
                    logger.info(f"抓取 [{label}] 成功: {len(df)} 条")

            # 登录成功则保存 Cookie
            if _is_logged_in(context):
                _save_cookies(context)

            browser.close()

        if all_raw:
            df_raw = pd.concat(all_raw, ignore_index=True)
            raw_path = config.spider.DATA_DIR / f"qdii_all_raw_{now_str}.csv"
            df_raw.to_csv(raw_path, index=False, encoding="utf-8-sig")
            logger.info(f"原始数据已保存: {raw_path}")
            return df_raw
        else:
            logger.error("未抓取到任何数据")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"Playwright 抓取失败: {e}")
        raise
