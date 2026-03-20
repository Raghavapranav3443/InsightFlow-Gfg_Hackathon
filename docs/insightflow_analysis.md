# InsightFlow — Project Analysis

## What Is InsightFlow?

**InsightFlow** is a natural-language BI assistant that converts plain English questions into interactive dashboards — SQL, charts, KPI cards, and AI insights — in under 2 seconds. Built for the **GeeksforGeeks Classroom × MVSR Hyderabad Hackathon 2026**.

---

## Architecture Overview

```mermaid
graph LR
    A["User Question (NL)"] --> B["Schema Context Builder"]
    B --> C["Stage 1: LLM (Groq / Gemini)"]
    C --> D["SQL Validator (blocklist + regex)"]
    D --> E["SQLite Execution (read-only WAL)"]
    E --> F["Stage 2: Deterministic Viz Mapping"]
    F --> G["Post-Processor (9 rules)"]
    G --> H["Cannot-Answer Gate"]
    H --> I["React Dashboard"]
```

### Key Components

| Layer | Files | Responsibility |
|---|---|---|
| **Backend API** | [backend/main.py](file:///c:/Users/Rupesh/Desktop/Pranav/GfG_Hackathon-InsightFlow/InsightFLow_v3/backend/main.py) | FastAPI routes, rate limiting, input sanitization |
| **Ingestion** | [backend/ingest.py](file:///c:/Users/Rupesh/Desktop/Pranav/GfG_Hackathon-InsightFlow/InsightFLow_v3/backend/ingest.py) | CSV → SQLite, column classification, bucket SQL |
| **Query Pipeline** | [backend/query_pipeline.py](file:///c:/Users/Rupesh/Desktop/Pranav/GfG_Hackathon-InsightFlow/InsightFLow_v3/backend/query_pipeline.py) | Two-stage LLM pipeline, SQL execution, insight gen |
| **Post-Processor** | [backend/post_processor.py](file:///c:/Users/Rupesh/Desktop/Pranav/GfG_Hackathon-InsightFlow/InsightFLow_v3/backend/post_processor.py) | 9-rule chart correction, pivot, Pearson r, forecasting |
| **LLM Providers** | [backend/llm_providers.py](file:///c:/Users/Rupesh/Desktop/Pranav/GfG_Hackathon-InsightFlow/InsightFLow_v3/backend/llm_providers.py) | Multi-provider ladder (Groq + Gemini), caching, key rotation |
| **Frontend** | `frontend/src/` | React 18 + Vite, Recharts, PDF/PNG export |

---

## 🏆 Hackathon Angle

### Strengths — What Will Impress Judges

**1. Production-Grade Architecture in Hackathon Time**
The two-stage LLM pipeline (`query_pipeline.py`) is a genuine engineering decision — Stage 1 generates SQL only; Stage 2 does deterministic visualization mapping from actual row shapes. This eliminates the classic NL-to-chart hallucination bug. Judges who know ML engineering will notice this.

**2. Deterministic Visualization (Not LLM-Driven)**
Chart type selection is fully algorithmic (`infer_viz()`):
- 2 text + 1 numeric → grouped bar
- 0 text + 2 numeric → scatter
- 1 text + 1 numeric, ordinal → line
- ≤8 rows → pie (with auto-correction to bar if one slice >60%)

This avoids the most common failure mode of AI BI apps.

**3. Deep Post-Processing (9 Rules)**
Most hackathon projects use raw LLM output. InsightFlow runs a dedicated correction layer:
- Pie dominance detection + auto-conversion to bar with a UI badge
- Long → wide pivot for Recharts grouped bar
- Pearson r for scatter plots
- 3-step linear regression forecasting for line charts
- Tail merge for pie charts (merges small slices into "Other")
- Ambiguous column flagging (e.g., `product_availability_online`)

**4. Security Layer**
- SQL blocklist (`DROP`, `INSERT`, `UPDATE`, `DELETE`, `ATTACH`, `PRAGMA`, `SQLITE_MASTER`) validated with word-boundary regex
- SQLite opened with `?mode=ro` — writes structurally impossible
- 5MB file limit, CSV-only, filename sanitization
- Rate limiting (`slowapi`) on all routes
- Input sanitization to ASCII printable only

**5. Multi-Provider LLM Fallback**
`llm_providers.py` implements a full "ladder": Groq (3 keys) → Gemini (3 keys). On 429 or timeout, automatically rotates. 10-minute SHA-256 response cache reduces API calls by ~55% per the README.

**6. Live Demo Out-of-the-Box**
Bundled CSV: 11,789 customers × 25 columns (retail consumer behavior). One click on the landing page fires a real query. No setup needed for demo.

**7. Polish**
- Animated terminal demo on landing page
- Pipeline progress bar while query runs (step-by-step animation)
- AI dataset overview card on dataset load
- Chatbot widget on dashboard
- Full report generator (4-chart auto-report)
- PDF + per-chart PNG export
- Dark/light theme toggle
- Collapsible Data Dictionary sidebar with column role breakdown
- SQL transparency toggle on every chart

---

### Potential Hackathon Weaknesses

| Gap | Impact |
|---|---|
| Sessions are **in-memory only** — server restart wipes all sessions | Demo fragility |
| No user auth / multi-user isolation | Fine for hackathon, but visible |
| SQLite per-session means disk fills if many users upload CSVs | Not a demo problem |
| `start.py` auto-launcher assumes Python + Node on PATH | May fail on judge machines |
| Vercel deployment config exists but in-memory sessions + SQLite won't survive serverless cold starts | Misleading if judges try to deploy |
| CSS is in one giant `App.css` (55KB) | No modularity |

---

## 📦 Product Angle

### What It Actually Does Well as a Product

**Core value proposition is real**: Self-serve BI for non-technical users is a _massive_ market. Tableau costs $75/user/month. InsightFlow's UX is frictionless — upload CSV, ask question, get dashboard.

**The honesty gate is a genuine differentiator**: Most AI tools fabricate confident-looking wrong answers. InsightFlow explicitly refuses time-series queries when there's no date column, and surfaces `cannot_answer: true` with a clear reason. This is trust-building behavior.

**The two-stage pipeline is a moat**: The architecture (generate SQL → execute → visualize from real rows) is fundamentally more reliable than single-pass approaches. This is the correct way to build AI BI tools and would survive scrutiny from experienced engineers.

---

### Product Gaps to Address

**Critical (for any real launch)**

| Gap | What's Needed |
|---|---|
| **No persistence** | PostgreSQL or Supabase for sessions + uploaded data |
| **No auth** | Login system for user isolation (Google OAuth is easiest) |
| **Serverless incompatible** | Move to a persistent backend (Railway, Render, Fly.io) or use a managed DB |
| **Single dataset per session** | Users need workspaces with multiple datasets, saved queries |
| **No saved dashboards** | Users can't bookmark or share results |
| **CSV only (5MB)** | Real products need Excel, Google Sheets, direct DB connectors |

**Important (for growth)**

| Gap | What's Needed |
|---|---|
| No multi-table JOIN support | Schema introspection across related tables |
| No collaboration / sharing | Dashboard sharing via URL |
| No scheduled reports | Cron-based automated report delivery |
| No user-defined column annotations | Users may know domain context the LLM doesn't |
| Insight cards are text-only | Richer narrative format, highlight/bold, clickable deep-dives |

**Nice-to-Have**

| Feature | Why |
|---|---|
| Chart annotation (draw on chart) | Presentations |
| Slack / email integration | Report delivery |
| More chart types (candlestick, heatmap, funnel) | Domain-specific use cases |
| LLM-generated SQL → editable | Power users want to tweak SQL |

---

## Engineering Quality Assessment

| Area | Score | Notes |
|---|---|---|
| Backend architecture | ⭐⭐⭐⭐⭐ | Two-stage pipeline is correct; separation of concerns is clean |
| Security | ⭐⭐⭐⭐ | SQL blocklist, read-only SQLite, rate limiting, input sanitization |
| Error handling | ⭐⭐⭐⭐ | SQL retry on failure; graceful fallbacks at every stage |
| Frontend UX | ⭐⭐⭐⭐ | Pipeline animation, skeleton loaders, session persistence |
| Code organization | ⭐⭐⭐ | Backend is modular; frontend CSS is one 55KB file |
| Test coverage | ⭐ | No visible test files anywhere |
| Scalability | ⭐⭐ | In-memory sessions, SQLite = not production-scalable |
| Documentation | ⭐⭐⭐⭐ | README is thorough with architecture diagrams |

---

## Competitive Landscape

| Tool | NL to SQL | Charts | Upload CSV | Open Source | Free |
|---|---|---|---|---|---|
| **InsightFlow** | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tableau | ❌ | ✅ | ✅ | ❌ | ❌ |
| Power BI | ✅ (Copilot) | ✅ | ✅ | ❌ | Partial |
| Metabase | ✅ (basic) | ✅ | ❌ | ✅ | ✅ |
| Julius AI | ✅ | ✅ | ✅ | ❌ | Partial |
| ChartGPT | ✅ | ✅ | ✅ | ❌ | Partial |

InsightFlow is functionally competitive with paid tools in its core flow. Its differentiators: fully open-source, deterministic visualization (not LLM-guessed), honesty gate, and the 9-rule post-processor.

---

## Summary

### As a Hackathon Project ✅
InsightFlow is a **strong submission**. The engineering decisions (two-stage pipeline, deterministic viz mapping, post-processor, multi-provider failover) go well beyond typical hackathon quality. The live demo is instant and impressive. The security layer shows awareness of real risks. The UI has polish — animations, export, chatbot, dark mode.

**Key demo moments to emphasize to judges:**
1. The "cannot answer" honest refusal (time-series with no date column)
2. The pie → bar auto-correction with the badge explaining why
3. The SQL transparency toggle (shows exactly what was run)
4. The multi-provider fallback (Groq → Gemini on rate limit)
5. The 2-second end-to-end latency

### As a Product Concept 🚀
The **value proposition is real** and the market is large. InsightFlow would need persistent storage, auth, and multi-dataset support to be launchable. But the core pipeline is architecturally sound enough to build upon — it's not a throwaway prototype.

The most viable near-term path: deploy on Railway with a PostgreSQL backend, add Google OAuth, persist dashboards, and target **small business analysts** who work with CSV exports from their ERP/CRM but don't know SQL.
