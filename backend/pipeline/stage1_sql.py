"""
pipeline/stage1_sql.py
──────────────────────────────────────────────────────────────────────────────
Stage 1: SQL generation via LLM.
Input:  schema context (token-trimmed) + sanitized user question
Output: {charts: [{title, sql}], kpis: [{label, sql, format}]}

Security: user prompt is wrapped in XML delimiters before being passed to LLM.
The LLM writes SQL ONLY — no chart types, no column mapping.
"""
from __future__ import annotations

from typing import Any, Dict, List

from llm.providers import call_llm
from llm.sanitizer import SYSTEM_INJECTION_GUARD, sanitize_user_input, wrap_for_prompt


def build_stage1_prompt(
    schema_context: str,
    user_prompt: str,
    table_name: str,
    error_feedback: str = "",
    last_contexts: list[dict] | None = None,
) -> str:
    """
    Build the Stage 1 prompt with prompt injection defense.
    user_prompt is sanitized and XML-wrapped before interpolation.
    """
    safe_prompt = sanitize_user_input(user_prompt, max_length=500)
    wrapped_prompt = wrap_for_prompt(safe_prompt)

    error_section = ""
    if error_feedback:
        error_section = f"""
⚠ PREVIOUS ATTEMPT FAILED — FIX THIS:
{error_feedback}
Write corrected SQL that avoids this error.

"""

    context_section = ""
    if last_contexts:
        context_section = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nPREVIOUS QUERIES CONTEXT\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, ctx in enumerate(last_contexts, 1):
            context_section += (
                f"Q{i}: {ctx['prompt']}\nSQL: {ctx['sql']}\n"
                f"Cols: {', '.join(ctx['columns'])}\n\n"
            )

    return f"""{SYSTEM_INJECTION_GUARD}

You are a SQL expert writing queries for SQLite.
YOUR ONLY JOB: write correct SQL. Do not decide chart types.

{schema_context}

{context_section}
USER QUESTION: {wrapped_prompt}
{error_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SQL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. SELECT only. Never DROP, INSERT, UPDATE, DELETE, ATTACH, PRAGMA.
2. Table name: {table_name} — no other tables exist.
3. Column names: use ONLY safe_names from the schema above. NEVER invent names.
4. Quote every column with double quotes: "age", "gender", "city_tier"
5. Always end with ORDER BY on the main grouping column.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PATTERN RULES WITH EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PATTERN A — Distribution of a dimension column:
  "Show customer distribution by shopping_preference"
  → SELECT "shopping_preference", COUNT(*) AS "count"
    FROM {table_name} GROUP BY "shopping_preference" ORDER BY "count" DESC

PATTERN B — Distribution by TWO dimensions:
  → SELECT "shopping_preference", "city_tier", COUNT(*) AS "count"
    FROM {table_name} GROUP BY "shopping_preference", "city_tier"
  CRITICAL: SELECT and GROUP BY all dimension columns.

PATTERN C — Continuous column bucketed (look for bucket_sql in schema):
  → Use the exact bucket_sql from schema. Alias MUST match schema alias.

PATTERN D — Average of a measure/score column by dimension:
  → SELECT "shopping_preference", AVG("brand_loyalty_score") AS "avg_brand_loyalty"
    FROM {table_name} GROUP BY "shopping_preference" ORDER BY "avg_brand_loyalty" DESC
  CRITICAL: score/measure columns → AVG(), not COUNT(). Never GROUP BY a score.

PATTERN E — KPI (single scalar):
  → SELECT COUNT(*) AS "total_customers" FROM {table_name}
  CRITICAL: KPI SQL must return EXACTLY ONE ROW with ONE VALUE.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPOND WITH ONLY THIS JSON:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "cannot_answer": false,
  "clarification_needed": false,
  "clarification_prompt": "",
  "reason": "",
  "charts": [
    {{
      "title": "Short descriptive title",
      "sql": "SELECT ... FROM {table_name} ..."
    }}
  ],
  "kpis": [
    {{
      "label": "Short label (3-5 words)",
      "sql": "SELECT COUNT(*) FROM {table_name}",
      "format": "number|currency|percentage|text"
    }}
  ]
}}

Limits: 1-3 chart SQLs, 2-4 KPI SQLs.

If question CANNOT be answered (time trends without date column, columns that don't exist):
{{"cannot_answer": true, "reason": "clear explanation in plain English", "charts": [], "kpis": []}}

If question is TOO AMBIGUOUS to answer without clarification:
{{"clarification_needed": true, "clarification_prompt": "Your specific question", "charts": [], "kpis": []}}
"""


async def run_stage1(
    schema_context: str,
    user_prompt: str,
    table_name: str,
    dataset_id: str,
    error_feedback: str = "",
    last_contexts: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Async Stage 1: call the LLM to generate SQL for the user's question.
    Returns the parsed LLM JSON response.
    """
    prompt = build_stage1_prompt(
        schema_context, user_prompt, table_name,
        error_feedback=error_feedback, last_contexts=last_contexts,
    )
    return await call_llm(prompt, dataset_id=dataset_id)
