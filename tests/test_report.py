import json

import pytest

from inventory_agent.llm_client import LLMError
from inventory_agent.report import ReportError, build_facts, generate_report, parse_report, risk_rule

SKUS = ["SKU-1001", "SKU-1002"]
GOOD = json.dumps({"items": [{"sku": "SKU-1001", "risk": "high", "reason": "Low stock, selling fast."},
                             {"sku": "SKU-1002", "risk": "low", "reason": "Plenty of stock left."}]})


class FakeModel:
    """FAKE model for tests only: returns scripted replies, no API key needed."""
    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    def invoke(self, messages):
        self.calls += 1
        return type("R", (), {"content": self.replies.pop(0)})()


def test_valid_report_and_code_fence():
    assert [i.risk for i in parse_report(GOOD, SKUS).items] == ["high", "low"]
    assert len(parse_report("```json\n" + GOOD + "\n```", SKUS).items) == 2


@pytest.mark.parametrize("bad", [
    "not json at all",
    json.dumps({"items": [{"sku": "SKU-1001", "risk": "urgent", "reason": "Invalid risk value."}]}),
    json.dumps({"items": [{"sku": "SKU-1001", "risk": "high", "reason": "ok"}]}),
    json.dumps({"items": [{"sku": "SKU-1001", "risk": "high", "reason": "Low stock here."}]}),
    json.dumps({"items": [{"sku": "SKU-1001", "risk": "high", "reason": "Low stock here."},
                          {"sku": "SKU-1002", "risk": "low", "reason": "Plenty of stock."},
                          {"sku": "SKU-7777", "risk": "low", "reason": "Invented product."}]}),
])
def test_invalid_reports_are_rejected(bad):
    with pytest.raises(ReportError):
        parse_report(bad, SKUS)


def test_retry_after_invalid_answer_succeeds():
    model = FakeModel(["oops", GOOD])
    facts = [{"sku": s} for s in SKUS]
    assert len(generate_report(model, facts).items) == 2 and model.calls == 2


def test_gives_up_after_two_invalid_answers():
    model = FakeModel(["oops", "still not json"])
    with pytest.raises(ReportError, match="2 attempts"):
        generate_report(model, [{"sku": s} for s in SKUS])
    assert model.calls == 2


def test_model_failure_is_a_clear_error():
    class Broken:
        def invoke(self, messages):
            raise TimeoutError("boom")
    with pytest.raises(LLMError):
        generate_report(Broken(), [{"sku": "SKU-1001"}])


def test_build_facts_and_rule_in_code():
    facts = {f["sku"]: f for f in build_facts()}
    assert len(facts) == 7
    assert facts["SKU-3001"]["days_of_stock_left"] is None and risk_rule(facts["SKU-3001"]) == "high"
    assert risk_rule({"on_hand": 10, "days_of_stock_left": 3.0}) == "high"
    assert risk_rule({"on_hand": 10, "days_of_stock_left": 10.0}) == "medium"
    assert risk_rule({"on_hand": 10, "days_of_stock_left": 30.0}) == "low"
    assert risk_rule({"on_hand": 10, "days_of_stock_left": None}) == "medium"