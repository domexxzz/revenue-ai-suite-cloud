"""RFM (Recency, Frequency, Monetary) segmentation engine.

Scores each customer on three dimensions (1-5 each) and assigns one of
eight business-meaningful segments used in the Customer Intelligence view.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

# Segment definitions ordered from most to least valuable
SEGMENT_META: dict[str, dict] = {
    "Champions": {
        "label": "Champions",
        "color": "#10B981",
        "description": "ซื้อล่าสุด, ซื้อบ่อย, ใช้จ่ายสูง — Hero customers",
        "action": "ให้รางวัล VIP, ขอ review, ให้เป็น brand ambassador",
        "priority": 1,
    },
    "Loyal Customers": {
        "label": "Loyal Customers",
        "color": "#3B82F6",
        "description": "ซื้อบ่อยและใช้จ่ายสูงต่อเนื่อง",
        "action": "Upsell premium items, loyalty program, early access offers",
        "priority": 2,
    },
    "Potential Loyalists": {
        "label": "Potential Loyalists",
        "color": "#8B5CF6",
        "description": "ลูกค้าใหม่ที่มาซื้อหลายครั้งแล้ว",
        "action": "Membership offer, ส่ง personalised recommendation",
        "priority": 3,
    },
    "Recent Customers": {
        "label": "Recent Customers",
        "color": "#06B6D4",
        "description": "ซื้อล่าสุดแต่ยังมาไม่บ่อย",
        "action": "Welcome series, แนะนำเมนู best-seller, กระตุ้นซื้อครั้งที่ 2",
        "priority": 4,
    },
    "Promising": {
        "label": "Promising",
        "color": "#F59E0B",
        "description": "Recency ดี แต่ยังไม่บ่อยหรือยังไม่ใช้จ่ายมาก",
        "action": "Bundle deals, flash sale เฉพาะกลุ่ม, referral program",
        "priority": 5,
    },
    "Need Attention": {
        "label": "Need Attention",
        "color": "#F97316",
        "description": "เคยซื้อบ่อยและใช้จ่ายสูง แต่เริ่มห่างหาย",
        "action": "Win-back offer ทันที, survey ความพึงพอใจ, ส่วนลดพิเศษ",
        "priority": 6,
    },
    "At Risk": {
        "label": "At Risk",
        "color": "#EF4444",
        "description": "ลูกค้าเก่าคุณภาพดีที่กำลังจะหายไป",
        "action": "Urgent win-back campaign, โทรหา / LINE ส่วนตัว, offer ขนาดใหญ่",
        "priority": 7,
    },
    "Lost": {
        "label": "Lost",
        "color": "#6B7280",
        "description": "ไม่มาซื้อนานมากแล้ว มูลค่าต่ำ",
        "action": "Re-engage ด้วยต้นทุนต่ำ (email, LINE broadcast) หรือ deprioritise",
        "priority": 8,
    },
}


def _score_quantile(series: pd.Series, n: int = 5, ascending: bool = True) -> pd.Series:
    """Assign 1-n scores based on quantile rank. ascending=False → lower value = higher score."""
    labels = list(range(1, n + 1)) if ascending else list(range(n, 0, -1))
    try:
        return pd.qcut(series, q=n, labels=labels, duplicates="drop").astype(int)
    except ValueError:
        # Fallback when not enough distinct values
        pct = series.rank(pct=True)
        bins = np.linspace(0, 1, n + 1)
        return pd.cut(pct, bins=bins, labels=labels, include_lowest=True).astype(int)


def _assign_segment(r: int, f: int, m: int) -> str:
    rf = (r + f) / 2
    if r >= 5 and f >= 4 and m >= 4:
        return "Champions"
    if f >= 4 and m >= 3:
        return "Loyal Customers"
    if r >= 4 and f <= 3:
        return "Potential Loyalists"
    if r == 5 and f <= 2:
        return "Recent Customers"
    if r >= 3 and f <= 2:
        return "Promising"
    if r <= 3 and f >= 2 and m >= 3:
        return "Need Attention"
    if r <= 2 and f >= 3 and m >= 3:
        return "At Risk"
    return "Lost"


def compute_rfm(
    df: pd.DataFrame,
    snapshot_date: dt.date | None = None,
    customer_col: str = "customer_id",
    date_col: str = "order_time",
    monetary_col: str = "net_sales",
) -> pd.DataFrame:
    """
    Compute RFM table from a transactions DataFrame.

    Returns a DataFrame indexed by customer_id with columns:
        recency_days, frequency, monetary, r_score, f_score, m_score,
        rfm_score (str e.g. '554'), rfm_total (int), segment
    """
    if df.empty or customer_col not in df.columns:
        return pd.DataFrame()

    snap = pd.Timestamp(snapshot_date) if snapshot_date else pd.Timestamp.now()

    rfm = (
        df.groupby(customer_col)
        .agg(
            last_order=(date_col, "max"),
            frequency=(date_col, "count"),
            monetary=(monetary_col, "sum"),
        )
        .reset_index()
    )
    rfm["recency_days"] = (snap - rfm["last_order"]).dt.days.clip(lower=0)

    # Score: recency — fewer days = higher score (ascending=False)
    rfm["r_score"] = _score_quantile(rfm["recency_days"], ascending=False)
    rfm["f_score"] = _score_quantile(rfm["frequency"], ascending=True)
    rfm["m_score"] = _score_quantile(rfm["monetary"], ascending=True)

    rfm["rfm_score"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)
    rfm["rfm_total"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    rfm["segment"] = rfm.apply(lambda row: _assign_segment(row["r_score"], row["f_score"], row["m_score"]), axis=1)
    rfm["segment_color"] = rfm["segment"].map(lambda s: SEGMENT_META[s]["color"])
    rfm["segment_priority"] = rfm["segment"].map(lambda s: SEGMENT_META[s]["priority"])

    return rfm.sort_values("rfm_total", ascending=False).reset_index(drop=True)


def label_transactions(df: pd.DataFrame, rfm: pd.DataFrame, customer_col: str = "customer_id") -> pd.DataFrame:
    """Merge RFM segments back into the transactions DataFrame."""
    if rfm.empty:
        return df
    seg_map = rfm.set_index(customer_col)["segment"]
    df = df.copy()
    df["customer_segment"] = df[customer_col].map(seg_map).fillna("Promising")
    return df


def rfm_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    """Aggregate RFM by segment for display."""
    if rfm.empty:
        return pd.DataFrame()
    agg = (
        rfm.groupby("segment")
        .agg(
            customers=("customer_id", "count"),
            avg_recency=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            total_revenue=("monetary", "sum"),
        )
        .reset_index()
    )
    agg["avg_recency"] = agg["avg_recency"].round(0).astype(int)
    agg["avg_frequency"] = agg["avg_frequency"].round(1)
    agg["avg_monetary"] = agg["avg_monetary"].round(0)
    agg["total_revenue"] = agg["total_revenue"].round(0)
    agg["color"] = agg["segment"].map(lambda s: SEGMENT_META.get(s, {}).get("color", "#6B7280"))
    agg["priority"] = agg["segment"].map(lambda s: SEGMENT_META.get(s, {}).get("priority", 9))
    agg["action"] = agg["segment"].map(lambda s: SEGMENT_META.get(s, {}).get("action", ""))
    return agg.sort_values("priority").reset_index(drop=True)
