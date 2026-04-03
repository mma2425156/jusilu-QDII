"""
数据解析器 - 清洗与筛选
"""
import logging
from pathlib import Path

import pandas as pd
import numpy as np

import config

logger = logging.getLogger(__name__)

# 目标列名（清洗后标准列名）
TARGET_COLS = ["代码", "名称", "T-2净值 溢价率", "申购状态", "来源"]
# jisilu.cn HTML 表格实际列名映射
HTML_COL_MAP = {
    "代码": "代码",
    "名称": "名称",
    "T-2净值 溢价率": "T-2净值 溢价率",  # 溢价率（需登录则显示"登录"）
    "申购状态": "申购状态",
    "来源": "来源",
}
# 需要过滤掉的占位符值
PLACEHOLDER_VALUES = {"登录", "会员", "-"}


def clean_and_extract(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗 DataFrame，统一列名，输出标准格式。

    支持两种数据格式：
    1. API 格式（JSON API）：列名含 "溢价率" (float), "溢价率_str",
       "代码", "名称", "申购状态", "来源"
    2. HTML 格式（降级抓取）：列名含 "T-2净值 溢价率" (带 % 符号，需过滤 "登录" 占位符)

    溢价率列需要登录才显示真实数据，未登录时显示"登录"/"会员"等占位符。
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    # ── 判断数据格式 ───────────────────────────────────────────
    has_api_premium = "溢价率" in df.columns and "溢价率_str" in df.columns
    has_html_premium = "T-2净值 溢价率" in df.columns

    if has_api_premium:
        # API 格式：溢价率已是数值（float 或 None）
        rate_col = "溢价率"
        df[rate_col] = pd.to_numeric(df[rate_col], errors="coerce")

        # 只保留有溢价率数值的行（过滤掉无法计算的）
        before = len(df)
        df = df.dropna(subset=[rate_col])
        after = len(df)
        if before != after:
            logger.info(f"过滤无溢价率数据行：{before} → {after}")

        # 统一列名
        if "T-2净值" in df.columns:
            df = df.rename(columns={"T-2净值": "净值"})

        out_cols = ["代码", "名称", "溢价率", "净值", "净值日期", "参考指数",
                    "参考指数涨跌幅", "申购状态", "赎回状态", "来源"]
        out_cols = [c for c in out_cols if c in df.columns]
        df = df[out_cols].copy()

    elif has_html_premium:
        # HTML 格式：需自动定位表头
        for i in range(min(5, len(df))):
            row_vals = df.iloc[i].astype(str).tolist()
            if all(col in row_vals for col in ["代码", "名称", "T-2净值 溢价率"]):
                df.columns = df.iloc[i].tolist()
                df = df.iloc[i + 1:].reset_index(drop=True)
                logger.info(f"自动表头定位成功，跳过前 {i+1} 行")
                break

        rate_col = "T-2净值 溢价率"
        status_col = "申购状态"

        # 过滤登录占位符行
        if rate_col in df.columns:
            df = df[~df[rate_col].isin(PLACEHOLDER_VALUES)].copy()
            logger.info(f"过滤登录占位符后剩余 {len(df)} 条")

        # 溢价率去掉 % 符号并转为数值
        if rate_col in df.columns:
            df[rate_col] = (
                df[rate_col]
                .replace("-", np.nan)
                .astype(str)
                .str.rstrip("%")
            )
            df[rate_col] = pd.to_numeric(df[rate_col], errors="coerce")

        # 清理申购状态字段
        if status_col in df.columns:
            df[status_col] = df[status_col].astype(str).str.strip()

        # 统一溢价率列名
        df = df.rename(columns={"T-2净值 溢价率": "溢价率"})

        out_cols = [c for c in TARGET_COLS if c in df.columns]
        df = df[out_cols].copy()
    else:
        logger.warning(f"无法识别数据格式，列名: {list(df.columns)}")

    # 去掉全空行
    df = df.dropna(subset=["代码", "名称"])
    return df


def filter_data(
    df: pd.DataFrame,
    premium_min: float = None,
    status_filter: str = None,
) -> pd.DataFrame:
    """
    根据条件筛选基金数据。

    参数:
        premium_min: 溢价率下限（默认取 config.filter_cfg.PREMIUM_THRESHOLD）
        status_filter: 申购状态过滤关键词（默认不过滤，返回全部）
                      常见值: "限", "开放", "暂停", "限100"
    """
    if df.empty:
        return df

    if premium_min is None:
        # 无门槛：返回全部清洗后数据
        df.to_csv(config.spider.output_clean_path, index=False, encoding="utf-8-sig")
        logger.info(f"无门槛筛选，清洗数据已保存: {config.spider.output_clean_path}")
        return df

    df = df.copy()
    # 溢价率筛选（NaN 不参与比较）
    mask_rate = df["溢价率"].fillna(-999) >= premium_min

    # 状态筛选
    if status_filter and status_filter != "all":
        mask_status = df["申购状态"].str.contains(status_filter, na=False)
        filtered = df[mask_rate & mask_status]
    else:
        filtered = df[mask_rate]

    # 保存筛选结果
    if not filtered.empty:
        # 保存到 qdii_tables/
        filtered.to_csv(config.spider.output_filtered_path, index=False, encoding="utf-8-sig")
        logger.info(f"筛选结果已保存: {config.spider.output_filtered_path}，共 {len(filtered)} 条")

    # 同时保存清洗后完整数据
    df.to_csv(config.spider.output_clean_path, index=False, encoding="utf-8-sig")
    logger.info(f"清洗数据已保存: {config.spider.output_clean_path}")

    return filtered


def run_workflow(
    premium_min: float = None,
    status_filter: str = None,
) -> tuple[pd.DataFrame, str]:
    """
    运行完整抓取 → 清洗 → 筛选流程。

    返回: (filtered_df, now_str)
    """
    from apps.spider.fetcher import fetch_qdii_data

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    df_raw = fetch_qdii_data()
    df_clean = clean_and_extract(df_raw)
    df_filtered = filter_data(df_clean, premium_min, status_filter)
    return df_filtered, now_str


# 本地 import 避免循环
from datetime import datetime
