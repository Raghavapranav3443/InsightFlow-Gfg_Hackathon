"""
pipeline/executor.py
──────────────────────────────────────────────────────────────────────────────
SQL validation using sqlglot AST parser + blocklist, then read-only execution.
This replaces the old keyword-only blocklist with a proper AST-level check.

Security model:
  - Only SELECT statements permitted (AST check, not string match)
  - Only the user's specific table permitted
  - Blocked node types: Drop, Insert, Update, Delete, Alter, Create, etc.
  - Blocked system table references: sqlite_master, sqlite_schema
  - Read-only SQLite URI (?mode=ro)
"""
from __future__ import annotations

import asyncio
import re
import sqlite3
from pathlib import Path
from typing import Any

import sqlglot
import sqlglot.expressions as exp
import structlog

from core.exceptions import ValidationError

logger = structlog.get_logger()

# ── Blocked node types ────────────────────────────────────────────────────────
_BLOCKED_NODE_TYPES = (
    exp.Drop, exp.Insert, exp.Update, exp.Delete,
    exp.Create, exp.Alter, exp.Command,
    exp.Use, exp.Pragma, exp.Transaction,
)

# Blocked system tables (case-insensitive substring match on resolved table names)
_BLOCKED_TABLES = {
    "sqlite_master", "sqlite_schema", "sqlite_sequence",
    "sqlite_stat1", "sqlite_stat2", "sqlite_stat3", "sqlite_stat4",
    "information_schema",
}

# Legacy keyword blocklist (secondary defense, word-boundary regex)
_BLOCKED_KEYWORDS = {
    "DROP", "INSERT", "UPDATE", "DELETE", "ATTACH",
    "PRAGMA", "SQLITE_MASTER", "SQLITE_SCHEMA",
}
_BLOCKLIST_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def validate_sql(sql: str, allowed_table: str) -> None:
    """
    Validate SQL using sqlglot AST.
    Raises ValidationError with a clear message if any rule is violated.
    This is the primary SQL security gate.
    """
    sql = sql.strip()

    # ── Stage 0: Basic string sanity ────────────────────────────────────────
    if not sql:
        raise ValidationError("SQL query is empty.")

    # ── Stage 1: Legacy blocklist (fast, handles non-parseable injection) ───
    m = _BLOCKLIST_RE.search(sql)
    if m:
        raise ValidationError(f"Blocked SQL keyword detected: {m.group()}")

    # ── Stage 2: AST parse ───────────────────────────────────────────────────
    try:
        statements = sqlglot.parse(sql, dialect="sqlite", error_level=sqlglot.ErrorLevel.RAISE)
    except sqlglot.errors.ParseError as e:
        raise ValidationError(f"SQL parse error: {e}")

    if not statements or len(statements) != 1:
        raise ValidationError("Exactly one SQL statement is required.")

    stmt = statements[0]

    # ── Stage 3: Only SELECT allowed ─────────────────────────────────────────
    if not isinstance(stmt, exp.Select):
        raise ValidationError(
            f"Only SELECT statements are permitted. Got: {type(stmt).__name__}"
        )

    # ── Stage 4: No blocked node types anywhere in the AST ───────────────────
    for node in stmt.walk():
        if isinstance(node, _BLOCKED_NODE_TYPES):
            raise ValidationError(
                f"Blocked SQL operation: {type(node).__name__}"
            )

    # ── Stage 5: Only the user's table is allowed ────────────────────────────
    tables_in_query = {
        t.name.lower()
        for t in stmt.find_all(exp.Table)
        if t.name
    }

    for tbl in tables_in_query:
        if tbl in _BLOCKED_TABLES:
            raise ValidationError(f"Access to system table '{tbl}' is not permitted.")
        if tbl != allowed_table.lower():
            raise ValidationError(
                f"Query references table '{tbl}' but only '{allowed_table}' is permitted."
            )

    if not tables_in_query:
        raise ValidationError(f"SQL does not reference the required table '{allowed_table}'.")

    logger.debug("sql_validated_ok", table=allowed_table)


def _make_db_uri(db_path: str) -> str:
    """Build a read-only SQLite connection URI."""
    posix = Path(db_path).resolve().as_posix()
    if posix.startswith("/"):
        return f"file://{posix}?mode=ro"
    return f"file:///{posix}?mode=ro"


def execute_sql_sync(sql: str, db_path: str) -> list[dict[str, Any]]:
    """
    Execute a validated SELECT query against the user's read-only SQLite database.
    Returns rows as a list of dicts.
    Raises RuntimeError on any DB error.
    """
    uri = _make_db_uri(db_path)
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        raise RuntimeError(f"SQL execution error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Query failed: {e}") from e


async def execute_sql(sql: str, db_path: str) -> list[dict[str, Any]]:
    """
    Async wrapper: runs execute_sql_sync in a thread pool.
    Required because sqlite3 is blocking — we must not block the event loop.
    """
    return await asyncio.to_thread(execute_sql_sync, sql, db_path)
