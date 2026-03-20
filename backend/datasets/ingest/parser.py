"""
datasets/ingest/parser.py
──────────────────────────────────────────────────────────────────────────────
CSV → SQLite ingest pipeline.
Zero compiled dependencies — uses only Python stdlib.
Runs synchronously, so it MUST be called via asyncio.to_thread().

Pipeline:
  1. strip_safari_wrapper()  — remove bplist/HTML wrappers (GFG dataset only)
  2. detect_encoding()       — UTF-8 → latin-1 fallback
  3. csv.DictReader()        — parse rows as dicts
  4. sanitize_column_names() — safe SQL identifiers, no duplicates
  5. _infer_sql_type()       — INTEGER / REAL / TEXT per column
  6. classify_column()       — continuous/score/measure/dimension/id/datetime/text
  7. compute_bucket_sql()    — CASE WHEN SQL for continuous columns
  8. sqlite3.executemany()   — write all rows with WAL mode
  9. PII detection
"""
from __future__ import annotations

import csv
import io
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

# ── Module-level constants ─────────────────────────────────────────

AMBIGUOUS_COLUMNS = {"product_availability_online"}

# Compiled once at module load — used in classify_column()
_DATE_PAT = re.compile(
    r"^\d{4}-\d{2}-\d{2}|^\d{2}/\d{2}/\d{4}|^\d{4}/\d{2}/\d{2}"
)

# Basic heuristics for PII detection during ingest
_PII_KEYWORDS = re.compile(
    r"\b(ssn|social_security|passport|credit_card|card_number|email|phone|address|zipcode)\b",
    re.IGNORECASE
)


# ── 1. Safari WebArchive wrapper stripping ────────────────────────

def strip_safari_wrapper(raw: bytes) -> bytes:
    """Strip Safari WebArchive (bplist + HTML) wrapper from CSV bytes."""
    for header_marker in (b">age,", b">age,"):
        idx = raw.find(header_marker)
        if idx != -1:
            csv_bytes = raw.split(header_marker, 1)[1]
            tail = csv_bytes.find(b"</")
            if tail != -1:
                csv_bytes = csv_bytes.split(b"</", 1)[0]
            return csv_bytes

    is_wrapped = (
        raw.startswith(b"bplist")
        or raw.lower().startswith(b"<html>")
        or raw.find(b"WebResourceData", 0, 512) != -1
    )
    if not is_wrapped:
        return raw

    match = re.search(rb">([A-Za-z_][A-Za-z0-9_]*,)", raw)
    if match:
        marker = match.group(0)
        csv_bytes = raw.split(marker, 1)[1]
        tail = csv_bytes.find(b"</")
        return csv_bytes.split(b"</", 1)[0] if tail != -1 else csv_bytes

    return raw


# ── 2. Encoding detection ─────────────────────────────────────────

