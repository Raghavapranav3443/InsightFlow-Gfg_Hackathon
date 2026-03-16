# InsightFlow

**Smart Dashboards from Plain English**

InsightFlow converts natural-language business questions into interactive BI dashboards. Type a question, get SQL, charts, KPI cards, and an AI-written insight — in under two seconds.

> Built for the GFG Classroom × MVSR Hyderabad Hackathon 2026

---

## Demo

```
User: "Compare average online vs store spending by gender and city tier"

InsightFlow:
  → Builds SQL against the loaded dataset
  → Validates + executes on read-only SQLite
  → Runs 8 post-processing rules
  → Renders grouped bar chart with colour-coded series
  → Displays KPI cards + AI insight
  → Suggests 3 contextual follow-up questions
```

---

## Features

| Feature | Description |
|---|---|
| Natural language queries | No SQL required — type any business question |
| 6 chart types | Bar, grouped bar, line, area, pie, scatter — auto-selected deterministically |
| KPI cards | Key metrics with INR formatting (₹, lakh, crore) |
| Conversational refine | Follow-up prompts update existing charts in place |
| CSV upload | Upload any CSV — columns are auto-classified into 7 roles |
| AI dataset overview | Plain-English summary generated on first load, cached |
| Auto follow-up suggestions | 3 contextual next questions after every result |
| Per-chart PNG download | Download individual charts as images |
| PDF export | Full dashboard as landscape A4 PDF |
| Query history | Every query logged with chart types and timestamps |
| Honesty system | Refuses to answer unanswerable questions — never fabricates |
| SQL transparency | Every chart shows the exact SQL that generated it |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · Python 3.10+ |
| Database | SQLite with WAL mode · per-session databases |
| LLM | Groq API · llama-3.3-70b-versatile |
| Frontend | React 18 · Vite · Recharts |
| Export | html-to-image · jsPDF |
| Session | In-memory dict · 30-minute TTL |

---

## Architecture

