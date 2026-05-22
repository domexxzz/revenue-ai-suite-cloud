"""Loyverse POS REST API connector.

Fetches receipts, customers, and items from the Loyverse API and normalises
them into the standard pandas DataFrame schema used by app.py.

Standard schema columns:
    order_id, order_time, branch, staff, customer_id, customer_segment,
    item, qty, gross, discount, net_sales, cost, margin
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any

import pandas as pd
import requests

BASE_URL = "https://api.loyverse.com/v1.0"
RATE_LIMIT_PAUSE = 0.25  # seconds between paginated requests
DEFAULT_MARGIN_RATIO = 0.40  # fallback when cost data unavailable

logger = logging.getLogger(__name__)


class LoyverseConnector:
    """Thin wrapper around the Loyverse REST API."""

    def __init__(self, api_token: str, timeout: int = 30) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        })
        self.timeout = timeout

    # ── internal helpers ────────────────────────────────────────────────────

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"
        resp = self.session.get(url, params=params or {}, timeout=self.timeout)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 5))
            logger.warning("Rate limited — waiting %ss", retry_after)
            time.sleep(retry_after)
            resp = self.session.get(url, params=params or {}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _paginate(
        self,
        endpoint: str,
        key: str,
        params: dict[str, Any] | None = None,
        limit: int = 250,
    ) -> list[dict]:
        params = {**(params or {}), "limit": limit}
        results: list[dict] = []
        cursor: str | None = None
        while True:
            if cursor:
                params["cursor"] = cursor
            data = self._get(endpoint, params)
            batch = data.get(key, [])
            results.extend(batch)
            cursor = data.get("cursor")
            if not cursor or len(batch) < limit:
                break
            time.sleep(RATE_LIMIT_PAUSE)
        return results

    # ── public fetch methods ─────────────────────────────────────────────────

    def fetch_receipts(
        self,
        date_from: dt.datetime | None = None,
        date_to: dt.datetime | None = None,
    ) -> list[dict]:
        """Return raw receipt objects from Loyverse."""
        params: dict[str, Any] = {}
        if date_from:
            params["created_at_min"] = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
        if date_to:
            params["created_at_max"] = date_to.strftime("%Y-%m-%dT%H:%M:%SZ")
        return self._paginate("receipts", "receipts", params)

    def fetch_customers(self) -> list[dict]:
        return self._paginate("customers", "customers")

    def fetch_items(self) -> list[dict]:
        return self._paginate("items", "items")

    def fetch_employees(self) -> list[dict]:
        return self._paginate("employees", "employees")

    def test_connection(self) -> bool:
        """Return True if the token is valid."""
        try:
            self._get("merchants")
            return True
        except Exception:
            return False

    def get_merchant_info(self) -> dict:
        try:
            return self._get("merchants")
        except Exception:
            return {}

    # ── normalisation ────────────────────────────────────────────────────────

    def to_standard_df(
        self,
        date_from: dt.datetime | None = None,
        date_to: dt.datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch receipts and return a DataFrame in the app standard schema."""
        receipts = self.fetch_receipts(date_from, date_to)
        if not receipts:
            return pd.DataFrame()

        # Build lookup tables
        employees = {e["id"]: e.get("name", "Unknown") for e in self.fetch_employees()}
        items_map = {
            v["variant_id"]: {
                "name": i.get("item_name", "Unknown"),
                "cost": v.get("cost", 0) or 0,
            }
            for i in self.fetch_items()
            for v in i.get("variants", [])
        }

        rows: list[dict] = []
        for receipt in receipts:
            if receipt.get("cancelled_at"):
                continue
            order_id = receipt.get("receipt_number") or receipt.get("id", "")
            order_time = pd.to_datetime(receipt.get("created_at"), utc=True).tz_localize(None)
            branch = receipt.get("store", {}).get("name", "Main") if isinstance(receipt.get("store"), dict) else "Main"
            employee_id = receipt.get("employee_id", "")
            staff = employees.get(employee_id, "Unknown")
            customer_id = receipt.get("customer_id") or f"GUEST_{receipt.get('id', '')[:8]}"

            total_money = receipt.get("total_money", 0) or 0
            discount_money = receipt.get("discount_amount", 0) or 0
            point_payment = receipt.get("points_deducted", 0) or 0
            gross = total_money + discount_money + point_payment

            for line in receipt.get("line_items", []):
                variant_id = line.get("variant_id", "")
                item_info = items_map.get(variant_id, {"name": line.get("item_name", "Unknown"), "cost": 0})
                item_name = item_info["name"]
                qty = line.get("quantity", 1) or 1
                item_gross = line.get("gross_total_money", 0) or 0
                item_discount = line.get("discount_amount", 0) or 0
                item_net = item_gross - item_discount
                unit_cost = item_info["cost"]
                item_cost = unit_cost * qty if unit_cost else round(item_net * DEFAULT_MARGIN_RATIO, 2)
                item_margin = round(item_net - item_cost, 2)

                rows.append({
                    "order_id": f"{order_id}-{line.get('id', '')}",
                    "order_time": order_time,
                    "branch": branch,
                    "staff": staff,
                    "customer_id": customer_id,
                    "customer_segment": "active",  # will be overwritten by RFM engine
                    "item": item_name,
                    "qty": int(qty),
                    "gross": round(item_gross, 2),
                    "discount": round(item_discount, 2),
                    "net_sales": round(item_net, 2),
                    "cost": round(item_cost, 2),
                    "margin": item_margin,
                })

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["order_time"] = pd.to_datetime(df["order_time"])
        return df.sort_values("order_time").reset_index(drop=True)
