import json
import math

import pytest

from inventory_agent import inventory as inv
from inventory_agent.inventory import DATA_DIR


def sales_of(sku):
    rows = json.loads((DATA_DIR / "sales.json").read_text())["sales"][sku]
    return [r["units"] for r in sorted(rows, key=lambda r: r["date"])]


def test_get_products_hides_notes_but_flags_them():
    r = inv.get_products()
    assert r["count"] == 7 and all("notes" not in p for p in r["products"])
    assert {p["sku"]: p["has_notes"] for p in r["products"]}["SKU-3002"] is True


def test_category_filter_and_unknown_category():
    r = inv.get_products("electronics")
    assert r["count"] > 0 and all(p["category"] == "Electronics" for p in r["products"])
    e = inv.get_products("Toys")
    assert e["error"] == "unknown_category" and "Electronics" in e["available"]
    assert inv.get_products(5)["error"] == "invalid_category"


def test_check_stock_normalises_input_and_flags_low_stock():
    r = inv.check_stock("  sku-3001 ")
    assert r == {"sku": "SKU-3001", "on_hand": 0, "reorder_point": 8, "below_reorder_point": True}
    assert inv.check_stock("SKU-1002")["below_reorder_point"] is False


@pytest.mark.parametrize("bad", ["1001", "SKU-12", "", None, 1001, "SKU-1001; DROP"])
def test_invalid_sku_is_rejected(bad):
    assert inv.check_stock(bad)["error"] == "invalid_sku"


def test_unknown_sku():
    assert inv.check_stock("SKU-9999")["error"] == "unknown_sku"
    assert inv.analyze_sales("SKU-9999", 7)["error"] == "unknown_sku"


def test_analyze_sales_matches_independent_calculation():
    units = sales_of("SKU-1001")[-7:]
    r = inv.analyze_sales("SKU-1001", 7)
    assert r["units_sold"] == sum(units) and r["days_covered"] == 7
    assert r["daily_average"] == round(sum(units) / 7, 2)
    assert r["period_end"] == "2026-11-09"


@pytest.mark.parametrize("bad", [0, 91, -1, "7", 3.5, True, None])
def test_invalid_days_is_rejected(bad):
    assert inv.analyze_sales("SKU-1001", bad)["error"] == "invalid_days"


def test_no_sales_history_is_an_error_not_a_guess():
    assert inv.analyze_sales("SKU-3001", 30)["error"] == "no_sales_data"
    assert inv.suggest_restock("SKU-3001", 14)["error"] == "no_sales_data"


def test_trend_helper():
    assert inv._trend([1, 1, 5, 5]) == "increasing"
    assert inv._trend([5, 5, 1, 1]) == "decreasing"
    assert inv._trend([3, 3, 3, 3]) == "stable"
    assert inv._trend([1, 2]) == "insufficient_data"


@pytest.mark.parametrize("sku,lead,on_hand,cost", [("SKU-1001", 7, 12, 8.5), ("SKU-1002", 5, 140, 3.2)])
def test_suggest_restock_formula(sku, lead, on_hand, cost):
    avg = sum(sales_of(sku)[-30:]) / 30
    expected = max(0, math.ceil(avg * (14 + lead)) - on_hand)
    r = inv.suggest_restock(sku, 14)
    assert r["quantity"] == expected and r["cost"] == round(expected * cost, 2)


def test_suggest_restock_rejects_bad_target_days():
    assert inv.suggest_restock("SKU-1001", 0)["error"] == "invalid_target_days"
    assert inv.suggest_restock("SKU-1001", "14")["error"] == "invalid_target_days"


def test_order_quantity_is_capped(tmp_path):
    (tmp_path / "products.json").write_text(json.dumps({"products": [
        {"sku": "SKU-0001", "name": "x", "category": "c", "unit_cost": 1.0,
         "supplier_lead_days": 10, "on_hand": 0, "reorder_point": 5, "notes": ""}]}))
    rows = [{"date": f"2026-10-{d:02d}", "units": 500} for d in range(1, 31)]
    (tmp_path / "sales.json").write_text(json.dumps({"sales": {"SKU-0001": rows}}))
    r = inv.suggest_restock("SKU-0001", 14, data_dir=tmp_path)
    assert r["quantity"] == inv.MAX_ORDER_QTY and r["capped"] is True


def test_missing_data_files_give_data_error(tmp_path):
    assert inv.get_products(data_dir=tmp_path)["error"] == "data_error"
    assert inv.check_stock("SKU-1001", data_dir=tmp_path)["error"] == "data_error"