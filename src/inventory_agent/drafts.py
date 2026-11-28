"""The only write action: save a local restock draft. Needs approval, stays inside outputs/drafts."""
import json
import uuid
from pathlib import Path

from inventory_agent.inventory import MAX_ORDER_QTY, _err, _is_int, _norm_sku, _product
from inventory_agent.permissions import safe_join

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "outputs" / "drafts"
MAX_ITEMS = 20
MAX_DRAFT_COST = 2000.0


def create_restock_draft(items, approved=False, data_dir=None, out_dir=None):
    if approved is not True:
        return _err("approval_required", "A restock draft can only be saved after the user approves it")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
        return _err("invalid_items", f"items must be a list of 1 to {MAX_ITEMS} entries")
    lines, seen, total = [], set(), 0.0
    for it in items:
        if not isinstance(it, dict):
            return _err("invalid_items", "each item must be an object with sku and quantity")
        sku, qty = _norm_sku(it.get("sku")), it.get("quantity")
        if sku is None:
            return _err("invalid_sku", "SKU must look like SKU-1234")
        if not _is_int(qty) or not 1 <= qty <= MAX_ORDER_QTY:
            return _err("invalid_quantity", f"quantity must be an integer from 1 to {MAX_ORDER_QTY}")
        if sku in seen:
            return _err("duplicate_sku", f"{sku} appears more than once")
        product, err = _product(sku, data_dir)
        if err:
            return err
        seen.add(sku)
        cost = round(qty * product["unit_cost"], 2)
        total += cost
        lines.append({"sku": sku, "name": product["name"], "quantity": qty,
                      "unit_cost": product["unit_cost"], "cost": cost})
    total = round(total, 2)
    if total > MAX_DRAFT_COST:
        return _err("budget_exceeded", f"total cost {total} is above the limit {MAX_DRAFT_COST}")
    draft_id = "DRAFT-" + uuid.uuid4().hex[:8]
    base = Path(out_dir or OUT_DIR)
    base.mkdir(parents=True, exist_ok=True)
    try:
        path = safe_join(base, f"{draft_id}.json")       # the file name is made by code, never by the model
    except PermissionError:
        return _err("path_not_allowed", "The draft path is outside the allowed folder")
    path.write_text(json.dumps({"draft_id": draft_id, "status": "draft",
                                "note": "Local draft only. Nothing was ordered.",
                                "items": lines, "total_cost": total}, indent=2), encoding="utf-8")
    shown = path.relative_to(REPO_ROOT).as_posix() if REPO_ROOT in path.parents else path.name
    return {"draft_id": draft_id, "path": shown, "total_cost": total, "items": len(lines)}