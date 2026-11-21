"""Structured output: the model returns a JSON risk report, which is validated."""
import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from inventory_agent.inventory import DEMAND_WINDOW_DAYS, analyze_sales, check_stock, get_products
from inventory_agent.llm_client import ask


class ReportError(Exception):
    """The model output could not be turned into a valid report."""


class RiskItem(BaseModel):
    sku: str
    risk: Literal["high", "medium", "low"]
    reason: str = Field(min_length=5, max_length=300)


class StockRiskReport(BaseModel):
    items: list[RiskItem]


SYSTEM = """You assess stock risk for a small shop. Use ONLY the facts given; never invent numbers or SKUs.
Return JSON only, no other text, exactly in this shape:
{"items": [{"sku": "SKU-1234", "risk": "high|medium|low", "reason": "one short sentence"}]}
Give exactly one item per SKU in the input.
Risk rule: high if on_hand is 0 or days_of_stock_left < 7; medium if days_of_stock_left < 14,
or if there is no sales history while stock is above 0; otherwise low."""


def risk_rule(fact):
    """The same rule in code, used to check the model's answer."""
    if fact["on_hand"] == 0:
        return "high"
    left = fact["days_of_stock_left"]
    if left is None:
        return "medium"
    return "high" if left < 7 else "medium" if left < 14 else "low"


def build_facts(data_dir=None):
    facts = []
    for p in get_products(data_dir=data_dir)["products"]:
        stock = check_stock(p["sku"], data_dir)
        sales = analyze_sales(p["sku"], DEMAND_WINDOW_DAYS, data_dir)
        avg = days_left = None
        if "error" not in sales:
            avg = sales["units_sold"] / sales["days_covered"]
            days_left = round(stock["on_hand"] / avg, 1) if avg > 0 else None
        facts.append({"sku": p["sku"], "name": p["name"], "on_hand": stock["on_hand"],
                      "reorder_point": stock["reorder_point"],
                      "daily_average_30d": None if avg is None else round(avg, 2),
                      "days_of_stock_left": days_left,
                      "sales_history": "none" if avg is None else "available"})
    return facts


def parse_report(text, expected_skus):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned).strip()
    try:
        data = json.loads(cleaned)
    except ValueError as e:
        raise ReportError("the answer is not valid JSON") from e
    try:
        report = StockRiskReport.model_validate(data)
    except ValidationError as e:
        raise ReportError(f"the JSON does not match the schema: {str(e)[:200]}") from e
    got = [i.sku.strip().upper() for i in report.items]
    expected = set(expected_skus)
    if len(got) != len(set(got)):
        raise ReportError("a SKU appears more than once")
    if set(got) - expected:
        raise ReportError(f"unknown SKU in the answer: {sorted(set(got) - expected)}")
    if expected - set(got):
        raise ReportError(f"missing SKU in the answer: {sorted(expected - set(got))}")
    return report


def generate_report(model, facts, max_attempts=2):
    """Ask for the report; if it is invalid, tell the model what was wrong and retry once."""
    prompt = "Facts (calculated by code):\n" + json.dumps(facts, indent=1)
    skus = [f["sku"] for f in facts]
    last = None
    for _ in range(max_attempts):
        text = ask(model, SYSTEM, prompt if last is None else
                   f"{prompt}\n\nYour previous answer was invalid: {last}. Return only the corrected JSON.")
        try:
            return parse_report(text, skus)
        except ReportError as e:
            last = str(e)
    raise ReportError(f"no valid report after {max_attempts} attempts: {last}")