def detect_encoding(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


# ── 3-4. Column name sanitisation ────────────────────────────────

def sanitize_column_names(names: List[str]) -> List[str]:
    """Convert arbitrary header strings to safe SQL identifiers."""
    seen: Dict[str, int] = {}
    result: List[str] = []
    for name in names:
        safe_name = name if name is not None else "col"
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", str(safe_name).strip()).lower()
        safe = re.sub(r"_+", "_", safe).strip("_") or "col"
        if safe[0].isdigit():
            safe = "col_" + safe
        count = seen.get(safe, 0)
        seen[safe] = count + 1
        result.append(safe if count == 0 else f"{safe}_{count + 1}")
    return result


# ── 5. SQL type inference ─────────────────────────────────────────

def _infer_sql_type(values: List[str]) -> str:
    non_empty = [v for v in values if v is not None and str(v).strip()]
    if not non_empty:
        return "TEXT"
    int_pat = re.compile(r"^-?\d+$")
    float_pat = re.compile(r"^-?\d+\.\d+$")
    if all(int_pat.match(v) for v in non_empty):
        return "INTEGER"
    if all(int_pat.match(v) or float_pat.match(v) for v in non_empty):
        return "REAL"
    return "TEXT"


# ── 6. Column role classification ────────────────────────────────

def classify_column(sql_type: str, nunique: int, total: int, values: List[str]) -> str:
    """Map a column to one of: continuous | score | measure | dimension | id | datetime | text"""
    non_empty = [v for v in values if v is not None and str(v).strip()]

    if non_empty and _DATE_PAT.match(non_empty[0]):
        return "datetime"

    if sql_type == "TEXT":
        return "dimension" if nunique <= 20 else "text"

    if nunique <= 10:
        return "score"
    if nunique <= 20:
        return "measure"
    if sql_type == "INTEGER" and nunique / max(total, 1) > 0.99:
        return "id"
    return "continuous"


# ── 7. Bucket SQL for continuous columns ─────────────────────────

def compute_bucket_sql(safe_name: str, values: List[str]) -> str | None:
    nums: List[float] = []
    for v in values:
        try:
            nums.append(float(v))
        except (ValueError, TypeError):
            pass
    if not nums:
        return None

    mn, mx = min(nums), max(nums)
    if mx == mn:
        return None

    sorted_nums = sorted(nums)
    n = len(sorted_nums)

    def pct(p: float) -> float:
        idx = p * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        return sorted_nums[lo] + (idx - lo) * (sorted_nums[hi] - sorted_nums[lo])

    col = f'"{safe_name}"'
    b1 = int(mn)
    b2 = max(int(pct(0.25)), b1 + 1)
    b3 = max(int(pct(0.50)), b2 + 1)
    b4 = max(int(pct(0.75)), b3 + 1)

    return (
        f"CASE "
        f"WHEN {col} < {b2} THEN '{b1}–{b2-1}' "
        f"WHEN {col} < {b3} THEN '{b2}–{b3-1}' "
        f"WHEN {col} < {b4} THEN '{b3}–{b4-1}' "
        f"ELSE '{b4}+' END"
    )


# ── 8. Main entry point ───────────────────────────────────────────

def ingest_csv_to_sqlite(raw: bytes, db_path: str) -> Dict[str, Any]:
    """
    Full pipeline: raw CSV bytes → SQLite database + JSON schema payload.
    Called inside an asyncio thread pool.
    """
    raw = strip_safari_wrapper(raw)
    enc = detect_encoding(raw)
    text = raw.decode(enc, errors="replace").lstrip("\ufeff")

    text = text.replace('\r\n', '\n').replace('\r', '\n')
    reader = csv.DictReader(io.StringIO(text, newline=''))
    original_names = list(reader.fieldnames or [])
    if not original_names:
        raise ValueError("CSV has no header row")

    safe_names = sanitize_column_names(original_names)
    name_map = dict(zip(original_names, safe_names))

    def clean_value(val: str | None) -> str | None:
        if not val:
            return None
        s = str(val).strip()
        if s.upper() in ("NULL", "NA", "N/A", "NAN", "-") or s == "":
            return None
        return s

    rows = [{name_map[k]: clean_value(v) for k, v in row.items() if k in name_map} for row in reader]
    if not rows:
        raise ValueError("CSV has no data rows")

    total = len(rows)

    col_values: Dict[str, List[str]] = {}
    for s in safe_names:
        col_values[s] = []
    for row in rows:
        for s in safe_names:
            col_values[s].append(row.get(s, "") or "")

    table_name = "data"  # Always "data" in v2 (isolated per-dataset SQLite file)

    col_metas: List[Dict[str, Any]] = []
    col_defs: List[str] = []
    pii_detected = False

    for orig, safe in zip(original_names, safe_names):
        vals = col_values[safe]
        sql_type = _infer_sql_type(vals)
        non_empty = [v for v in vals if v is not None and str(v).strip()]
        nunique = len(set(non_empty))
        role = classify_column(sql_type, nunique, total, vals)
        samples: List[str] = []
        for v in dict.fromkeys(v for v in non_empty if v).keys():
            samples.append(v)
            if len(samples) == 3:
                break
        bucket_sql = compute_bucket_sql(safe, vals) if role == "continuous" else None

        # Basic PII detection
        if _PII_KEYWORDS.search(safe) or _PII_KEYWORDS.search(orig):
            pii_detected = True

        col_metas.append({
            "original_name": orig,
            "safe_name": safe,
            "role": role,
            "sql_type": sql_type,
            "nunique": nunique,
            "samples": samples,
            "bucket_sql": bucket_sql,
            "is_ambiguous": (safe in AMBIGUOUS_COLUMNS),
        })
        col_defs.append(f'"{safe}" {sql_type}')

    has_date = any(c["role"] == "datetime" for c in col_metas)

    # Write to SQLite
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sqlite3.connect(str(db), check_same_thread=False) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            conn.execute(f'CREATE TABLE "{table_name}" ({", ".join(col_defs)})')
            placeholders = ", ".join("?" for _ in safe_names)
            conn.executemany(
                f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                [[row.get(s) for s in safe_names] for row in rows],
            )
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Database write failed: {e}") from e
    
    # Return schema dict to be converted to JSON in Postgres
    return {
        "table_name": table_name,
        "row_count": total,
        "col_count": len(safe_names),
        "columns": col_metas,
        "has_date_column": has_date,
        "pii_detected": pii_detected,
    }
