---
name: sec-financial-report-improved
description: Deterministic workflow for extracting quarterly financial metrics and computing derived percentages from local SEC-style inputs.
---

# SEC Financial Report Improved

Use this procedure for small financial reporting tasks with fixed quarter folders.

## Workflow

1. Read both quarter files completely before calculating anything.
2. Normalize all extracted money values to millions of USD.
3. Extract these fields directly from the source:
   - company
   - currency
   - q2 revenue
   - q3 revenue
   - q2 net income
   - q3 net income
   - q3 operating income
4. Compute:
   - `revenue_growth_pct = ((q3_revenue - q2_revenue) / q2_revenue) * 100`
   - `net_income_growth_pct = ((q3_net_income - q2_net_income) / q2_net_income) * 100`
   - `q3_operating_margin_pct = (q3_operating_income / q3_revenue) * 100`
5. Round derived percentages to two decimal places.
6. Set `higher_revenue_quarter` to the quarter with the larger revenue value.
7. Write exactly one JSON file with only the required keys.

## Guardrails

- Use only the local quarter files.
- Do not browse, search, or fetch external data.
- Do not infer different units; the source values are already in millions.
- Keep extracted values numeric in the final JSON.
- Make the summary short and deterministic.

## Suggested implementation pattern

If needed, use a small Python one-liner or script to avoid arithmetic mistakes, then delete any temporary helper file before finishing.
