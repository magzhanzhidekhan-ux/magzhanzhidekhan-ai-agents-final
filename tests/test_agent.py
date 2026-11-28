import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from fakes import ScriptedModel, call, say
from inventory_agent.agent import run_agent
from inventory_agent.tools import Env


def last_tool(messages):
    tm = [m for m in messages if isinstance(m, ToolMessage)]
    return json.loads(tm[-1].content) if tm else None


def no_approval(summary):
    raise AssertionError("approver must not be called for read tools")


@pytest.mark.parametrize("sku,expected", [("SKU-1001", ["check_stock", "suggest_restock"]),
                                          ("SKU-1002", ["check_stock"])])
def test_tool_result_changes_the_next_action(sku, expected):
    def script(messages):
        r = last_tool(messages)
        if r is None:
            return call("check_stock", {"sku": sku})
        if r.get("below_reorder_point") and "quantity" not in r:
            return call("suggest_restock", {"sku": sku, "target_days": 14})
        return say("done")
    res = run_agent(ScriptedModel(script), "q", no_approval)
    assert [t["tool"] for t in res["trace"]] == expected and res["stop_reason"] == "completed"


def test_invalid_arguments_go_back_to_the_model_which_can_retry():
    def script(messages):
        r = last_tool(messages)
        if r is None:
            return call("analyze_sales", {"sku": "SKU-1001", "days": "7"})
        if "error" in r:
            return call("analyze_sales", {"sku": "SKU-1001", "days": 7})
        return say("done")
    res = run_agent(ScriptedModel(script), "q", no_approval)
    assert "error" in res["trace"][0]["result"] and res["trace"][1]["result"]["days_covered"] == 7


def test_unknown_tool_from_the_model_is_handled():
    def script(messages):
        return call("delete_everything", {}) if last_tool(messages) is None else say("ok")
    res = run_agent(ScriptedModel(script), "q", no_approval)
    assert res["trace"][0]["result"]["error"] == "unknown_tool" and res["stop_reason"] == "completed"


def test_every_tool_call_id_is_answered():
    def script(messages):
        if last_tool(messages) is None:
            return AIMessage(content="", tool_calls=[
                {"name": "check_stock", "args": {"sku": "SKU-1001"}, "id": "a1", "type": "tool_call"},
                {"name": "check_stock", "args": {"sku": "SKU-1002"}, "id": "a2", "type": "tool_call"}])
        return say("ok")
    model = ScriptedModel(script)
    run_agent(model, "q", no_approval)
    assert [m.tool_call_id for m in model.seen[-1] if isinstance(m, ToolMessage)] == ["a1", "a2"]


def draft_script(messages):
    if last_tool(messages) is None:
        return call("create_restock_draft", {"items": [{"sku": "SKU-1001", "quantity": 42}]})
    return say("done")


def test_denied_approval_saves_nothing(tmp_path):
    res = run_agent(ScriptedModel(draft_script), "plan", lambda s: False, env=Env(out_dir=tmp_path))
    assert res["trace"][0]["result"]["error"] == "approval_denied"
    assert list(tmp_path.iterdir()) == [] and res["drafts"] == []


def test_approved_draft_is_saved_and_approver_sees_the_action(tmp_path):
    seen = []
    res = run_agent(ScriptedModel(draft_script), "plan", lambda s: seen.append(s) or True,
                    env=Env(out_dir=tmp_path))
    assert "SKU-1001" in seen[0] and len(list(tmp_path.glob("DRAFT-*.json"))) == 1
    assert len(res["drafts"]) == 1 and res["stop_reason"] == "completed"


def test_step_limit_stops_a_looping_model():
    model = ScriptedModel(lambda m: call("check_stock", {"sku": "SKU-1001"}))
    res = run_agent(model, "loop", no_approval, max_steps=3)
    assert res["stop_reason"] == "step_limit" and len(res["trace"]) == 3 and res["answer"] is None


def test_tool_call_limit_stops_the_run_and_answers_every_call():
    five = AIMessage(content="", tool_calls=[
        {"name": "check_stock", "args": {"sku": "SKU-1001"}, "id": f"t{i}", "type": "tool_call"}
        for i in range(5)])
    res = run_agent(ScriptedModel(lambda m: five), "q", no_approval, max_tool_calls=2)
    errors = [t for t in res["trace"] if t["result"].get("error") == "tool_call_limit"]
    assert res["stop_reason"] == "tool_call_limit" and len(res["trace"]) == 5 and len(errors) == 3


def test_model_failure_is_reported_not_raised():
    class Broken:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            raise TimeoutError("boom")
    res = run_agent(Broken(), "q", no_approval)
    assert res["stop_reason"] == "model_error" and "TimeoutError" in res["error"]