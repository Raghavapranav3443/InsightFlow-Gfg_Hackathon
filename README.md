# InsightFlow

**Conversational AI for Instant Business Intelligence Dashboards**

> Type a plain-English business question. Get SQL, charts, KPIs, and an AI insight summary in seconds.

Built for **GFG Classroom × MVSR Hyderabad Hackathon 2026**.

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd insightflow
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Get a free Gemini API key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

### 2. Run

```bash
python start.py
```

This automatically creates a virtual environment, installs all dependencies, and launches both servers.

- Frontend → http://localhost:5173  
- Backend  → http://localhost:8000

### 3. Requirements

- Python 3.11+ (any version, no compilation needed)
- Node.js 18+
- npm 9+

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python · FastAPI · SQLite · httpx |
| AI | Google Gemini (`gemini-2.0-flash`) |
| Frontend | React 18 · Vite · Recharts |
| Export | html-to-image · jsPDF |
| Deps | Zero compiled packages (no pandas, no pydantic) |

---

## Features

- **Natural language → dashboard** — type any business question, get charts + KPIs + AI insight
- **Honest AI** — explicitly refuses questions the data cannot answer, never fabricates
- **6 chart types** — bar, grouped bar, line, area, pie, scatter with auto-selection and Python post-processing
- **Conversational refinement** — follow-up prompts update charts in place
- **SQL visibility** — toggle per-chart SQL with one click
- **Correlation detection** — Pearson r computed and reported on scatter charts
- **CSV upload** — bring your own dataset
- **PDF export** — full dashboard to PDF
- **Session history** — timeline of all queries with re-run capability
- **Live diagnostics** — status bar shows exactly what's working; diagnostic modal with direct test command

---

## Debugging Gemini

If queries return "AI service unavailable", check the terminal for `[Gemini] Status:` lines.

To test directly:
```bash
backend\venv\Scripts\python.exe -c "
import httpx, os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.env'))
key = os.getenv('GEMINI_API_KEY')
r = httpx.post(
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
  headers={'x-goog-api-key': key, 'Content-Type': 'application/json'},
  json={'contents': [{'parts': [{'text': 'Say hello'}]}]}
)
print(r.status_code, r.text[:500])
"
```

---

## Demo Script (10 min)

| Time | Action |
|---|---|
| 0–1m | Landing page → explain concept → click Open Dashboard |
| 1–3m | Q1: "Show customer distribution by shopping preference and city tier" |
| 3–6m | Q2: "Compare average online vs in-store spending across age groups and genders" · toggle SQL |
| 6–9m | Q3: "Which segments have the highest online value — does tech savviness predict it?" |
| 9–10m | Follow-up: "Now filter to Tier 1 cities only" → export PDF → History page |
