import json
import pytest

from inventory_agent import first_request as fr
from inventory_agent.llm_client import LLMError, ask, build_model


class FakeModel:
    """FAKE model for tests only: no API key needed."""
    def __init__(self, text=None, error=None):
        self.text, self.error = text, error

    def invoke(self, messages):
        if self.error:
            raise self.error
        return type("R", (), {"content": self.text})()


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMError, match="OPENAI_API_KEY"):
        build_model()


def test_ask_returns_text():
    assert ask(FakeModel("SKU-1001"), "sys", "question") == "SKU-1001"


def test_api_failure_is_wrapped():
    with pytest.raises(LLMError, match="Model call failed"):
        ask(FakeModel(error=TimeoutError("boom")), "sys", "question")


def test_empty_input_and_empty_answer_are_rejected():
    with pytest.raises(LLMError):
        ask(FakeModel("x"), "sys", "   ")
    with pytest.raises(LLMError, match="empty"):
        ask(FakeModel("  "), "sys", "question")


def test_low_stock_truth_and_parser():
    products = fr.load_products()
    assert fr.low_stock_truth(products) == ["SKU-1001", "SKU-1003", "SKU-2002", "SKU-3001"]
    assert fr.parse_skus("sku-1001,\nSKU-1003 , sku-1001") == ["SKU-1001", "SKU-1003"]
    assert fr.parse_skus("none") == []