from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
SUMMARY_CSV = RESULTS_DIR / "model_matrix_summary.csv"
VISUALS_DIR = RESULTS_DIR / "visuals"

TASK_ORDER = [
    "software-dependency-audit",
    "sec-financial-report",
    "sales-pivot-analysis",
]
CONDITION_ORDER = ["no-skill", "improved-skill"]
CONDITION_LABELS = {
    "no-skill": "No skill",
    "improved-skill": "Improved skill",
}
MODEL_ORDER = [
    "openhands/claude-sonnet-4-5-20250929",
    "openhands/gemini-3-flash-preview",
    "openhands/gemini-3-pro-preview",
    "openhands/kimi-k2-0711-preview",
    "openhands/minimax-m2.5",
]
MODEL_LABELS = {
    "openhands/claude-sonnet-4-5-20250929": "Claude Sonnet 4.5",
    "openhands/gemini-3-flash-preview": "Gemini 3 Flash",
    "openhands/gemini-3-pro-preview": "Gemini 3 Pro",
    "openhands/kimi-k2-0711-preview": "Kimi K2",
    "openhands/minimax-m2.5": "MiniMax M2.5",
}
TASK_LABELS = {
    "software-dependency-audit": "Dependency audit",
    "sec-financial-report": "SEC financial report",
    "sales-pivot-analysis": "Sales pivot analysis",
}
PASS_COLOR = "#1f7a4d"
FAIL_COLOR = "#c44536"
SKILL_COLOR = "#0b6e4f"
NO_SKILL_COLOR = "#d97b29"
TEXT_COLOR = "#1c1b1a"
MUTED_COLOR = "#6a645d"
GRID_COLOR = "#d8d2c8"
BG_COLOR = "#f8f4ec"


def load_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with SUMMARY_CSV.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row["model"]:
                continue
            rows.append(
                {
                    "task": row["task"],
                    "condition": row["condition"],
                    "model": row["model"],
                    "passed": row["passed"] == "True",
                    "runtime_seconds": float(row["runtime_seconds"]),
                    "event_count": float(row["event_count"]),
                }
            )
    return rows


def pass_rate_data(rows: list[dict[str, object]]) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for row in rows:
        grouped[(row["task"], row["condition"])].append(bool(row["passed"]))
    return {
        key: (sum(1 for item in values if item) / len(values)) * 100.0
        for key, values in grouped.items()
    }


def average_data(rows: list[dict[str, object]], field: str) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["task"], row["condition"])].append(float(row[field]))
    return {key: sum(values) / len(values) for key, values in grouped.items()}


def svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f'<rect width="{width}" height="{height}" fill="{BG_COLOR}"/>'
    )


def escape(text: object) -> str:
    return html.escape(str(text))


def draw_grouped_bars(
    title: str,
    subtitle: str,
    value_map: dict[tuple[str, str], float],
    max_value: float,
    y_suffix: str,
    file_name: str,
) -> None:
    width = 1100
    height = 640
    margin_left = 110
    margin_right = 40
    margin_top = 110
    margin_bottom = 110
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    group_gap = 70
    bar_width = 90
    inner_gap = 24
    total_group_width = 2 * bar_width + inner_gap
    start_x = margin_left + 60

    parts = [svg_header(width, height)]
    parts.append(
        f'<text x="{margin_left}" y="52" font-size="30" font-weight="700" fill="{TEXT_COLOR}" '
        f'font-family="Georgia, serif">{escape(title)}</text>'
    )
    parts.append(
        f'<text x="{margin_left}" y="80" font-size="15" fill="{MUTED_COLOR}" '
        f'font-family="Helvetica, Arial, sans-serif">{escape(subtitle)}</text>'
    )

    for tick in range(6):
        value = (max_value / 5) * tick
        y = margin_top + chart_h - (value / max_value) * chart_h
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="{GRID_COLOR}" stroke-width="1"/>')
        parts.append(
            f'<text x="{margin_left - 14}" y="{y + 5:.1f}" text-anchor="end" font-size="13" '
            f'fill="{MUTED_COLOR}" font-family="Helvetica, Arial, sans-serif">{value:.0f}{escape(y_suffix)}</text>'
        )

    for idx, task in enumerate(TASK_ORDER):
        group_x = start_x + idx * (total_group_width + group_gap)
        center_x = group_x + total_group_width / 2
        parts.append(
            f'<text x="{center_x:.1f}" y="{height - 42}" text-anchor="middle" font-size="14" '
            f'fill="{TEXT_COLOR}" font-family="Helvetica, Arial, sans-serif">{escape(TASK_LABELS[task])}</text>'
        )
        for cond_index, condition in enumerate(CONDITION_ORDER):
            value = value_map[(task, condition)]
            bar_h = (value / max_value) * chart_h
            x = group_x + cond_index * (bar_width + inner_gap)
            y = margin_top + chart_h - bar_h
            color = NO_SKILL_COLOR if condition == "no-skill" else SKILL_COLOR
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_h:.1f}" rx="8" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{y - 10:.1f}" text-anchor="middle" font-size="14" '
                f'fill="{TEXT_COLOR}" font-family="Helvetica, Arial, sans-serif">{value:.1f}{escape(y_suffix)}</text>'
            )

    legend_y = height - 82
    legend_x = width - 320
    for i, (label, color) in enumerate(
        [(CONDITION_LABELS["no-skill"], NO_SKILL_COLOR), (CONDITION_LABELS["improved-skill"], SKILL_COLOR)]
    ):
        x = legend_x + i * 150
        parts.append(f'<rect x="{x}" y="{legend_y - 12}" width="18" height="18" rx="4" fill="{color}"/>')
        parts.append(
            f'<text x="{x + 28}" y="{legend_y + 2}" font-size="14" fill="{TEXT_COLOR}" '
            f'font-family="Helvetica, Arial, sans-serif">{escape(label)}</text>'
        )

    parts.append("</svg>")
    (VISUALS_DIR / file_name).write_text("".join(parts), encoding="utf-8")


