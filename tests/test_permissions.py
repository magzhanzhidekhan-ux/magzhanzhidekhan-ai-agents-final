import pytest

from inventory_agent.permissions import POLICY, safe_join
from inventory_agent.tools import SPECS


def test_every_tool_has_a_policy():
    assert set(POLICY) == set(SPECS)          # a tool without a policy would be unguarded


def test_only_the_draft_tool_writes_and_needs_approval():
    writers = {n for n, p in POLICY.items() if p.access == "write"}
    approvals = {n for n, p in POLICY.items() if p.requires_approval}
    assert writers == approvals == {"create_restock_draft"}


def test_safe_join_inside(tmp_path):
    assert safe_join(tmp_path, "a.json").parent == tmp_path.resolve()


@pytest.mark.parametrize("bad", ["../x.json", "sub/../../x.json", "/etc/passwd", "C:\\Windows\\x.json"])
def test_safe_join_rejects_escape(tmp_path, bad):
    with pytest.raises(PermissionError):
        safe_join(tmp_path, bad)