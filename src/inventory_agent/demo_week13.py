import argparse
import json
from pathlib import Path

from inventory_agent.agent import run_agent
from inventory_agent.llm_client import LLMError, build_model


def make_approver(mode):
    if mode == "yes":                       # only for the recorded demo; the default asks a human
        return lambda summary: True
    if mode == "no":
        return lambda summary: False
    return lambda summary: input(f"\nAPPROVAL NEEDED: {summary}\nApprove? [y/N] ").strip().lower() == "y"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("request")
    p.add_argument("--approve", choices=["ask", "yes", "no"], default="ask")
    p.add_argument("--name", required=True, help="trace file name suffix")
    a = p.parse_args()
    try:
        model = build_model()
    except LLMError as e:
        raise SystemExit(f"ERROR: {e}")
    result = run_agent(model, a.request, make_approver(a.approve))
    print("REQUEST:", a.request)
    for t in result["trace"]:
        r = t["result"]
        status = f"ERROR {r['error']}" if "error" in r else "ok"
        print(f"  step {t['step']}: {t['tool']}({json.dumps(t['args'])}) -> {status}")
    print("\nANSWER:", result["answer"])
    print(f"stop_reason={result['stop_reason']} steps={result['steps']} tool_calls={result['tool_calls']} "
          f"drafts={result['drafts']}")
    Path("outputs").mkdir(exist_ok=True)
    Path(f"outputs/week-13-{a.name}.json").write_text(
        json.dumps({"request": a.request, "approve_mode": a.approve, **result}, indent=2, ensure_ascii=False),
        encoding="utf-8")


if __name__ == "__main__":
    main()