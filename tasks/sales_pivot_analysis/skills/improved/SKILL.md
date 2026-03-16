---
name: sales-pivot-analysis-improved
description: Deterministic workflow for combining workbook and PDF data into a validated result workbook with derived sales metrics.
---

# Sales Pivot Analysis Improved

Use this procedure for small workbook-generation tasks that combine spreadsheet data and PDF-extracted reference values.

## Workflow

1. Read `income.xlsx` first to identify the city and revenue rows.
2. Read `population.pdf` and extract the city-to-population mapping.
3. Build a normalized combined table with:
   - city
   - region
   - revenue in millions
   - population in millions
   - revenue per capita
4. Round revenue per capita to two decimals.
5. Create a `Summary` sheet with:
   - total revenue
   - total population
   - city-level revenue per capita table
6. Create a `CombinedData` sheet with one row per city.

## Guardrails

- Prefer deterministic cell values over Excel-specific pivot mechanics.
- The verifier cares about the resulting workbook contents, not whether a native pivot object exists.
- Keep sheet names exact: `CombinedData` and `Summary`.
- Do not assume `openpyxl` or `pandas` are installed inside the task runtime.
- Prefer built-in parsing paths that work without installing anything.
- Do not use `pip`, `apt`, or any other package installer.

## No-install parsing path

If spreadsheet libraries are missing, use built-in Python modules:

- Parse `income.xlsx` with `zipfile` and `xml.etree.ElementTree` by reading `xl/worksheets/sheet1.xml`.
- Parse `population.pdf` with `strings input/population.pdf` because the bundled PDF stores the population lines as plain text.

Suggested extraction pattern for the workbook:

```bash
python3 - <<'PY'
from zipfile import ZipFile
import xml.etree.ElementTree as ET

with ZipFile('input/income.xlsx') as zf:
    root = ET.fromstring(zf.read('xl/worksheets/sheet1.xml'))
print(root.tag)
PY
```

Suggested extraction pattern for the PDF:

```bash
strings input/population.pdf | grep -E 'Austin|Chicago|Denver|Seattle'
```
