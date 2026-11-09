# Semester Week 10 Progress Report

## Completed Work

- Forked the instructor repository `css4007-ai-agents-final` and cloned it.
- Read the project requirements and the A-level requirements.
- Compared several project ideas and chose the topic: an inventory management agent.
- Chose level A. The first version of the idea (four read-only tools) was closer to level C, so I added a write tool that needs approval, execution state, planning, limits and guardrails.
- Wrote `reports/proposal.md`: problem, users, functions, five agent tools, model, architecture, example requests, evaluation plan and weekly milestones.

Note: I wrote the proposal on 9 November 2026, which is the start of semester week 11, because I was finishing the HW5 homework during week 10. I have not backdated any commit.

## Important Commits

- Commit hash: (the commit that adds `reports/proposal.md` and this report)
- Description: Add project proposal and Week 10 report.
- Link: (link to that commit in my fork on GitHub)

## Current Functionality

There is no application code yet. The deliverable for this week is the plan: a documented architecture, the tool definitions in the proposal and an evaluation plan.

## Problems Encountered

- My first idea was too simple for level A, because all its tools only read data and there was nothing to approve or limit.
- I started the proposal late, because HW5 had the same period.
- I could not choose the research paper yet, because I need a recent paper and I have not verified one.

## Solutions

- I added a restock draft tool that needs user approval, and defined limits and guardrails. This makes the project multi-step and controlled.
- I made a realistic plan for Weeks 11–17 starting with code this week, so the late proposal does not delay development.
- I postponed the paper choice to Week 14, as the schedule allows, and noted topics to search for.

## What I Learned

- The difference between levels: level C needs the model to choose tools, and level A also needs state, planning, limits, approval and guardrails.
- A model only requests a tool, while my code validates and runs it, so permissions and limits belong in my code and not in the prompt.
- Tool results are data, not instructions, which is why prompt injection needs its own test.
- From HW4: a calculator-style tool is more accurate than mental arithmetic, so restock quantities should be calculated by code.

## Next Week

- Set up the project structure, `.env.example`, `.gitignore` and dependencies.
- Create the fictional data files (`products.json`, `sales.json`) including a few edge cases: an unknown SKU, a product with no sales and a product note containing an injected instruction.
- Make the first working request to `gpt-5.6-luna` and commit it.
- Start `get_products` and `check_stock` with tests, and write `reports/week-11.md`.