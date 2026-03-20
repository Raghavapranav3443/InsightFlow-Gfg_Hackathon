# InsightFlow v2 — Architecture Document
**Version:** 2.0  
**Audience:** All developers and AI coding agents building this system  
**Rule:** If your planned change doesn't fit this structure, update this document and get approval — do NOT improvise a new location.

---

## 1. Technology Stack

| Layer | Technology | Version | Reason |
|---|---|---|---|
| Backend framework | FastAPI | 0.115+ | Async-native, auto OpenAPI, Python |
| Async server | Uvicorn | 0.30+ | ASGI, production-grade |
| Database (app data) | PostgreSQL | 16+ | ACID, relations, JSON columns |
| Database (user data) | SQLite (WAL) | stdlib | Per-dataset, read-only sandbox |
| ORM | SQLAlchemy 2.0 + asyncpg | 2.0+ | Async, typed |
| Migrations | Alembic | 1.13+ | Schema versioning |
| Cache / Rate limit | Redis 7 | 7.2+ | LLM cache, rate limiting, refresh tokens |
| Auth | python-jose + passlib | latest | JWT, bcrypt |
| OAuth | Authlib | latest | Google OAuth2 |
| HTTP client | httpx (async) | 0.27+ | Async LLM calls |
| SQL parsing | sqlglot | latest | AST-based SQL validation |
| Logging | structlog | latest | Structured JSON logs |
| Error tracking | Sentry SDK | latest | Exception capture |
| Package mgr | uv | latest | Fast Python deps |
| Frontend framework | React 18 + Vite | 18 / 5.x | Fast dev, modern |
| State management | Zustand | 4.x | Minimal, typed |
| Charts | Recharts | 2.x | Declarative, React-native |
| Styling | CSS Modules + custom tokens | — | Scoped, zero runtime |
| Real-time | EventSource (SSE) | — | Query progress streaming |
| Testing (BE) | pytest + pytest-asyncio | latest | Async test support |
| Testing (FE) | vitest + @testing-library/react | latest | Vite-native |
| E2E | Playwright | latest | Multi-browser |
| CI | GitHub Actions | — | Industry standard |
| Container | Docker + Docker Compose | — | Reproducible environments |
| Deployment | Railway (prod), Docker (local) | — | Simple PaaS |

---

## 2. Canonical Directory Structure

