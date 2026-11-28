"""Tool schemas the model sees, and the single function that runs them safely."""
import json
from dataclasses import dataclass, replace
from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from inventory_agent import inventory as inv
from inventory_agent.drafts import MAX_ITEMS, create_restock_draft
from inventory_agent.permissions import POLICY


@dataclass(frozen=True)
class Env:
    """Run configuration. Set by the application, never by the model."""
    data_dir: Path | None = None
    out_dir: Path | None = None
    approved: bool = False


class _Args(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")    # no type coercion, no extra fields


class GetProductsArgs(_Args):
    category: str | None = None


class SkuArgs(_Args):
    sku: str


class SalesArgs(_Args):
    sku: str
    days: int = Field(ge=1, le=inv.MAX_DAYS)


class RestockArgs(_Args):
    sku: str
    target_days: int = Field(ge=1, le=inv.MAX_DAYS)


class DraftItem(_Args):
    sku: str
    quantity: int = Field(ge=1, le=inv.MAX_ORDER_QTY)


class DraftArgs(_Args):
    items: list[DraftItem] = Field(min_length=1, max_length=MAX_ITEMS)


SPECS = {
    "get_products": (GetProductsArgs,
        "List products (sku, name, category, unit_cost, supplier_lead_days). Optional category filter. "
        "Supplier notes are never returned.",
        lambda a, e: inv.get_products(a.category, e.data_dir)),
    "check_stock": (SkuArgs,
        "Current stock of one product: on_hand, reorder_point, below_reorder_point.",
        lambda a, e: inv.check_stock(a.sku, e.data_dir)),
    "analyze_sales": (SalesArgs,
        "Sales summary for one product over the last `days` days (1-90): units_sold, daily_average, trend. "
        "Returns an error if there is no sales history.",
        lambda a, e: inv.analyze_sales(a.sku, a.days, e.data_dir)),
    "suggest_restock": (RestockArgs,
        "Recommended order quantity for one product so that stock covers its lead time plus target_days. "
        "Also returns days_of_stock_left and the cost. All arithmetic is done by this tool.",
        lambda a, e: inv.suggest_restock(a.sku, a.target_days, e.data_dir)),
    "create_restock_draft": (DraftArgs,
        "Save a LOCAL restock draft for a list of {sku, quantity}. The application asks the user to approve "
        "first. Nothing is ordered. You cannot choose the file path.",
        lambda a, e: create_restock_draft([i.model_dump() for i in a.items], e.approved, e.data_dir, e.out_dir)),
}


def _noop(**kwargs):
    raise RuntimeError("tools are executed by execute_tool, not by LangChain")


def build_tools():
    return [StructuredTool.from_function(func=_noop, name=n, description=d, args_schema=m)
            for n, (m, d, _) in SPECS.items()]


def execute_tool(name, raw_args, approver, env):
    """Validate, check the permission policy, run. Always returns a dict, never raises."""
    spec = SPECS.get(name)
    if spec is None:
        return {"error": "unknown_tool", "message": f"No tool named {name}", "available": sorted(SPECS)}
    model_cls, _, runner = spec
    if not isinstance(raw_args, dict):
        return {"error": "invalid_arguments", "message": "arguments must be an object"}
    try:
        args = model_cls.model_validate(raw_args)
    except ValidationError as e:
        msg = "; ".join(f"{'.'.join(map(str, x['loc'])) or 'arguments'}: {x['msg']}" for x in e.errors())
        return {"error": "invalid_arguments", "message": msg[:300]}
    approved = False
    if POLICY[name].requires_approval:
        try:
            approved = approver(f"{name}: {json.dumps(raw_args)}") is True
        except Exception:
            approved = False
        if not approved:
            return {"error": "approval_denied",
                    "message": "The user did not approve this action; nothing was saved."}
    try:
        return runner(args, replace(env, approved=approved))
    except Exception as e:                                 # a bug in a tool must not crash the agent
        return {"error": "tool_failed", "message": f"{type(e).__name__}: {str(e)[:150]}"}