"""
pipeline/postprocessor.py
──────────────────────────────────────────────────────────────────────────────
Chart correction pipeline that runs AFTER SQL execution and Viz Inference.
Rules are applied in order:
  1. Empty result         → set warning, return early
  2. Grouped bar pivot    → long → wide form for Recharts
  3. Raw row dump guard   → block >200 rows without aggregation
  4. Truncate large       → cap bar/line/area at 20 rows
  5. Pie tail merge       → merge tail slices into "Other" (5 < n <= 12)
  6. Pie → bar            → convert if >8 categories OR dominant slice >60%
  7. Scatter correlation  → compute Pearson r, add note
  8. Line Forecasting     → 3-step linear regression projection
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


# ── Pearson r & Linear Regression ─────────────────────────────────────────────

def pearson_r(xs: List[float], ys: List[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def linear_regression(xs: List[float], ys: List[float]) -> Tuple[float, float] | None:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    dx_sq = sum((x - mx) ** 2 for x in xs)
    if dx_sq == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / dx_sq
    intercept = my - slope * mx
    return slope, intercept


# ── Pivot for grouped bar ─────────────────────────────────────────────────────

def pivot_for_grouped_bar(
    rows: List[Dict[str, Any]], x_col: str, color_col: str, y_col: str
) -> List[Dict[str, Any]]:
    """
    Convert long-form SQL result to wide-form for Recharts grouped bar.
    """
    pivot: Dict[str, Dict[str, Any]] = {}
    x_order: List[str] = []
    color_vals: List[str] = []

    for row in rows:
        x_val = str(row.get(x_col, ""))
        c_val = str(row.get(color_col, ""))
        y_val = row.get(y_col, 0)

        if x_val not in pivot:
            pivot[x_val] = {}
            x_order.append(x_val)
        pivot[x_val][c_val] = y_val

        if c_val not in color_vals:
            color_vals.append(c_val)

    return [
        {x_col: x_val, **{c: pivot[x_val].get(c, 0) for c in color_vals}}
        for x_val in x_order
    ]


# ── Main post-processor ───────────────────────────────────────────────────────

def post_process_chart(
    chart_spec: Dict[str, Any], rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Apply chart correction rules.
    Mutates and returns chart_spec with 'rows' added and properties updated.
    """
    chart_type = chart_spec.get("type", "bar")
    x_col = chart_spec.get("x_col", "")
    color_col = chart_spec.get("color_col")

    # 1. Empty result
    if not rows:
        chart_spec["warning"] = "no_matching_data"
        chart_spec["rows"] = []
        return chart_spec

    # 2. Grouped bar long → wide pivot
    if chart_type == "grouped_bar" and color_col:
        y_cols = chart_spec.get("y_cols", [])
        y_col = y_cols[0] if y_cols else None
        if y_col:
            rows = pivot_for_grouped_bar(rows, x_col, color_col, y_col)
            if rows:
                chart_spec["y_cols"] = [k for k in rows[0] if k != x_col]

    # 3. Raw row dump guard
    if len(rows) > 200:
        chart_spec["warning"] = (
            f"Query returned {len(rows)} rows — too many to visualise. "
            "Add a GROUP BY clause or more specific filters."
        )
        while len(rows) > 20:
            rows.pop()
        chart_spec["rows"] = rows
        return chart_spec

    # 4. Truncate large charts
    if len(rows) > 50 and chart_type in ("bar", "line", "area", "grouped_bar"):
        while len(rows) > 20:
            rows.pop()

    # 5. Pie tail merge
    if chart_type == "pie":
        y_cols = chart_spec.get("y_cols", [])
        y_col = y_cols[0] if y_cols else None
        if y_col and 5 < len(rows) <= 12:
            try:
                sorted_rows = sorted(
                    rows, key=lambda r: float(r.get(y_col) or 0), reverse=True
                )
                top = list(sorted_rows)
                while len(top) > 5:
                    top.pop()
                tail_sum = 0.0
                for i in range(5, len(sorted_rows)):
                    tail_sum += float(sorted_rows[i].get(y_col) or 0)
                rows = top + ([{x_col: "Other", y_col: tail_sum}] if tail_sum > 0 else [])
            except (TypeError, ValueError):
                pass

    # 6. Pie → bar guard
    if chart_type == "pie":
        y_cols = chart_spec.get("y_cols", [])
        y_col = y_cols[0] if y_cols else None
        convert_to_bar = len(rows) > 8
        if not convert_to_bar and y_col:
            try:
                total = sum(float(r.get(y_col) or 0) for r in rows)
                if total > 0:
                    max_share = max(float(r.get(y_col) or 0) for r in rows) / total
                    convert_to_bar = max_share > 0.6
            except (TypeError, ValueError):
                pass
        if convert_to_bar:
            chart_type = "bar"
            chart_spec["type"] = "bar"

    # 7. Scatter Pearson r
    if chart_type == "scatter":
        y_cols = chart_spec.get("y_cols", [])
        y_col = y_cols[0] if y_cols else None
        if y_col:
            xs: list[float] = []
            ys: list[float] = []
            for r in rows:
                try:
                    xs.append(float(r.get(x_col, 0)))
                    ys.append(float(r.get(y_col, 0)))
                except (KeyError, TypeError, ValueError):
                    pass
            r_val = pearson_r(xs, ys)
            if r_val is not None:
                strength = (
                    "strong" if abs(r_val) >= 0.5
                    else "moderate" if abs(r_val) >= 0.3
                    else "weak / no"
                )
                direction = "positive" if r_val >= 0 else "negative"
                chart_spec["correlation_note"] = (
                    f"Pearson r = {r_val:.3f} — {strength} {direction} correlation"
                )

    # 8. Line Forecasting
    if chart_type == "line":
        y_cols = chart_spec.get("y_cols", [])
        if y_cols:
            y_col = y_cols[0]
            xs: list[float] = [float(i) for i in range(len(rows))]
            ys: list[float] = []
            valid_x: list[float] = []
            for i, r in enumerate(rows):
                try:
                    val = float(r.get(y_col)) # type: ignore
                    ys.append(val)
                    valid_x.append(float(i))
                except (TypeError, ValueError):
                    pass

            if len(ys) >= 3:
                model = linear_regression(valid_x, ys)
                if model:
                    slope, intercept = model
                    forecast_key = f"{y_col}_forecast"
                    last_obj = rows[-1].copy() if rows else {}

                    last_obj.update({forecast_key: last_obj.get(y_col)})
                    rows[-1] = last_obj

                    for step in range(1, 4):
                        new_x = (xs[-1] if xs else 0) + step
                        pred_y = float(slope * new_x + intercept)
                        rows.append({
                            x_col: f"Next +{step}",
                            forecast_key: float(f"{pred_y:.2f}")
                        })

                    if forecast_key not in chart_spec["y_cols"]:
                        chart_spec["y_cols"].append(forecast_key)

                    note = chart_spec.get("note", "")
                    chart_spec["note"] = (note + " 📈 Includes 3-step forecast projection.").strip()

    chart_spec["rows"] = rows
    return chart_spec
