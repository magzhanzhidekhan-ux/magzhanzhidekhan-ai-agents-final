import json

import pytest

from inventory_agent.drafts import create_restock_draft

OK = [{"sku": "sku-1001", "quantity": 10}, {"sku": "SKU-1002", "quantity": 5}]


@pytest.mark.parametrize("flag", [False, None, "yes", 1])
def test_no_draft_without_real_approval(tmp_path, flag):
    r = create_restock_draft(OK, approved=flag, out_dir=tmp_path)
    assert r["error"] == "approval_required" and list(tmp_path.iterdir()) == []


def test_approved_draft_is_written_inside_the_folder(tmp_path):
    r = create_restock_draft(OK, approved=True, out_dir=tmp_path)
    saved = json.loads((tmp_path / f"{r['draft_id']}.json").read_text())
    assert r["total_cost"] == 101.0 == saved["total_cost"]          # 10*8.5 + 5*3.2
    assert saved["status"] == "draft" and [i["sku"] for i in saved["items"]] == ["SKU-1001", "SKU-1002"]


@pytest.mark.parametrize("items,code", [
    ([], "invalid_items"), ("x", "invalid_items"), ([5], "invalid_items"),
    ([{"sku": "SKU-1001", "quantity": 0}], "invalid_quantity"),
    ([{"sku": "SKU-1001", "quantity": 1001}], "invalid_quantity"),
    ([{"sku": "SKU-1001", "quantity": True}], "invalid_quantity"),
    ([{"sku": "bad", "quantity": 1}], "invalid_sku"),
    ([{"sku": "SKU-9999", "quantity": 1}], "unknown_sku"),
    ([{"sku": "SKU-1001", "quantity": 1}, {"sku": "sku-1001", "quantity": 2}], "duplicate_sku"),
])
def test_invalid_items_are_rejected_and_nothing_is_written(tmp_path, items, code):
    assert create_restock_draft(items, approved=True, out_dir=tmp_path)["error"] == code
    assert list(tmp_path.iterdir()) == []


def test_budget_limit(tmp_path):
    r = create_restock_draft([{"sku": "SKU-1003", "quantity": 100}], approved=True, out_dir=tmp_path)
    assert r["error"] == "budget_exceeded" and list(tmp_path.iterdir()) == []      # 100 * 32 = 3200