```
User question
      │
      ▼
Schema context builder  ──── Token trimming (~55% fewer tokens per query)
      │                       Alias injection (prevents column hallucination)
      ▼
Groq LLM (Stage 1)      ──── SQL generation only
      │                       Key rotation on 429 (instant failover)
      │                       Response cache (zero cost on duplicate queries)
      ▼
SQL validator           ──── Blocklist: DROP/INSERT/UPDATE/DELETE/ATTACH/PRAGMA
      │                       Word-boundary regex (prevents substring bypass)
      │                       Table name verification
      ▼
SQLite execution        ──── Read-only URI mode (?mode=ro)
      │                       Per-session WAL database
      ▼
infer_viz (Stage 2)     ──── Deterministic chart type mapping from result shape
      │                       No LLM — result columns tell us everything
      ▼
Post-processor          ──── 8 correction rules (pie→bar, pivot, Pearson r, …)
      │
      ▼
Cannot-answer gate      ──── Column validation, time-series guard, honesty refusals
      │
      ▼
React dashboard         ──── Recharts · sessionStorage persistence
```

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Groq API key** — free at [console.groq.com](https://console.groq.com)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/insightflow.git
cd insightflow
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=gsk_your_primary_key_here
GROQ_API_KEY_2=gsk_your_second_key_here      # optional — key rotation
GROQ_API_KEY_3=gsk_your_third_key_here       # optional — key rotation
GROQ_MODEL=llama-3.3-70b-versatile
```

> **Rate limit tip:** Add multiple free Groq keys. On a 429, InsightFlow instantly rotates to the next key — no waiting.

### 3. Launch

```bash
python start.py
```

This single command:
- Creates a Python virtual environment
- Installs all backend dependencies
- Installs all frontend dependencies
- Starts the FastAPI backend on port 8000
- Starts the Vite dev server on port 5173
- Opens your browser automatically

Then navigate to `http://localhost:5173` and go to **Upload** to load the sample dataset.

---

## Manual Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
insightflow/
├── backend/
│   ├── main.py              FastAPI app — all routes
│   ├── ingest.py            CSV → SQLite pipeline (pure stdlib)
│   ├── query_pipeline.py    LLM pipeline, SQL validation, caching, infer_viz
│   ├── post_processor.py    8-rule chart correction layer
│   ├── session_store.py     In-memory sessions with 30-min TTL
│   ├── schema_context.py    Schema string builder, token trimming, alias system
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx              Router · navbar with SVG logo
│       ├── App.css              Design system (~1600 lines)
│       ├── pages/
│       │   ├── Landing.jsx      Live terminal demo · architecture · demo queries
│       │   ├── Dashboard.jsx    Main dashboard · sessionStorage persistence
│       │   ├── Upload.jsx       CSV upload · column preview
│       │   └── History.jsx      Query history · clear button
│       ├── components/
│       │   ├── DynamicChart.jsx     6 chart types · axis labels · legend
│       │   ├── SharedComponents.jsx KpiCard · InsightCard · CannotAnswer · SqlToggle
│       │   ├── ExportButton.jsx     PDF export
│       │   └── DiagnosticModal.jsx  Groq key diagnostics
│       └── utils/
│           ├── api.js           All API calls
│           ├── session.js       sessionStorage session ID
│           └── formatters.js    KPI value formatting
├── data/
│   └── Customer_Behaviour__Online_vs_Offline_.csv
├── start.py                 One-click launcher
└── .env.example
```

---

## API Reference

| Method | Route | Description |
|---|---|---|
| GET | `/health` | System status, key validity |
| GET | `/health/summary` | Compact status |
| GET | `/debug-llm` | Raw Groq test call |
| POST | `/preload` | Load the bundled GFG dataset |
| POST | `/upload-csv` | Ingest a user-uploaded CSV |
| GET | `/schema` | Session schema with column metadata |
| POST | `/query` | Natural language → charts + KPIs + insight |
| POST | `/refine` | Follow-up → modified charts |
| DELETE | `/history` | Clear session query history |
| POST | `/overview` | AI dataset overview (generated once per load) |
| GET | `/history` | Session query timeline |

All endpoints accept `X-Session-ID` header for session routing.

---

## The Pipeline in Detail

### Stage 1 — SQL generation (LLM)

The LLM receives a token-trimmed schema context and generates SQL only — no chart decisions. The context includes:

- Column names, types, roles (7 categories), sample values
- `bucket_sql` and standardised aliases for continuous columns (`age` → `age_group`)
- 8 annotated SQL patterns with examples (A through H)
- Dataset-specific constraints (e.g. no date column = no time-series)

On validation or execution failure, the error is fed back to Stage 1 and retried once with the exact error message in the prompt.

### Stage 2 — Visualisation mapping (deterministic)

No LLM. The actual result rows determine chart type algorithmically:

| Result shape | Chart type |
|---|---|
| 2 text cols + 1 numeric | `grouped_bar` (long form — post-processor pivots) |
| 1 text col + 2+ numeric cols | `grouped_bar` (wide form) |
| 2 numeric cols only | `scatter` |
| 1 text col + 1 numeric, ordinal labels | `line` |
| 1 text col + 1 numeric, ≤8 rows | `pie` |
| 1 text col + 1 numeric, >8 rows | `bar` |

`x_col` and `y_cols` are always actual keys from `rows[0]` — column name hallucination is structurally impossible.

Mixed-scale columns are filtered: if any column's median is >1000× smaller than the reference column, it is excluded from `y_cols` (e.g. `avg_delivery_days=3` vs `avg_spend=60000`).

### Post-processor — 8 rules

1. **Empty guard** — no data → warning, no chart
2. **Row limit** — >200 rows → truncate + warning
3. **Bar/line limit** — >50 rows → truncate to 20
4. **Pie tail merge** — 5 < n ≤ 12 → merge small slices into "Other"
5. **Pie dominance** — one category >60% → auto-convert to bar + badge
6. **Grouped bar pivot** — long form → wide form (color_col dimension becomes series)
7. **Pearson r** — scatter charts auto-compute correlation coefficient
8. **Ambiguity flag** — known ambiguous columns get a warning note

### Honesty system

When a query cannot be answered, InsightFlow returns a labeled "Cannot answer" card with an explanation — never a fabricated chart. The UI distinguishes between:

- **Data-boundary refusal** — wrong column, time-series on no-date dataset, no charts generated → shows "Honesty by design" badge
- **Technical failure** — rate limit, timeout, parse error → shows plain error message without the badge

---

## Rate Limit Strategy

Three layers working together:

**Key rotation** — Add multiple Groq keys to `.env` as `GROQ_API_KEY`, `GROQ_API_KEY_2`, `GROQ_API_KEY_3`. On a 429, the next key is tried instantly with zero wait time. Only after all keys are exhausted does the system pause briefly.

**Response cache** — SHA-256 hash of the prompt → result dict. Identical queries return from cache with zero API calls. Cache lives for the server process lifetime.

**Token trimming** — Schema context only expands columns with keyword overlap to the query. Continuous columns always get full detail (they need `bucket_sql`). All other columns are sent as one-line summaries. Typical reduction: ~55% fewer tokens per query.

---

## Security

- All generated SQL is validated against a blocklist (`DROP`, `INSERT`, `UPDATE`, `DELETE`, `ATTACH`, `PRAGMA`, `SQLITE_MASTER`) using word-boundary regex — not substring matching
- SQLite opens in `?mode=ro` read-only URI mode — writes are impossible at the database level regardless of SQL content
- Each session gets its own SQLite database file — no cross-session data access
- File upload is limited to `.csv` extension, 5 MB max, UTF-8 or latin-1 encoding

---

## Demo Queries

Load the bundled GFG dataset, then try these confirmed queries:

```
Show customer distribution by shopping preference and city tier
Compare average online vs store spending by gender and city tier
Show age distribution of customers by shopping preference
Show distribution of daily internet hours by city tier
Compare brand loyalty scores across shopping preferences
Show monthly online orders vs store visits by city tier
```

---

## Dataset

The bundled dataset is **Customer Behaviour: Online vs Offline** — 11,789 customers × 25 columns covering retail consumer behaviour.

| Group | Columns |
|---|---|
| Demographics | age, gender, city\_tier, monthly\_income |
| Spending | avg\_online\_spend, avg\_store\_spend, monthly\_online\_orders, monthly\_store\_visits |
| Digital behaviour | daily\_internet\_hours, smartphone\_usage\_years, social\_media\_hours |
| Psychographic scores | brand\_loyalty\_score, discount\_sensitivity, impulse\_buying\_score, tech\_savviness (all 1–10) |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Primary Groq API key |
| `GROQ_API_KEY_2` | No | Second key for rotation |
| `GROQ_API_KEY_3` | No | Third key for rotation |
| `GROQ_MODEL` | No | Model name (default: `llama-3.3-70b-versatile`) |

---

## Known Limitations

- No date column in the bundled dataset — time-series queries are declined with an explanation
- Session data is in-memory — server restart clears all sessions
- Upload limit is 5 MB — large CSVs should be sampled before uploading
- Dark mode is not implemented

---

## License

MIT

---

*InsightFlow — Built for GFG Classroom × MVSR Hyderabad Hackathon 2026*
