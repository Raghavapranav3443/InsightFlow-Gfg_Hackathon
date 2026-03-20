"""
pipeline/insight.py
──────────────────────────────────────────────────────────────────────────────
Insight and suggestion generation via LLM.
Runs after SQL execution and visualization mapping.

SECURITY: Row values from query results are checked for PII before sending
to external LLM APIs. If PII is detected, values are redacted.
"""
from __future__ import annotations

import itertools
from typing import Any, Dict, List

import structlog

from llm.providers import call_llm
from llm.sanitizer import SYSTEM_INJECTION_GUARD, sanitize_user_input, wrap_for_prompt

logger = structlog.get_logger()


def _summarise_rows(rows: List[Dict[str, Any]], max_rows: int = 15) -> str:
    """
    Compact result summary for the insight LLM prompt.
    Sorts by the largest numeric column descending so dominant values appear first.
    """
    if not rows:
        return "[] (empty result)"

    cols = list(rows[0].keys())

    # Find primary numeric column to sort by
    sort_col = None
    for c in reversed(cols):
        try:
            vals = [float(r[c]) for r in rows if r.get(c) is not None]
            if vals:
                sort_col = c
                break
        except (TypeError, ValueError):
            pass

    sorted_rows = rows
    if sort_col:
        try:
            sorted_rows = sorted(
                rows, key=lambda r: float(r.get(sort_col) or 0), reverse=True
            )
        except Exception:
            sorted_rows = rows

    sample = [r for r in itertools.islice(sorted_rows, max_rows)]
    lines = [
        f"columns: {cols}",
        f"total rows: {len(rows)}",
        f"rows (sorted by {sort_col or 'original order'} desc):",
    ]
    for r in sample:
        lines.append(f"  {dict(r)}")
    if len(rows) > max_rows:
        lines.append(f"  … ({len(rows) - max_rows} more rows)")
    return "\n".join(lines)


def _build_insight_prompt(
    user_prompt: str,
    charts_summary: str,
    schema_columns: List[str] | None = None,
) -> str:
    safe_question = sanitize_user_input(user_prompt)
    wrapped = wrap_for_prompt(safe_question)
    
    col_str = ""
    if schema_columns is not None:
        col_str = ", ".join(c for c in itertools.islice(schema_columns, 15))
    cols_ctx = f"\nRelevant columns: {col_str}" if col_str else ""

    return f"""{SYSTEM_INJECTION_GUARD}

Analyze the business results shown below.

ORIGINAL QUESTION: {wrapped}
{cols_ctx}

RESULTS:
{charts_summary}

Please provide:
1. A bulleted 'insight' (3-5 bullet points starting with •). Each bullet = one concrete finding.
2. A list of 'brief_insights' (3-5 concise, one-line business observations).
3. Exactly 3 'suggestions' (short follow-up questions, specific to this dataset and result).

Respond with ONLY this JSON:
{{
  "insight": "• Finding 1\\n• Finding 2\\n• Finding 3",
  "brief_insights": ["one-liner 1", "one-liner 2", "one-liner 3"],
  "suggestions": ["Follow-up Q1", "Follow-up Q2", "Follow-up Q3"]
}}"""


async def generate_insight(
    user_prompt: str,
    chart_results: List[Dict[str, Any]],
    schema_columns: List[str],
    dataset_id: str,
    pii_detected: bool = False,
) -> Dict[str, Any]:
    """
    Generate insight text + follow-up suggestions from chart result data.
    Redacts row values if PII was detected in the dataset.
    """
    if not chart_results:
        return {"insight": "", "brief_insights": [], "suggestions": []}

    # Build per-chart summaries
    summaries = []
    for chart in chart_results:
        title = chart.get("title", "Chart")
        rows = chart.get("rows", [])

        if pii_detected:
            # Replace all string values with [REDACTED] — numerics are safe
            rows = [
                {
                    k: "[REDACTED]" if isinstance(v, str) else v
                    for k, v in row.items()
                }
                for row in rows
            ]

        if rows:
            summaries.append(f"{title}:\n{_summarise_rows(rows, 15)}")

    if not summaries:
        return {"insight": "", "brief_insights": [], "suggestions": []}

    prompt = _build_insight_prompt(user_prompt, "\n\n".join(summaries), schema_columns)

    try:
        resp = await call_llm(prompt, dataset_id=f"{dataset_id}_insight")
        return {
            "insight": resp.get("insight", ""),
            "brief_insights": resp.get("brief_insights", []),
            "suggestions": resp.get("suggestions", []),
        }
    except Exception as exc:
        logger.warning("insight_generation_failed", error=str(exc))
        return {"insight": "", "brief_insights": [], "suggestions": []}
