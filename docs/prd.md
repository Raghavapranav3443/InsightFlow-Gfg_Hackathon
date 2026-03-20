# InsightFlow — Production PRD
**Version:** 2.0  
**Date:** March 2026  
**Status:** Draft — Pending Engineering Review

---

## 1. Executive Summary

InsightFlow is a **self-serve AI Business Intelligence platform** that converts plain-English questions into interactive dashboards. The v2.0 production upgrade focuses on four pillars:
1. **Enterprise security** — authentication, authorization, data isolation
2. **Reliability** — persistent storage, async processing, graceful degradation
3. **Scale** — multi-user, multi-dataset, multi-tenant ready architecture
4. **Product depth** — saved dashboards, collaboration, scheduled reports, richer UX

---

## 2. Problem Statement

Business analysts spend 60–80% of their time extracting data rather than analyzing it. SQL is a barrier. Traditional BI tools (Tableau, Power BI) require weeks of setup and specialists. AI-powered alternatives either hallucinate dangerously or lack the depth to handle real business questions.

InsightFlow v2 solves this by combining:
- Natural language as the interface
- SQL as the verified, transparent computation layer
- A deterministic post-processor that corrects AI mistakes
- An honest "cannot answer" gate that prevents fabrication

---

## 3. Target Users

### Primary: The Data-Curious Analyst
- Role: Business analyst, product manager, marketing ops
- Skills: Excel power user, no SQL
- Pain: Dependent on engineering for any data question
- Goal: Answer ad-hoc questions in minutes, not days

### Secondary: The Startup Founder
- Role: Early-stage founder wearing many hats
- Skills: Some technical background, no data eng bandwidth
- Pain: Can't afford a data team
- Goal: Self-serve reporting on their own CSV exports

### Tertiary: The Enterprise Team (v2.1+)
- Role: BI team at a mid-market company
- Skills: SQL-capable but wants speed
- Pain: Dashboard creation is slow; sharing is clunky
- Goal: Quick exploratory analysis, shareable dashboards

---

## 4. Goals & Non-Goals

### Goals (v2.0)
- [G1] Zero-friction onboarding: sign up → first insight in < 60 seconds
- [G2] Full auth with Google OAuth and email/password
- [G3] Persistent sessions, datasets, and dashboard history
- [G4] Async LLM processing with real-time progress via Server-Sent Events (SSE)
- [G5] PII detection warning before data leaves the system
- [G6] Multi-dataset workspaces per user
- [G7] Saved and shareable dashboards
- [G8] Production security: SQL sandboxing, prompt injection defense, proper CORS
- [G9] Full observability: structured logging, error tracking, performance monitoring
- [G10] Mobile-responsive design

### Non-Goals (v2.0)
- Direct database connectors (PostgreSQL, MySQL) — v2.1
- Multi-user collaboration on same dashboard (real-time) — v2.2
- White-label / multi-tenant SaaS — v2.2
- Custom LLM fine-tuning — future
- Native mobile apps — future

---

## 5. Functional Requirements

### FR-01: Authentication & Authorization
| ID | Requirement |
|---|---|
| FR-01-1 | Users must register/login before accessing any feature |
| FR-01-2 | Support Google OAuth 2.0 as primary SSO method |
| FR-01-3 | Support email + password with bcrypt hashing |
| FR-01-4 | JWT access tokens (15min TTL) + refresh tokens (7 days, httpOnly cookie) |
| FR-01-5 | All API endpoints require a valid JWT; unauthenticated requests return 401 |
| FR-01-6 | Session IDs are server-generated UUIDs tied to verified user identity |
| FR-01-7 | Users can only access their own datasets, dashboards, and history |

### FR-02: Dataset Management
| ID | Requirement |
|---|---|
| FR-02-1 | Users can upload CSV files (max 50MB, configurable) |
| FR-02-2 | Users can have up to 10 datasets per account (configurable limit) |
| FR-02-3 | Datasets are named and can be renamed/deleted |
| FR-02-4 | Each dataset shows: name, row count, column count, upload date, size |
| FR-02-5 | PII scanner runs on upload and warns user if patterns detected (email, phone, SSN, CC) |
| FR-02-6 | Dataset preview (first 100 rows) available in a data table view |
| FR-02-7 | Dataset deletion permanently removes the SQLite file and all associated dashboards |
| FR-02-8 | Support UTF-8, Latin-1, and CP1252 encodings with auto-detection |