```
insightflow/
├── backend/                        ← FastAPI application
│   ├── alembic/                    ← Database migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── auth/                       ← Authentication system
│   │   ├── __init__.py
│   │   ├── dependencies.py         ← get_current_user FastAPI dependency
│   │   ├── models.py               ← Auth-related Pydantic models
│   │   ├── router.py               ← /auth/* endpoints
│   │   └── service.py              ← JWT, bcrypt, OAuth logic
│   ├── core/                       ← App-wide configuration & cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── config.py               ← Pydantic Settings (reads .env)
│   │   ├── database.py             ← PostgreSQL async engine + session
│   │   ├── redis.py                ← Redis client factory
│   │   ├── logging.py              ← structlog configuration
│   │   └── exceptions.py          ← Custom exception classes + handlers
│   ├── middleware/                  ← FastAPI middlewares
│   │   ├── __init__.py
│   │   ├── security.py             ← Security headers, CORS validation
│   │   └── request_id.py           ← X-Request-ID injection per request
│   ├── datasets/                   ← Dataset management feature
│   │   ├── __init__.py
│   │   ├── models.py               ← Dataset SQLAlchemy ORM + Pydantic schemas
│   │   ├── router.py               ← /datasets/* endpoints
│   │   ├── service.py              ← Dataset business logic
│   │   └── ingest/                 ← CSV ingestion sub-package
│   │       ├── __init__.py
│   │       ├── parser.py           ← CSV parsing, encoding detection, Safari wrapper
│   │       ├── classifier.py       ← Column role classification
│   │       ├── writer.py           ← SQLite WAL writer
│   │       └── pii_scanner.py      ← PII detection before LLM dispatch
│   ├── dashboards/                 ← Dashboard management feature
│   │   ├── __init__.py
│   │   ├── models.py               ← Dashboard ORM + Pydantic schemas
│   │   ├── router.py               ← /dashboards/* endpoints
│   │   └── service.py              ← Save, load, share, export logic
│   ├── pipeline/                   ← NL → dashboard query pipeline
│   │   ├── __init__.py
│   │   ├── runner.py               ← Orchestrates all stages, emits SSE events
│   │   ├── stage1_sql.py           ← SQL generation prompt + LLM call
│   │   ├── stage2_viz.py           ← Deterministic visualization mapping
│   │   ├── post_processor.py       ← 9-rule chart correction pipeline
│   │   ├── insight.py              ← Insight + suggestions LLM call
│   │   ├── executor.py             ← SQL validation (sqlglot) + SQLite execution
│   │   ├── schema_context.py       ← Schema context builder (token-aware)
│   │   └── router.py               ← /datasets/{id}/query, /refine, /chat endpoints (SSE)
│   ├── llm/                        ← LLM provider abstraction
│   │   ├── __init__.py
│   │   ├── providers.py            ← Multi-provider ladder: Groq → Gemini → Anthropic → OpenAI
│   │   ├── cache.py                ← Redis-backed LLM response cache
│   │   └── sanitizer.py           ← Prompt injection defense, user input sanitization
│   ├── users/                      ← User profile management
│   │   ├── __init__.py
│   │   ├── models.py               ← User ORM + Pydantic schemas
│   │   ├── router.py               ← /me, user preferences endpoints
│   │   └── service.py              ← User CRUD, soft delete, GDPR erasure
│   ├── tests/                      ← All backend tests
│   │   ├── unit/
│   │   │   ├── test_sql_validator.py
│   │   │   ├── test_post_processor.py
│   │   │   ├── test_ingest_parser.py
│   │   │   ├── test_schema_context.py
│   │   │   └── test_llm_cache.py
│   │   ├── integration/
│   │   │   ├── test_auth.py
│   │   │   ├── test_datasets.py
│   │   │   └── test_pipeline.py
│   │   ├── conftest.py             ← pytest fixtures (test DB, mock LLM, test user)
│   │   └── factories.py            ← Test data factories
│   ├── main.py                     ← FastAPI app factory, router registration, lifespan
│   └── pyproject.toml              ← Python deps, ruff config, mypy config
│
├── frontend/                       ← React 18 + Vite application
│   ├── src/
│   │   ├── design-system/          ← Design tokens and global CSS
│   │   │   ├── tokens.css          ← All CSS custom properties (colors, spacing, etc.)
│   │   │   ├── reset.css           ← Minimal CSS reset
│   │   │   └── typography.css      ← Font imports and text scale
│   │   ├── components/
│   │   │   ├── ui/                 ← Primitive, reusable UI components
│   │   │   │   ├── Button/
│   │   │   │   │   ├── Button.jsx
│   │   │   │   │   └── Button.module.css
│   │   │   │   ├── Input/
│   │   │   │   ├── Modal/
│   │   │   │   ├── Badge/
│   │   │   │   ├── Toast/
│   │   │   │   ├── Skeleton/
│   │   │   │   └── DataTable/      ← Virtualized data table
│   │   │   ├── charts/             ← Chart rendering components
│   │   │   │   ├── DynamicChart.jsx
│   │   │   │   ├── ChartCard.jsx   ← Chart + header + export + SQL toggle wrapper
│   │   │   │   └── ChartSkeleton.jsx
│   │   │   ├── dashboard/          ← Composed dashboard-specific components
│   │   │   │   ├── KpiCard.jsx
│   │   │   │   ├── InsightCard.jsx
│   │   │   │   ├── QueryInput.jsx
│   │   │   │   ├── SuggestionChips.jsx
│   │   │   │   ├── PipelineProgress.jsx ← Real SSE-driven progress
│   │   │   │   ├── CannotAnswer.jsx
│   │   │   │   └── OverviewCard.jsx
│   │   │   └── layout/             ← Layout components
│   │   │       ├── Sidebar.jsx
│   │   │       ├── TopBar.jsx
│   │   │       ├── CommandPalette.jsx
│   │   │       └── ChatDrawer.jsx
│   │   ├── pages/                  ← Route-level page components
│   │   │   ├── Landing.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Upload.jsx
│   │   │   ├── History.jsx
│   │   │   ├── Datasets.jsx        ← Dataset management list
│   │   │   ├── SavedDashboards.jsx
│   │   │   └── SharedView.jsx      ← Public read-only dashboard
│   │   ├── stores/                 ← Zustand state stores
│   │   │   ├── authStore.js
│   │   │   ├── datasetStore.js
│   │   │   ├── dashboardStore.js
│   │   │   └── uiStore.js
│   │   ├── lib/
│   │   │   ├── api/                ← Typed API client wrappers
│   │   │   │   ├── auth.js
│   │   │   │   ├── datasets.js
│   │   │   │   ├── dashboards.js
│   │   │   │   ├── pipeline.js     ← SSE-based query runner
│   │   │   │   └── client.js       ← Base fetch wrapper (auth header injection)
│   │   │   └── utils/
│   │   │       ├── formatters.js   ← Number, currency, date formatters
│   │   │       └── sse.js          ← EventSource / fetch-event-source wrapper
│   │   ├── App.jsx                 ← Router setup, auth guard, theme provider
│   │   └── main.jsx                ← Entry point
│   ├── tests/
│   │   ├── unit/
│   │   └── e2e/                    ← Playwright tests
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── data/                           ← Bundled demo dataset(s)
│   └── Customer_Behaviour__Online_vs_Offline_.csv
│
├── docker/                         ← Docker configuration
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf                  ← Production reverse proxy config
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── docker-compose.yml              ← Local dev (backend + frontend + postgres + redis)
├── docker-compose.prod.yml         ← Production (backend + nginx)
├── Makefile                        ← Dev commands: make dev, make test, make migrate
├── .env.example                    ← All env vars with documentation
├── .gitignore
└── README.md
```

