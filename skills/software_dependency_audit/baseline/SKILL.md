---
name: dependency-audit-baseline
description: Minimal procedural guidance for auditing a dependency lockfile and writing the tutorial report format.
---

# Dependency Audit Baseline

Use this process when asked to audit a dependency lockfile.

1. Inspect the task input and confirm the expected output path.
2. Prefer a reproducible CLI workflow over guessing from package names.
3. If you use a scanner, save raw output first, then transform it into the requested schema.
4. Only include HIGH and CRITICAL findings.
5. Write a JSON object with a top-level `findings` array.

Required fields for each finding:
- `package`
- `version`
- `cve_id`
- `severity`
- `cvss_score`
- `fixed_version`
- `title`
- `url`
