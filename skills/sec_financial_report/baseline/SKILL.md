---
name: sec-financial-report-baseline
description: Lightweight guidance for extracting quarterly financial metrics into a fixed JSON output.
---

# SEC Financial Report Baseline

Use this for small financial extraction tasks with local quarterly inputs.

## Workflow

1. Read both quarter files before writing anything.
2. Extract the stated revenue and net income values directly from the source.
3. Compute derived percentages carefully.
4. Write exactly one JSON file in the required schema.

## Guardrails

- Use the provided local files as the only source of truth.
- Keep numbers as JSON numbers, not strings.
- Do not add extra keys.
