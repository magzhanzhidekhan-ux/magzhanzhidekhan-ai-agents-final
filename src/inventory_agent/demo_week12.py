from inventory_agent.inventory import suggest_restock
from inventory_agent.llm_client import LLMError, build_model
from inventory_agent.report import ReportError, build_facts, generate_report, risk_rule


def main():
    facts = build_facts()
    print("FACTS (calculated by code)")
    for f in facts:
        print(f"  {f['sku']} {f['name']:<20} on_hand={f['on_hand']:<4} "
              f"avg30={f['daily_average_30d']} days_left={f['days_of_stock_left']}")
    try:
        report = generate_report(build_model(), facts)
    except (LLMError, ReportError) as e:
        raise SystemExit(f"ERROR: {e}")
    by_sku = {f["sku"]: f for f in facts}
    print("\nMODEL RISK REPORT (validated JSON) vs RULE IN CODE")
    agree = 0
    for item in report.items:
        expected = risk_rule(by_sku[item.sku])
        agree += item.risk == expected
        print(f"  {item.sku} model={item.risk:<6} code={expected:<6} {item.reason}")
    print(f"agreement: {agree}/{len(report.items)}")
    print("\nRESTOCK SUGGESTIONS (code, target 14 days) for high/medium risk")
    for item in report.items:
        if item.risk in ("high", "medium"):
            r = suggest_restock(item.sku, 14)
            print(f"  {item.sku}:", r if "error" in r else
                  f"order {r['quantity']} units, cost {r['cost']}, {r['reason']}")


if __name__ == "__main__":
    main()