### FR-03: Query & Dashboard Engine
| ID | Requirement |
|---|---|
| FR-03-1 | Natural language query submitted → dashboard rendered with charts + KPIs + AI insight |
| FR-03-2 | Query processing uses SSE to stream progress (schema → SQL → execute → viz → insight) |
| FR-03-3 | Each query returns: 1–3 charts, 2–4 KPI cards, AI insight, brief insights (3–5 bullets), 3 follow-up suggestions |
| FR-03-4 | SQL is always displayed in a collapsible panel (transparency) |
| FR-03-5 | Chart type is deterministically selected from actual result shape (not LLM-guessed) |
| FR-03-6 | Post-processor applies 9 correction rules before rendering |
| FR-03-7 | Honest refusal: if question cannot be answered, explain why clearly in plain English |
| FR-03-8 | Query refinement: user can follow up on current result without starting fresh |
| FR-03-9 | Clarification flow: if query is ambiguous, app asks a disambiguating question |
| FR-03-10 | All chart types: bar, grouped bar, line (with forecast), pie (with tail merge), scatter (with Pearson r), area, heatmap |

### FR-04: Dashboard Management
| ID | Requirement |
|---|---|
| FR-04-1 | Users can save a dashboard result with a name |
| FR-04-2 | Saved dashboards are listed in a "My Dashboards" view |
| FR-04-3 | Dashboards can be duplicated, renamed, and deleted |
| FR-04-4 | Dashboards can be shared via a public read-only URL (opt-in) |
| FR-04-5 | Shared URL dashboards require no login to view (but are read-only) |
| FR-04-6 | Dashboard export: PDF (structured layout, not screenshot) and per-chart PNG |
| FR-04-7 | Dashboard can be regenerated (re-run all queries) on demand |

### FR-05: Chat Assistant
| ID | Requirement |
|---|---|
| FR-05-1 | Chat assistant is context-aware of the currently displayed dashboard |
| FR-05-2 | Chat can generate new queries and update the dashboard inline |
| FR-05-3 | Chat maintains conversation history within a session |
| FR-05-4 | Chat can answer general questions about the dataset |
| FR-05-5 | Chat clearly distinguishes between "asking about data" and "generating a new query" |

### FR-06: Query History
| ID | Requirement |
|---|---|
| FR-06-1 | Full query history persisted per user per dataset |
| FR-06-2 | Clicking a history entry restores the full dashboard (charts, KPIs, insights) |
| FR-06-3 | History entries can be favorited / starred |
| FR-06-4 | History is searchable by keyword |
| FR-06-5 | History can be cleared (with confirmation) |

### FR-07: Auto-Report
| ID | Requirement |
|---|---|
| FR-07-1 | Auto-report analyzes the dataset schema and generates 4–6 contextually appropriate queries |
| FR-07-2 | Queries are dynamically generated based on actual column names and roles (not hardcoded) |
| FR-07-3 | Report sections: Overview KPIs, Distribution analysis, Correlation analysis, Key Segments |
| FR-07-4 | Auto-report can be saved as a dashboard |