def draw_scorecard(rows: list[dict[str, object]]) -> None:
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in rows:
        grouped[(row["task"], row["condition"], row["model"])] = row
    max_runtime = max(float(row["runtime_seconds"]) for row in rows)

    width = 1500
    height = 610
    left = 280
    top = 110
    cell_w = 210
    cell_h = 64
    parts = [svg_header(width, height)]
    parts.append(
        f'<text x="60" y="52" font-size="30" font-weight="700" fill="{TEXT_COLOR}" '
        f'font-family="Georgia, serif">Model scorecard</text>'
    )
    parts.append(
        f'<text x="60" y="80" font-size="15" fill="{MUTED_COLOR}" '
        f'font-family="Helvetica, Arial, sans-serif">Each cell shows pass/fail plus a runtime bar for one task-condition-model run.</text>'
    )

    columns: list[tuple[str, str]] = []
    for task in TASK_ORDER:
        for condition in CONDITION_ORDER:
            columns.append((task, condition))

    for idx, model in enumerate(MODEL_ORDER):
        y = top + idx * cell_h + 36
        parts.append(
            f'<text x="60" y="{y:.1f}" font-size="15" fill="{TEXT_COLOR}" '
            f'font-family="Helvetica, Arial, sans-serif">{escape(MODEL_LABELS[model])}</text>'
        )

    for idx, (task, condition) in enumerate(columns):
        x = left + idx * cell_w
        parts.append(
            f'<text x="{x + cell_w / 2:.1f}" y="102" text-anchor="middle" font-size="14" fill="{TEXT_COLOR}" '
            f'font-family="Helvetica, Arial, sans-serif">{escape(TASK_LABELS[task])}</text>'
        )
        parts.append(
            f'<text x="{x + cell_w / 2:.1f}" y="124" text-anchor="middle" font-size="12" fill="{MUTED_COLOR}" '
            f'font-family="Helvetica, Arial, sans-serif">{escape(CONDITION_LABELS[condition])}</text>'
        )

    for row_idx, model in enumerate(MODEL_ORDER):
        for col_idx, (task, condition) in enumerate(columns):
            x = left + col_idx * cell_w
            y = top + row_idx * cell_h
            row = grouped[(task, condition, model)]
            passed = bool(row["passed"])
            fill = PASS_COLOR if passed else FAIL_COLOR
            label = "PASS" if passed else "FAIL"
            runtime = float(row["runtime_seconds"])
            card_w = cell_w - 14
            card_h = cell_h - 10
            track_x = x + 18
            track_y = y + 35
            track_w = card_w - 36
            track_h = 12
            bar_w = max(10, (runtime / max_runtime) * track_w)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="10" fill="{fill}" opacity="0.95"/>'
            )
            parts.append(
                f'<text x="{x + 18}" y="{y + 26}" font-size="15" font-weight="700" fill="white" '
                f'font-family="Helvetica, Arial, sans-serif">{label}</text>'
            )
            parts.append(
                f'<rect x="{track_x}" y="{track_y}" width="{track_w}" height="{track_h}" rx="6" fill="white" opacity="0.22"/>'
            )
            parts.append(
                f'<rect x="{track_x}" y="{track_y}" width="{bar_w:.1f}" height="{track_h}" rx="6" fill="white" opacity="0.92"/>'
            )
            parts.append(
                f'<text x="{x + card_w - 18}" y="{y + 26}" text-anchor="end" font-size="13" fill="white" '
                f'font-family="Helvetica, Arial, sans-serif">{runtime:.1f}s</text>'
            )

    legend_y = height - 34
    parts.append(f'<rect x="60" y="{legend_y - 10}" width="160" height="12" rx="6" fill="{GRID_COLOR}"/>')
    parts.append(f'<rect x="60" y="{legend_y - 10}" width="80" height="12" rx="6" fill="{TEXT_COLOR}" opacity="0.65"/>')
    parts.append(
        f'<text x="230" y="{legend_y}" font-size="13" fill="{MUTED_COLOR}" '
        f'font-family="Helvetica, Arial, sans-serif">Longer bar = longer runtime, scaled to the slowest run</text>'
    )

    parts.append("</svg>")
    (VISUALS_DIR / "model_scorecard.svg").write_text("".join(parts), encoding="utf-8")