---

## 3. Key Architectural Decisions

### 3.1 — Auth Flow
```
Browser → POST /auth/login → backend validates credentials
        ← access_token (JWT, 15min, in JSON body)
        ← refresh_token (JWT, 7d, httpOnly cookie)

Browser → GET /api/* with Authorization: Bearer <access_token>
        → backend validates JWT signature + expiry
        → extracts user_id from sub claim

On 401 → browser calls POST /auth/refresh automatically
        → backend validates httpOnly cookie refresh token
        ← new access_token
```

### 3.2 — Query Pipeline (SSE)
```
POST /datasets/{id}/query  { "prompt": "..." }
  └→ Returns text/event-stream

Events emitted:
  data: {"event": "start", "request_id": "..."}
  data: {"event": "schema_built", "token_count": 1204}
  data: {"event": "sql_generated", "sql": "SELECT...", "title": "..."}
  data: {"event": "sql_executed", "rows": 9, "chart_index": 0}
  data: {"event": "chart_ready", "chart": {...}, "kpis": [...]}
  data: {"event": "insight_ready", "insight": "...", "suggestions": [...]}
  data: {"event": "done", "total_latency_ms": 2341}
  
On error:
  data: {"event": "error", "stage": "sql_execute", "message": "No matching data..."}
```

### 3.3 — Dataset Storage Layout
```
/data/
  users/
    {user_id}/
      datasets/
        {dataset_id}/
          original.csv        ← Immutable original upload
          data.db             ← Read-only SQLite (WAL)
          data.db-wal         ← WAL journal
          data.db-shm         ← Shared memory file
```

### 3.4 — Multi-Provider LLM Ladder
```
call_llm(prompt)
  → try providers in order:
     1. Groq (Key 1, 2, 3)  — fastest, free tier
     2. Gemini (Key 1, 2, 3) — free tier backup
     3. Anthropic Claude     — if API key set (optional)
     4. OpenAI GPT-4o        — if API key set (paid fallback)
  → on 429: rotate key, retry with 0.5s backoff
  → on failure: try next provider
  → all failed: return cannot_answer with clear message
  → successful: cache in Redis (TTL 10min, key=SHA256(prompt+dataset_id))
```

---

## 4. Data Models (PostgreSQL)

