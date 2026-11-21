"""Core inventory functions. Plain code, no model: all numbers are calculated here.

Every function validates its input and returns either a result dict or an
error dict {"error": code, "message": text}. Nothing raises for bad input.
"""
import json
import math
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SKU_RE = re.compile(r"^SKU-\d{4}$")
MAX_DAYS = 90
DEMAND_WINDOW_DAYS = 30
MAX_ORDER_QTY = 1000


def _err(code, message, **extra):
    return {"error": code, "message": message, **extra}


def _load(name, data_dir=None):
    try:
        return json.loads((Path(data_dir or DATA_DIR) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _norm_sku(sku):
    if not isinstance(sku, str):
        return None
    s = sku.strip().upper()
    return s if SKU_RE.match(s) else None


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _product(sku, data_dir=None):
    """Returns (product, None) or (None, error dict). sku must be normalised."""
    data = _load("products.json", data_dir)
    if data is None or "products" not in data:
        return None, _err("data_error", "Could not read products.json")
    for p in data["products"]:
        if p.get("sku") == sku:
            return p, None
    return None, _err("unknown_sku", f"No product with SKU {sku}")


def get_products(category=None, data_dir=None):
    if category is not None and not isinstance(category, str):
        return _err("invalid_category", "category must be a string or None")
    data = _load("products.json", data_dir)
    if data is None or "products" not in data:
        return _err("data_error", "Could not read products.json")
    products = data["products"]
    if category is not None:
        wanted = category.strip().lower()
        available = sorted({p["category"] for p in products})
        products = [p for p in products if p["category"].lower() == wanted]
        if not products:
            return _err("unknown_category", f"No category {category!r}", available=available)
    out = [{"sku": p["sku"], "name": p["name"], "category": p["category"],
            "unit_cost": p["unit_cost"], "supplier_lead_days": p["supplier_lead_days"],
            "has_notes": bool(p.get("notes"))} for p in products]
    return {"products": out, "count": len(out)}


def check_stock(sku, data_dir=None):
    s = _norm_sku(sku)
    if s is None:
        return _err("invalid_sku", "SKU must look like SKU-1234")
    p, err = _product(s, data_dir)
    if err:
        return err
    return {"sku": s, "on_hand": p["on_hand"], "reorder_point": p["reorder_point"],
            "below_reorder_point": p["on_hand"] < p["reorder_point"]}


def _trend(units):
    """Compare the average of the first half of the window with the second half."""
    if len(units) < 4:
        return "insufficient_data"
    half = len(units) // 2
    first, second = sum(units[:half]) / half, sum(units[-half:]) / half
    if first == 0:
        return "increasing" if second > 0 else "stable"
    change = (second - first) / first
    if change > 0.10:
        return "increasing"
    if change < -0.10:
        return "decreasing"
    return "stable"


def analyze_sales(sku, days, data_dir=None):
    s = _norm_sku(sku)
    if s is None:
        return _err("invalid_sku", "SKU must look like SKU-1234")
    if not _is_int(days) or not 1 <= days <= MAX_DAYS:
        return _err("invalid_days", f"days must be an integer from 1 to {MAX_DAYS}")
    _, err = _product(s, data_dir)
    if err:
        return err
    data = _load("sales.json", data_dir)
    if data is None or "sales" not in data:
        return _err("data_error", "Could not read sales.json")
    rows = data["sales"].get(s)
    if not rows:
        return _err("no_sales_data", f"No sales history for {s}; do not guess demand")
    try:
        rows = sorted(rows, key=lambda r: r["date"])
        window = rows[-days:]
        units = [int(r["units"]) for r in window]
    except (KeyError, TypeError, ValueError):
        return _err("data_error", "Malformed sales data")
    total = sum(units)
    return {"sku": s, "days_requested": days, "days_covered": len(units),
            "period_start": window[0]["date"], "period_end": window[-1]["date"],
            "units_sold": total, "daily_average": round(total / len(units), 2),
            "trend": _trend(units)}


def suggest_restock(sku, target_days, data_dir=None):
    """Quantity that covers supplier lead time plus target_days of demand.

    quantity = ceil(daily_average * (target_days + lead_days)) - on_hand, at least 0,
    at most MAX_ORDER_QTY. Daily demand comes from the last DEMAND_WINDOW_DAYS days.
    """
    if not _is_int(target_days) or not 1 <= target_days <= MAX_DAYS:
        return _err("invalid_target_days", f"target_days must be an integer from 1 to {MAX_DAYS}")
    stock = check_stock(sku, data_dir)
    if "error" in stock:
        return stock
    sales = analyze_sales(sku, DEMAND_WINDOW_DAYS, data_dir)
    if "error" in sales:
        return sales
    product, _ = _product(stock["sku"], data_dir)
    lead = product["supplier_lead_days"]
    avg = sales["units_sold"] / sales["days_covered"]
    on_hand = stock["on_hand"]
    days_left = round(on_hand / avg, 1) if avg > 0 else None
    needed = math.ceil(avg * (target_days + lead)) - on_hand
    quantity = max(0, needed)
    capped = quantity > MAX_ORDER_QTY
    quantity = min(quantity, MAX_ORDER_QTY)
    reason = (f"{avg:.2f} units/day over {sales['days_covered']} days; covering {lead} lead days "
              f"+ {target_days} target days needs {math.ceil(avg * (target_days + lead))} units, "
              f"{on_hand} on hand")
    return {"sku": stock["sku"], "quantity": quantity, "capped": capped,
            "days_of_stock_left": days_left, "lead_days": lead, "target_days": target_days,
            "daily_average": round(avg, 2), "cost": round(quantity * product["unit_cost"], 2),
            "reason": reason}