# Semester Week 11 Progress Report

## Completed Work

- Set up the project: virtual environment, `requirements.txt` with pinned versions, `.env.example`, `.gitignore` (Python 3.12.1).
- Created fictional data: `data/products.json` (7 products) and a generator `scripts/make_sample_data.py` that writes 90 days of sales with a fixed seed. The data includes edge cases for later weeks: a product with zero stock and no sales (SKU-3001), a product below its reorder point, and a product note with an injected instruction (SKU-3002) for the prompt-injection guardrail test.
- Wrote `llm_client.py`: builds the `gpt-5.6-luna` client from environment variables and wraps every failure (missing key, network or API error, empty answer) in one `LLMError` with a readable message.
- Made the first real request (`first_request.py`): the model gets the product table and names the products below their reorder point. The answer is parsed and compared with a plain-code calculation of the same thing.
- Wrote 5 tests with a clearly labelled fake model (no API key needed) and a short setup section in `README.md`.

## Important Commits

- Commit hash: [ВСТАВЬТЕ] — Description: project setup and fictional data with edge cases.
- Commit hash: [ВСТАВЬТЕ] — Description: LLM client with error handling, first request, 5 tests.
- Link: https://github.com/[ВСТАВЬТЕ-ник]/css4007-ai-agents-final/commits/main

## Current Functionality

The application can make a real request to `gpt-5.6-luna` and get a text answer. First request result (`outputs/week-11-first-request.txt`): model said [ВСТАВЬТЕ], code says [ВСТАВЬТЕ], match: [ВСТАВЬТЕ]. Missing keys, empty input and API failures give a clear error instead of a crash. `python -m pytest -q` gives [ВСТАВЬТЕ: 5 passed]. There are no tools or agent loop yet; these are planned for Weeks 12–14.

## Problems Encountered

- [ВСТАВЬТЕ real problems, for example: PowerShell wrote `requirements.txt` in the wrong encoding / `PYTHONPATH` / import errors from `src/`.]
- Earlier homework showed that this model rejects function tools when reasoning is on, so I need to design the client for tools from the start.
- The product notes contain an injected instruction. I have to decide how the model sees notes, because they are data and not commands.

## Solutions

- Set `reasoning_effort="none"` in the client now, so the same client will work when tools are added in Week 13.
- Left the notes out of the first prompt and planned a dedicated guardrail test in Week 15.
- Compared the model answer with an independent code calculation, so I measure the result instead of trusting it.

## What I Learned

- Putting all model access in one module makes error handling and testing simple: tests replace the model with a fake and need no key.
- A model answer needs validation: I parse the SKU list and compare it with a deterministic calculation. Later, quantities will be computed by code, as in HW4, because models are weak at exact arithmetic.
- Timeouts and retries must be set explicitly, otherwise a failed API call can hang or crash the program.

## Next Week

- Write `get_products`, `check_stock` and `analyze_sales` as plain functions with input validation (SKU format, `days` from 1 to 90) and error dictionaries.
- Use structured outputs where the model returns data, and validate them.
- Add tests: unknown SKU, no sales data, bad arguments (target 12 tests by Week 15).
- Write `reports/week-12.md`.