```sql
-- Users
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),           -- null if Google-only auth
  google_id   VARCHAR(255) UNIQUE,
  display_name VARCHAR(255),
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  last_active TIMESTAMPTZ,
  is_active   BOOLEAN DEFAULT TRUE,
  settings    JSONB DEFAULT '{}'        -- user preferences JSON
);

-- Datasets
CREATE TABLE datasets (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255),
  row_count   INTEGER,
  col_count   INTEGER,
  size_bytes  BIGINT,
  db_path     TEXT NOT NULL,            -- absolute path to .db file
  schema_json JSONB,                    -- cached SchemaPayload
  pii_detected BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Dashboards (saved query results)
CREATE TABLE dashboards (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  dataset_id  UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  name        VARCHAR(255) NOT NULL,
  prompt      TEXT,
  result_json JSONB NOT NULL,           -- full pipeline result
  is_public   BOOLEAN DEFAULT FALSE,
  share_token VARCHAR(64) UNIQUE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Query history
CREATE TABLE query_history (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  dataset_id  UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  prompt      TEXT NOT NULL,
  result_json JSONB,                    -- full pipeline result (for restore)
  is_favorited BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Refresh tokens
CREATE TABLE refresh_tokens (
  jti         UUID PRIMARY KEY,
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at  TIMESTAMPTZ NOT NULL,
  revoked     BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. Environment Variables (Complete List)

```bash
# ── Application ────────────────────────────────────────────────────
ENV=development                         # development | production
SECRET_KEY=<random-256-bit-hex>         # JWT signing key
ALLOWED_ORIGINS=http://localhost:5173   # comma-separated

# ── Database ───────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/insightflow
REDIS_URL=redis://localhost:6379/0

# ── Storage ────────────────────────────────────────────────────────
DATA_DIR=/data                          # root path for user datasets
MAX_CSV_SIZE_MB=50
MAX_DATASETS_PER_USER=10

# ── LLM Providers ──────────────────────────────────────────────────
GROQ_API_KEY=gsk_...
GROQ_API_KEY_2=gsk_...                  # optional backup
GROQ_API_KEY_3=gsk_...                  # optional backup
GROQ_MODEL=llama-3.3-70b-versatile

GEMINI_API_KEY=AIza...
GEMINI_API_KEY_2=AIza...               # optional backup
GEMINI_MODEL=gemini-2.0-flash

ANTHROPIC_API_KEY=sk-ant-...           # optional third-tier
OPENAI_API_KEY=sk-...                  # optional fourth-tier

# ── Auth ───────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Observability ──────────────────────────────────────────────────
SENTRY_DSN=https://...                  # optional
LOG_LEVEL=INFO                          # DEBUG | INFO | WARNING | ERROR
```

---

## 6. Naming Conventions

### Python
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private functions: `_leading_underscore`
- Type hints: always required on all public functions
- Pydantic models for all request/response bodies (never bare `dict`)

### TypeScript/JavaScript
- Components: `PascalCase.jsx`
- CSS Modules: `ComponentName.module.css`
- Stores: `useXxxStore` (Zustand convention)
- API functions: `verb + Resource` e.g. `getDatasets`, `createDashboard`
- Constants: `UPPER_SNAKE_CASE`
- Hooks: [use](file:///c:/Users/Rupesh/Desktop/Pranav/GfG_Hackathon-InsightFlow/InsightFLow_v3/frontend/src/pages/Landing.jsx#5-25) prefix

### Database
- Table names: `snake_case`, plural (`users`, `datasets`, `query_history`)
- Column names: `snake_case`
- Foreign keys: `{table_singular}_id`
- Indexes: `idx_{table}_{column(s)}`

### API
- Endpoints: REST conventions (`/datasets`, `/datasets/{id}`, not `/getDataset`)
- HTTP verbs: `GET` = read, `POST` = create, `PUT` = full update, `PATCH` = partial, `DELETE` = remove
- Response envelope: `{ "data": ..., "meta": {...} }` for lists; flat object for single resources
- Errors: `{ "error": "human_readable_code", "message": "...", "details": {...} }`

---

## 7. Security Architecture

```
Internet
  │
  ▼
Nginx (TLS termination, HSTS, rate limit at edge)
  │
  ▼
FastAPI Backend
  ├── SecurityHeadersMiddleware   ← Injects CSP, X-Frame-Options, etc.
  ├── RequestIDMiddleware         ← Injects X-Request-ID for tracing
  ├── CORSMiddleware              ← Allowlist-only origins
  ├── RateLimitMiddleware         ← Redis-backed token bucket per user+endpoint
  │
  ├── /auth/*                     ← No auth required; IP-rate-limited
  ├── /share/{token}              ← No auth required; read-only
  │
  └── All other routes:
      └── JWTAuthDependency       ← Validates Bearer token
          └── ResourceOwnershipCheck ← user_id in JWT must own requested resource
              └── Business Logic
                  └── SQL Sandbox (read-only SQLite, sqlglot AST validation)
```