def write_dashboard(rows: list[dict[str, object]]) -> None:
    pass_rates = pass_rate_data(rows)
    avg_runtime = average_data(rows, "runtime_seconds")
    cards = []
    for task in TASK_ORDER:
        no_skill = pass_rates[(task, "no-skill")]
        skill = pass_rates[(task, "improved-skill")]
        delta = skill - no_skill
        cards.append(
            f"""
            <div class="card">
              <h3>{escape(TASK_LABELS[task])}</h3>
              <p class="metric">{skill:.0f}% vs {no_skill:.0f}%</p>
              <p class="sub">Improved skill vs no skill pass rate</p>
              <p class="delta">{delta:+.0f} pts</p>
              <p class="sub">Avg runtime: {avg_runtime[(task, 'improved-skill')]:.1f}s vs {avg_runtime[(task, 'no-skill')]:.1f}s</p>
            </div>
            """
        )

    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OpenHands Skill Eval Visuals</title>
  <style>
    :root {{
      --bg: #f8f4ec;
      --panel: #fffdf8;
      --ink: #1c1b1a;
      --muted: #6a645d;
      --line: #d8d2c8;
      --accent: #0b6e4f;
      --warm: #d97b29;
    }}
    body {{
      margin: 0;
      font-family: Helvetica, Arial, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, #efe7d8 0, transparent 35%),
        linear-gradient(180deg, #f8f4ec, #f1ebdf);
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 40px 24px 56px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-family: Georgia, serif;
      font-size: 42px;
    }}
    p.lead {{
      max-width: 780px;
      color: var(--muted);
      line-height: 1.5;
      margin: 0 0 28px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px 20px;
      box-shadow: 0 10px 24px rgba(28, 27, 26, 0.05);
    }}
    .card h3 {{
      margin: 0 0 10px;
      font-size: 20px;
      font-family: Georgia, serif;
    }}
    .metric {{
      margin: 0;
      font-size: 30px;
      font-weight: 700;
    }}
    .delta {{
      margin: 10px 0 0;
      font-size: 24px;
      font-weight: 700;
      color: var(--accent);
    }}
    .sub {{
      margin: 6px 0 0;
      color: var(--muted);
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 16px;
      margin-bottom: 20px;
      box-shadow: 0 10px 24px rgba(28, 27, 26, 0.05);
    }}
    .panel img {{
      width: 100%;
      height: auto;
      display: block;
      border-radius: 14px;
    }}
    @media (max-width: 960px) {{
      .cards {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 34px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>OpenHands Skill Evaluation Results</h1>
    <p class="lead">These visuals summarize the model-specific runs across the three tutorial tasks. They focus on the cleanest comparison points: pass rate, runtime, and per-model outcomes for the no-skill vs improved-skill conditions.</p>
    <section class="cards">
      {''.join(cards)}
    </section>
    <section class="panel">
      <img src="pass_rate_by_task.svg" alt="Pass rate by task" />
    </section>
    <section class="panel">
      <img src="runtime_by_task.svg" alt="Average runtime by task" />
    </section>
    <section class="panel">
      <img src="model_scorecard.svg" alt="Model scorecard" />
    </section>
  </main>
</body>
</html>
"""
    (VISUALS_DIR / "index.html").write_text(html_text, encoding="utf-8")


def main() -> int:
    rows = load_rows()
    VISUALS_DIR.mkdir(parents=True, exist_ok=True)
    draw_grouped_bars(
        title="Pass rate by task",
        subtitle="Model-specific runs only. Higher is better.",
        value_map=pass_rate_data(rows),
        max_value=100.0,
        y_suffix="%",
        file_name="pass_rate_by_task.svg",
    )
    draw_grouped_bars(
        title="Average runtime by task",
        subtitle="Average seconds across model-specific runs. Lower is better.",
        value_map=average_data(rows, "runtime_seconds"),
        max_value=max(average_data(rows, "runtime_seconds").values()) * 1.15,
        y_suffix="s",
        file_name="runtime_by_task.svg",
    )
    draw_scorecard(rows)
    write_dashboard(rows)
    print(f"Wrote visuals to {VISUALS_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
