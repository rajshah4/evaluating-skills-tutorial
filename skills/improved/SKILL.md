---
name: dependency-audit-improved
description: Offline Trivy and CVSS extraction workflow for deterministic dependency auditing in OpenHands.
---

# Dependency Audit Improved

Use this procedure for dependency-audit tasks in restricted environments.

## Workflow

1. Verify the lockfile exists before scanning.
2. Check for a pinned offline scan snapshot at `input/trivy_report.json`.
3. If that snapshot exists, use it instead of refreshing a live vulnerability database.
4. Otherwise prefer Trivy in offline mode.
5. Use filesystem scanning against the lockfile and save raw JSON before transforming results.

Preferred deterministic path:

```bash
test -f input/trivy_report.json && cp input/trivy_report.json output/trivy_report.json
```

Suggested command pattern:

```bash
mkdir -p output
trivy fs input/package-lock.json \
  --format json \
  --output output/trivy_report.json \
  --scanners vuln \
  --skip-db-update \
  --offline-scan
```

If the environment uses a custom Trivy cache, add:

```bash
--cache-dir /path/to/trivy-cache
```

## Parsing rules

Only keep findings where `Severity` is `HIGH` or `CRITICAL`.

Map fields this way:
- `package`: `PkgName`
- `version`: `InstalledVersion`
- `cve_id`: `VulnerabilityID`
- `severity`: `Severity`
- `fixed_version`: `FixedVersion` or `N/A`
- `title`: `Title`
- `url`: `PrimaryURL`

## CVSS extraction

Prefer scores in this order:
1. `CVSS.nvd.V3Score`
2. `CVSS.ghsa.V3Score`
3. `CVSS.redhat.V3Score`
4. `N/A`

Always emit `cvss_score` as a string in the final JSON.

## Reporting

Write exactly one JSON file with:

```json
{
  "findings": []
}
```

Sort findings by package, then version, then CVE identifier before writing the final report.
