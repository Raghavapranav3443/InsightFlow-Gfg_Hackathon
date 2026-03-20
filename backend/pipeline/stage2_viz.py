"""
pipeline/stage2_viz.py
──────────────────────────────────────────────────────────────────────────────
Stage 2: Deterministic visualization mapping from actual SQL result rows.
NO LLM CALL — this is fully algorithmic.

Decision tree:
  2 text + 1 numeric  → grouped_bar (long form, post-processor pivots)
  1 text + 2+ numeric → grouped_bar (wide form, compatible scales only)
  0 text + 2 numeric  → scatter
  1 text + 1 numeric, ordinal x → line
  1 text + 1 numeric, ≤8 rows  → pie
  1 text + 1 numeric, >8 rows  → bar
  fallback            → bar

This eliminates hallucinated column names and wrong chart types that occur
when the LLM decides visualization before seeing real result data.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List
import itertools


def _is_numeric_col(col: str, rows: List[Dict[str, Any]]) -> bool:
    """True if the column holds numeric values in the result rows."""
    vals = [r.get(col) for r in itertools.islice(rows, 20) if r.get(col) is not None]
    if not vals:
        return False
    try:
        [float(v) for v in vals]
        return True
    except (TypeError, ValueError):
        return False


def _is_ordinal_text(col: str, rows: List[Dict[str, Any]]) -> bool:
    """
    True if the text column holds ordinal/sequential labels that benefit
    from a line chart over a bar chart.
    Examples: "18-32", "33-47", "64+", "Tier 1", "1", "2"
    At least 80% of non-null values must match a recognized ordinal pattern.
    """
    vals = [str(r.get(col, "")) for r in rows if r.get(col) is not None]
    if len(vals) < 2:
        return False

    range_pat = re.compile(r"^\d+[\-–]\d+$|^\d+\+$")
    tier_pat = re.compile(r"^tier\s+\d+$", re.IGNORECASE)
    digit_pat = re.compile(r"^\d+$")

    threshold = 0.8
    n = len(vals)

    if sum(1 for v in vals if range_pat.match(v.strip())) / n >= threshold:
        return True
    if sum(1 for v in vals if tier_pat.match(v.strip())) / n >= threshold:
        return True
    if sum(1 for v in vals if digit_pat.match(v.strip())) / n >= threshold:
        return True

    return False


def _compatible_numeric_cols(cols: List[str], rows: List[Dict[str, Any]]) -> List[str]:
    """
    Return only numeric columns on compatible scales (max 3).
    Rejects columns whose median is >1000x smaller than the reference
    to prevent invisible series on charts.
    """
    if len(cols) == 1:
        return cols

    def median_val(col: str) -> float:
        vals = []
        for r in rows:
            v = r.get(col)
            if v is not None:
                try:
                    vals.append(abs(float(v)))
                except (TypeError, ValueError):
                    pass
        if not vals:
            return 0.0
        vals.sort()
        return vals[len(vals) // 2]

    medians = {c: median_val(c) for c in cols}
    max_med = max(medians.values()) or 1
    compatible = [c for c in itertools.islice(cols, 3)]
    if not compatible:
        compatible = [sorted(cols, key=lambda c: medians[c], reverse=True)[0]]

    compatible.sort(key=lambda c: medians[c], reverse=True)
    return [c for c in itertools.islice(compatible, 3)]


def infer_viz(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministically infer chart type and column mapping.
    Called with ACTUAL rows from SQLite — never guesses column existence.
    """
    if not rows:
        return {"type": "bar", "x_col": "", "y_cols": [], "color_col": None}

    cols = list(rows[0].keys())
    n_rows = len(rows)
    t_cols = [c for c in cols if not _is_numeric_col(c, rows)]
    n_cols = [c for c in cols if _is_numeric_col(c, rows)]

    # 2 text + 1 numeric → grouped_bar (post-processor pivots long→wide)
    if len(t_cols) == 2 and len(n_cols) == 1:
        return {
            "type": "grouped_bar",
            "x_col": t_cols[0],
            "y_cols": n_cols,
            "color_col": t_cols[1],
        }

    # 1 text + 2+ numeric → grouped_bar wide form
    if len(t_cols) == 1 and len(n_cols) >= 2:
        safe_y = _compatible_numeric_cols(n_cols, rows)
        return {
            "type": "grouped_bar",
            "x_col": t_cols[0],
            "y_cols": safe_y,
            "color_col": None,
        }

    # 2 numeric only → scatter
    if len(t_cols) == 0 and len(n_cols) == 2:
        return {
            "type": "scatter",
            "x_col": n_cols[0],
            "y_cols": [n_cols[1]],
            "color_col": None,
        }

    # 1 text + 1 numeric
    if len(t_cols) == 1 and len(n_cols) == 1:
        if _is_ordinal_text(t_cols[0], rows):
            return {"type": "line", "x_col": t_cols[0], "y_cols": n_cols, "color_col": None}
        if n_rows <= 8:
            return {"type": "pie", "x_col": t_cols[0], "y_cols": n_cols, "color_col": None}
        return {"type": "bar", "x_col": t_cols[0], "y_cols": n_cols, "color_col": None}

    # Fallback
    if cols:
        x = cols[0]
        y = [c for c in itertools.islice(cols, 1, None) if _is_numeric_col(c, rows)]
        if not y and len(cols) > 1:
            y = [cols[1]]
        return {"type": "bar", "x_col": x, "y_cols": y, "color_col": None}

    return {"type": "bar", "x_col": "", "y_cols": [], "color_col": None}
