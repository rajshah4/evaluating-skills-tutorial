---
name: sales-pivot-analysis-baseline
description: Lightweight guidance for combining spreadsheet and PDF inputs into a deterministic result workbook.
---

# Sales Pivot Analysis Baseline

Use this for small spreadsheet-style analysis tasks with one workbook input and one PDF input.

## Workflow

1. Read both input sources before writing the result workbook.
2. Build a simple combined table first.
3. Then build a summary sheet from the combined table.
4. Prefer a deterministic worksheet layout over complex Excel-specific features.

## Guardrails

- Use only the provided local files.
- It is acceptable to create normal sheets and tables instead of a real pivot object.
- Keep the final workbook small and deterministic.
