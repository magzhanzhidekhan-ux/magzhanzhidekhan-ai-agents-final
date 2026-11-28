import pytest

from inventory_agent.tools import Env, build_tools, execute_tool


def never(summary):
    raise AssertionError("approver must not be called for read tools")


def test_unknown_tool():
    assert execute_tool("delete_everything", {}, never, Env())["error"] == "unknown_tool"


@pytest.mark.parametrize("name,args", [
    ("analyze_sales", {"sku": "SKU-1001", "days": "7"}),               # string instead of int
    ("analyze_sales", {"sku": "SKU-1001", "days": True}),              # bool is not an int here
    ("analyze_sales", {"sku": "SKU-1001", "days": 365}),               # out of range
    ("check_stock", {}),                                               # missing field
    ("check_stock", {"sku": "SKU-1001", "out_path": "/etc/x"}),        # extra field is refused
    ("create_restock_draft", {"items": [{"sku": "SKU-1001", "quantity": 5}], "approved": True}),
])
def test_invalid_arguments_are_refused(name, args):
    assert execute_tool(name, args, never, Env())["error"] == "invalid_arguments"


def test_read_tool_runs_without_approval():
    assert execute_tool("check_stock", {"sku": "SKU-3001"}, never, Env())["on_hand"] == 0


def test_write_tool_needs_approval(tmp_path):
    args = {"items": [{"sku": "SKU-1001", "quantity": 42}]}
    env = Env(out_dir=tmp_path)
    assert execute_tool("create_restock_draft", args, lambda s: False, env)["error"] == "approval_denied"
    def boom(s):
        raise RuntimeError("no terminal")
    assert execute_tool("create_restock_draft", args, boom, env)["error"] == "approval_denied"
    assert list(tmp_path.iterdir()) == []
    ok = execute_tool("create_restock_draft", args, lambda s: True, env)
    assert ok["total_cost"] == 357.0 and len(list(tmp_path.iterdir())) == 1


def test_model_cannot_pass_path_or_approval_flag():
    props = {t.name: set(t.args) for t in build_tools()}
    assert props["create_restock_draft"] == {"items"}
    assert len(props) == 5