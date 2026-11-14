import json
from pathlib import Path

from inventory_agent.llm_client import LLMError, ask, build_model

DATA = Path(__file__).resolve().parents[2] / "data"
SYSTEM = ("You are an inventory assistant. Use only the data given. "
          "Answer with SKU codes separated by commas, nothing else. If none, answer NONE.")


def load_products():
    return json.loads((DATA / "products.json").read_text(encoding="utf-8"))["products"]


def low_stock_truth(products):
    """What the code computes: SKUs with on_hand below reorder_point."""
    return sorted(p["sku"] for p in products if p["on_hand"] < p["reorder_point"])


def parse_skus(text):
    if text.strip().upper() == "NONE":
        return []
    return sorted({s.strip().upper() for s in text.replace("\n", ",").split(",") if s.strip()})


def main():
    products = load_products()
    table = "\n".join(f"{p['sku']}: {p['name']}, on_hand={p['on_hand']}, reorder_point={p['reorder_point']}"
                      for p in products)          # notes are left out on purpose for now
    try:
        answer = ask(build_model(), SYSTEM,
                     f"Products:\n{table}\n\nWhich products are below their reorder point?")
    except LLMError as e:
        raise SystemExit(f"ERROR: {e}")
    model_skus, truth = parse_skus(answer), low_stock_truth(products)
    print("model said:", model_skus)
    print("code says: ", truth)
    print("match:     ", model_skus == truth)


if __name__ == "__main__":
    main()