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
    尝试用用户名密码登录 jisilu.cn。
    返回是否登录成功。

    注意：集思录可能在多次失败后要求图形验证码，
    此时登录会超时，但 Session Cookie 仍可能保存部分有效数据。
    """
    creds = _get_login_credentials()
    if not creds:
        logger.warning("未配置 JISILU_USERNAME/JISILU_PASSWORD，跳过自动登录")
        return False

    username, password = creds

    try:
        page = context.new_page()
        page.goto("https://www.jisilu.cn/login/", timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)  # 等待 JS 初始化

        # 检查是否已跳转到主页（Cookie 已登录）
        if page.url != "https://www.jisilu.cn/login/" and "/login" not in page.url:
            logger.info("Cookie 已登录，跳过表单登录")
            page.close()
            return True

        # 检查是否有登录表单
        try:
            page.wait_for_selector('input[name="user_name"]', timeout=3000)
        except Exception:
            logger.warning("登录页面无 user_name 表单，可能已登录或页面结构变更")
            page.close()
            return False

        page.fill('input[name="user_name"]', username)
        page.fill('input[name="password"]', password)

        # 提交登录
        page.click('a.btn.btn-jisilu')
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        logged_in = _is_logged_in(context)
        page.close()

        if logged_in:
            _save_cookies(context)
            logger.info("jisilu.cn 用户名密码登录成功")
            return True
        else:
            logger.error("jisilu.cn 用户名密码登录失败（可能触发了验证码）")
            return False

    except Exception as e:
        logger.error(f"jisilu.cn 登录过程出错: {e}")
        return False


def _fetch_api(suffix: str, headers: dict) -> list[dict]:
    """通过 JSON API 获取指定市场数据。返回空列表表示需要重新登录。"""
    import requests
    url = f"https://www.jisilu.cn/data/qdii/qdii_list/{suffix}"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("isError"):
                msg = data.get("msg", "")
                if "登录" in msg:
                    logger.warning(f"API {suffix}: Cookie 已过期，需要重新登录")
                    return []  # 触发重新登录
                logger.warning(f"API {suffix} 错误: {msg}")
                return []
            return data.get("rows", [])
        elif r.status_code in (401, 403):
            logger.warning(f"API {suffix}: HTTP {r.status_code}，Cookie 无效")
            return []
        else:
            logger.warning(f"API {suffix} 返回状态码 {r.status_code}")
            return []
    except Exception as e:
        logger.warning(f"API {suffix} 请求失败: {e}")
        return []


def _api_rows_to_df(rows: list, source: str) -> pd.DataFrame:
    """将 API 行数据转换为 DataFrame。"""
    records = []
    for row in rows:
        cell = row.get("cell", {})
        premium_str = cell.get("nav_discount_rt", "")
        # 溢价率可能是 "-" 或空
        try:
            premium = float(premium_str)
        except (TypeError, ValueError):
            premium = None
        records.append({
            "代码": cell.get("fund_id", ""),
            "名称": cell.get("fund_nm_color", "") or cell.get("fund_nm", ""),
            "溢价率": premium,
            "溢价率_str": premium_str,
            "当前价": cell.get("price", ""),
            "最新净值": cell.get("fund_nav", ""),
            "净值日期": cell.get("nav_dt", ""),
            "T-2净值": cell.get("fund_nav", ""),
            "T-2净值日期": cell.get("nav_dt", ""),
            "参考指数": cell.get("index_nm", ""),
            "参考指数涨跌幅": cell.get("ref_increase_rt", ""),
            "申购状态": cell.get("apply_status", ""),
            "赎回状态": cell.get("redeem_status", ""),
            "管理费": cell.get("m_fee", ""),
            "托管费": cell.get("mt_fee", ""),
            "成交额(万)": cell.get("volume", ""),
            "溢价率_t1": None,  # API 只提供 T-2
            "来源": source,
        })
    return pd.DataFrame(records)


def fetch_qdii_data() -> pd.DataFrame:
    """
    通过 JSON API 抓取 jisilu.cn QDII 基金数据。
    优先使用 API，失败则降级为 Playwright HTML 抓取。
    """
    import requests

    config.spider.DATA_DIR.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_raw = []

    # ── 构建请求头（含 Cookie） ─────────────────────────────────
    base_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.jisilu.cn/data/qdii/",
    }
    # 从 Cookie 缓存加载
    cookie_str = ""
    if _COOKIE_FILE.exists():
        try:
            cookies = pickle.loads(_COOKIE_FILE.read_bytes())
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
        except Exception as e:
            logger.warning(f"加载 Cookie 失败: {e}")

    if cookie_str:
        base_headers["Cookie"] = cookie_str

    # ── API 抓取（3个市场标签页） ─────────────────────────────
    # 对应关系：#qdiie → E(欧美) + C(商品), #qdiia → A(亚洲)
    api_map = [
        ("E", "欧美市场"),
        ("C", "商品市场"),
        ("A", "亚洲市场"),
    ]

    api_success = False
    for suffix, label in api_map:
        rows = _fetch_api(suffix, base_headers)
        if rows:
            df = _api_rows_to_df(rows, label)
            if not df.empty:
                all_raw.append(df)
                logger.info(f"抓取 [{label}] 成功: {len(df)} 条")
                api_success = True
        else:
            logger.warning(f"抓取 [{label}] 返回空数据")

    # ── Cookie 过期：尝试用户名密码登录 ───────────────────────
    if not api_success and _get_login_credentials():
        logger.info("Cookie 可能过期，尝试用户名密码登录...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                if _login(context):
                    # 登录成功，重新构建 Cookie
                    new_cookies = context.cookies()
                    _save_cookies(context)
                    # 从新保存的 Cookie 文件重新加载（确保格式正确）
                    new_cache = pickle.loads(_COOKIE_FILE.read_bytes())
                    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in new_cache)
                    base_headers["Cookie"] = cookie_str
                    # 重试 API
                    for suffix, label in api_map:
                        rows = _fetch_api(suffix, base_headers)
                        if rows:
                            df = _api_rows_to_df(rows, label)
                            if not df.empty:
                                all_raw.append(df)
                                logger.info(f"重试抓取 [{label}] 成功: {len(df)} 条")
                                api_success = True
                browser.close()
        except Exception as e:
            logger.error(f"用户名密码登录尝试失败: {e}")

    # ── 降级：Playwright HTML 抓取 ─────────────────────────────
    if not api_success:
        logger.warning("API 抓取失败，降级为 Playwright HTML 抓取")
        _fetch_via_playwright(all_raw, now_str)

    if all_raw:
        df_raw = pd.concat(all_raw, ignore_index=True)
        raw_path = config.spider.DATA_DIR / f"qdii_all_raw_{now_str}.csv"
        df_raw.to_csv(raw_path, index=False, encoding="utf-8-sig")
        logger.info(f"原始数据已保存: {raw_path}")
        return df_raw
    else:
        logger.error("未抓取到任何数据")
        return pd.DataFrame()


def _fetch_via_playwright(all_raw: list, now_str: str) -> None:
    """降级方案：通过 Playwright 解析 HTML 获取数据。"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            _load_cached_cookies(context)

            for url, labels in config.spider.JISILU_URLS:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_selector("table", timeout=15000)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                tables = soup.find_all("table")

                if not tables:
                    continue

                for i, label in enumerate(labels):
                    if i >= len(tables):
                        break
                    try:
                        df = pd.read_html(io.StringIO(str(tables[i])), header=1)[0]
                        df.insert(0, "来源", label)
                        all_raw.append(df)
                        logger.info(f"Playwright 抓取 [{label}]: {len(df)} 条")
                    except Exception as e:
                        logger.warning(f"表格解析失败 [{label}]: {e}")

            browser.close()
    except Exception as e:
        logger.error(f"Playwright 降级抓取失败: {e}")
