"""Tool permission policy and safe path handling."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Policy:
    access: str               # "read" or "write"
    requires_approval: bool   # a human must approve before the tool runs
    scope: str                # where the tool may act


POLICY = {
    "get_products": Policy("read", False, "data/products.json"),
    "check_stock": Policy("read", False, "data/products.json"),
    "analyze_sales": Policy("read", False, "data/sales.json"),
    "suggest_restock": Policy("read", False, "data/products.json and data/sales.json"),
    "create_restock_draft": Policy("write", True, "outputs/drafts/ only"),
}


def safe_join(base, name):
    """Join name to base and refuse anything that ends up outside base."""
    base = Path(base).resolve()
    target = (base / name).resolve()
    if target != base and base not in target.parents:
        raise PermissionError(f"path escapes {base}")
    return target