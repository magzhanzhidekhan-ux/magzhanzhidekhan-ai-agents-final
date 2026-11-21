# Semester Week 12 Progress Report

## Completed Work

- Implemented the four core functions in `inventory.py`: `get_products`, `check_stock`, `analyze_sales`, `suggest_restock`. They are plain code and the model does no arithmetic.
- Added input validation: SKU format (`SKU-1234`, case and spaces normalised), `days` and `target_days` must be integers from 1 to 90 (booleans, strings and floats are rejected), category must be a string. Every failure returns an error dictionary with a code (`invalid_sku`, `unknown_sku`, `invalid_days`, `no_sales_data`, `data_error`, ...) and does not raise.
- Restock formula: `quantity = ceil(daily_average * (target_days + lead_days)) - on_hand`, at least 0 and capped at 1000 units. Daily demand comes from the last 30 days.
- Added structured output in `report.py`: the model gets the facts calculated by code and returns a JSON risk report (`high`, `medium`, `low` with a short reason). The output is validated with a pydantic schema and then checked so that every SKU appears exactly once and no SKU is invented. On an invalid answer the model is told what was wrong and gets one retry.
- Wrote [N] new tests (total [N]) and a demo, `demo_week12.py`, that shows the facts, the model's report, its agreement with the rule in code, and restock suggestions.

## Important Commits

- Commit hash: [HASH] — core functions with validation and tests.
- Commit hash: [HASH] — structured JSON report with schema validation and retry.
- Commit hash: [HASH] — demo run and README.
- Link: https://github.com/magzhanzhidekhan-ux/magzhanzhidekhan-ai-agents-final/commits/main

## Current Functionality

Real run (`outputs/week-12-demo.txt`): the application lists the 7 products with stock and 30-day demand, asks `gpt-5.6-luna` for a validated risk report, and compares it with the rule in code. The model agreed with the rule on 7 of 7 products (SKU-1001, SKU-1003, SKU-2002 and SKU-3001 high; SKU-1002, SKU-2001 and SKU-3002 low). For the high-risk products the code calculated restock quantities: SKU-1001 order 42 units (cost 357.0), SKU-1003 order 23 units (736.0), SKU-2002 order 104 units (41.6). I checked these three by hand with the formula. SKU-3001 (no stock, no sales history) returns `no_sales_data` instead of an invented quantity. `python -m pytest -q`: [N passed]. The functions are not yet exposed to the model as tools and there is no agent loop; that is Weeks 13-14.

Differences from the proposal: `get_products` returns `{"products": [...], "count": n}` so that it can also return an error, and the supplier `notes` field is not returned, only a `has_notes` flag, because notes are free text that can contain injected instructions.

## Problems Encountered

- Deciding what to do when there is no sales history: a guess would be an invented number.
- Free-text supplier notes are an injection risk, so I had to decide whether the model should see them at all.
- PyCharm showed "Unresolved reference" errors for `inventory_agent` because `src` was not marked as a sources root. The code and tests ran correctly from the terminal.
- The agreement of 7/7 is a weak check: the risk rule is written in the model's prompt, so the model only has to apply a rule it was given. It does not show that the model can judge risk on its own.

## Solutions

- Return a `no_sales_data` error and a `None` days-of-stock value, and let the risk rule treat "no history but stock above 0" as medium.
- Validate the model's JSON with a schema plus a set check on SKUs, with one retry that includes the error. After two failures a `ReportError` is raised and nothing is guessed.
- Keep notes out of all results and test it (`test_get_products_hides_notes_but_flags_them`).
- Tests use independent calculations from the raw JSON (not the function under test) and temporary data folders for the cap and missing-file cases.
- Marked `src` as a sources root in PyCharm; `pytest.ini` already sets `pythonpath = src` for the tests.

## What I Learned

- Model output must be treated like user input: parse it, validate the schema, and check it against the facts (no invented SKUs, one item per SKU).
- A deterministic rule in code is a good check on a model's answer, but when the rule is also in the prompt, agreement mostly shows that the model follows instructions, not that it reasons well.
- Error dictionaries with codes make tools easier for a model to use later, because it can read why a call failed.
- Booleans are integers in Python, so `True` would pass an `int` check unless it is rejected explicitly.

## Next Week

- Expose the functions to the model as tools (`get_products`, `check_stock`, `analyze_sales`, `suggest_restock`) with argument schemas, and add a write tool `create_restock_draft` with a permission policy (approval needed, only inside `outputs/`).
- Let the model choose the tools and answer from tool results; log every tool call.
- Add tests for tool selection with a fake model and for argument validation; write `reports/week-13.md`.