### FR-08: Security (Application Layer)
| ID | Requirement |
|---|---|
| FR-08-1 | All SQL executed against per-user read-only SQLite databases |
| FR-08-2 | SQL validated with: allowlist (SELECT only), blocklist, table-name verification, parameterized internal queries |
| FR-08-3 | Prompt injection defense: user input is clearly delineated from system instructions via XML/JSON delimiters |
| FR-08-4 | LLM output is parsed as JSON only; any non-JSON response is treated as failure (not eval'd) |
| FR-08-5 | All LLM calls use `response_format: json_object` and are sandboxed |
| FR-08-6 | Session ID validated server-side as UUIDv4, ownership verified against JWT claims |
| FR-08-7 | No user data (row values) sent to external LLMs without explicit opt-in consent during onboarding |
| FR-08-8 | Rate limiting via Redis-backed token bucket (not in-memory) |
| FR-08-9 | HTTPS enforced; HSTS header set; auth tokens in httpOnly cookies |

---

## 6. Non-Functional Requirements

### Performance
| NFR | Target |
|---|---|
| End-to-end query latency (p50) | < 3 seconds |
| End-to-end query latency (p95) | < 8 seconds |
| CSV ingestion (10MB file) | < 5 seconds |
| Dashboard load (saved) | < 500ms |
| API uptime | 99.9% (monthly) |

### Scalability
| NFR | Target |
|---|---|
| Concurrent users per instance | 100 |
| Max datasets per user | 10 (configurable) |
| Max CSV size | 50MB (configurable) |
| Max rows per dataset | 5,000,000 |
| Max query result rows returned for visualization | 10,000 |

### Security
- OWASP Top 10 compliance
- SOC 2 Type II readiness (audit log, access controls)
- GDPR: data deletion on request, no PII to external LLMs without consent
- All secrets in environment variables, never in code

### Observability
- Structured JSON logging to stdout (Logtail/Datadog compatible)
- Sentry error tracking with user context
- Request tracing with correlation ID
- Business metrics: queries per day, datasets uploaded, sessions, error rates

---

## 7. Feature Flags & Rollout Strategy

| Feature | Flag | Default | Notes |
|---|---|---|---|
| PII scanner warning | `pii_scan_enabled` | ON | Can be disabled per-tenant |
| LLM consent gate | `llm_consent_required` | ON | Must be OFF for demo mode |
| SSE streaming | `streaming_enabled` | ON | Fallback to polling if client doesn't support |
| Public dashboard sharing | `sharing_enabled` | ON | Can be disabled for enterprise |
| Auto-report | `auto_report_enabled` | ON | |
| Line forecasting | `forecast_enabled` | ON | Experimental; disable if noisy |

---

## 8. API Contract Summary

All API endpoints require `Authorization: Bearer <jwt>` header (except auth endpoints).

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Email + password registration |
| POST | `/auth/login` | Email + password login → JWT |
| GET | `/auth/google` | Google OAuth redirect |
| POST | `/auth/refresh` | Refresh JWT via httpOnly cookie |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/me` | Current user profile |
| GET | `/datasets` | List user's datasets |
| POST | `/datasets` | Upload new CSV dataset |
| GET | `/datasets/{id}` | Dataset metadata + schema |
| DELETE | `/datasets/{id}` | Delete dataset + all associated data |
| GET | `/datasets/{id}/preview` | First 100 rows |
| POST | `/datasets/{id}/query` | Run NL query → SSE stream |
| POST | `/datasets/{id}/refine` | Refine last query |
| GET | `/datasets/{id}/history` | Query history |
| DELETE | `/datasets/{id}/history` | Clear history |
| POST | `/datasets/{id}/auto-report` | Generate auto report |
| GET | `/dashboards` | List saved dashboards |
| POST | `/dashboards` | Save current state as dashboard |
| GET | `/dashboards/{id}` | Load saved dashboard |
| PUT | `/dashboards/{id}` | Update dashboard (rename) |
| DELETE | `/dashboards/{id}` | Delete dashboard |
| POST | `/dashboards/{id}/share` | Enable public sharing → returns URL token |
| GET | `/share/{token}` | Load shared dashboard (no auth) |
| POST | `/chat` | Chat message (dataset-aware) |
| GET | `/health` | Server health (no auth, no sensitive data) |

---

## 9. Success Metrics

### Acquisition
- Time-to-first-insight < 60 seconds from sign-up
- Landing page → sign-up conversion > 20%

### Engagement
- Queries per active user per session > 5
- Dashboard save rate > 30% of sessions
- D7 retention > 40%

### Reliability
- P95 query latency < 8s
- Error rate (5xx) < 0.5%
- LLM `cannot_answer` rate < 15% (ideally signals good question quality)

### Business (if monetized)
- Freemium → paid conversion > 5%
- Net Promoter Score > 45

---

## 10. Out-of-Scope (Explicit Deferrals)

- Direct SQL editor / manual SQL entry
- Real-time collaborative editing
- Data connectors (Postgres, BigQuery, Snowflake)
- Custom model hosting / fine-tuning
- Mobile native apps
- Embedded analytics (iframe embed in third-party apps)
- Role-based access control within a team (all v2.2+)
