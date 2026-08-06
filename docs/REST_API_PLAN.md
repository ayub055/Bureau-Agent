# Bureau Analyser → REST API — Reference & Implementation Plan

> **Purpose of this document.** A standing reference to help you *understand* how
> we would turn the Bureau Analyser into a callable REST API, and a saved plan you
> can later hand back to me with "implement this." Read §1–§6 to understand the
> shape and architecture, skim §7–§16 for the mechanics, use §17 as a reusable
> production-readiness checklist, and §18 to record your requirements.
>
> **Status:** design only. No implementation code has been written.

---

## Table of contents
1. Executive summary
2. Glossary
3. Where we are today (the current CLI system)
4. What we're building (goals, outputs, decisions)
5. The mental model (a request in plain English)
6. **Architecture — separation of concerns, ports & reliability tiers**
7. Component design — the data-file injection (the crux)
8. Component design — deterministic build & the JSON response
9. Component design — the async HTML → DMP → webhook path
10. Failure & error handling (the full matrix)
11. Security, PII & egress/SSRF control
12. Configuration reference
13. The API contract (request / response / webhook schemas)
14. Observability, concurrency & execution model
15. Dependencies & packaging
16. File-by-file change list
17. **Production API decisioning framework (generalizable checklist)**
18. Open questions for you
19. Verification plan
20. Deferred / future work

---

## 1. Executive summary

The Bureau Analyser today runs only from the command line. We want other systems
to obtain a bureau/CIBIL analysis over HTTP. The API does **two** things per
request:

1. **Return the full analysis as JSON, synchronously** — the primary, fast (<1s),
   deterministic deliverable an upstream decisioning system consumes.
2. **Render the human-readable HTML report and push it to DMP** asynchronously,
   notifying the caller with a **webhook** when it finishes (or fails).

The caller passes a **path/reference to a bureau data file (a DMP dump)** + a CRN;
we load that CRN's rows from that file. Excel is not part of the API.

The numeric engine is **reused as-is** (principle: *determinism > intelligence*);
the API adds transport, validation, auditability, and delivery. Two structural
ideas carry the design: a **single injection point** for the per-request data file
(§7), and **light architectural seams** (ports at four boundaries) that keep the
engine intact while making the swappable/failure-prone parts testable (§6).

---

## 2. Glossary

| Term | Meaning in this project |
|------|--------------------------|
| **CRN** | Customer Reference Number — identifies a customer across the data files. |
| **DMP** | Data Management Platform — source of the bureau data dump the caller references, and the destination we upload the finished HTML report to (over a REST endpoint). |
| **Tradeline** | One credit account on a bureau record; the DPD file has one row per tradeline. |
| **DPD** | Days Past Due — delinquency measure. |
| **Bureau income / Sustained EMI / Obligation** | Three deterministic calcs, each SQL run through DuckDB, feeding the report. |
| **FOIR** | Fixed-Obligation-to-Income Ratio; key affordability metric. |
| **Narration** | The optional LLM prose summary (local Ollama `llama3.2`); never produces numbers; fail-soft. |
| **Fail-soft** | On a sub-step failure, log + continue with a partial result rather than crash. |
| **Port / Adapter** | A port is an interface (a seam); an adapter is a concrete implementation of it. Lets us swap/stub the failure-prone edges. |
| **`contextvars`** | Per-request scoped values isolated across concurrent requests — how we pin "which data file for *this* request." |
| **Webhook** | An HTTP callback we POST to a caller-supplied URL to report async completion/failure. |
| **Idempotency key** | Caller id that lets a retried request be recognised as the same, so we don't duplicate artifacts. |
| **Tier-1 / Tier-2** | Tier-1 = the synchronous deterministic JSON path (must-not-fail). Tier-2 = the async artifact/delivery path (best-effort, retried). |

---

## 3. Where we are today (the current CLI system)

- **Entry point:** `run_bureau.py <crn>` → `generate_combined_report_pdf(crn, theme)`
  (`tools/combined_report.py`): ensures data, builds the report, narrates, renders
  HTML, writes a one-row Excel to `reports/`.
- **Deterministic build:** `build_bureau_report(crn)`
  (`pipeline/reports/bureau_report_builder.py`) → `BureauReport` dataclass
  (`schemas/bureau_report.py`): feature vectors, executive inputs, tradeline
  features, key findings, monthly exposure, and the three DuckDB results. Missing
  pieces are `None` (fail-soft); a missing CRN yields an **empty** report, not an error.
- **Data loading:** everything funnels through
  `pipeline/extractors/bureau_feature_extractor.py::_load_bureau_data` (and
  `tradeline_feature_extractor.py::_load_tl_features`), reading files named in
  `config/settings.py`, cached in an **unkeyed module global**. The three DuckDB
  tools reuse `_load_bureau_data()`.
- **Rendering:** `render_combined_report_html(report, theme) -> str` returns HTML
  as a **string** (the file-writing `render_combined_report` wraps it). Default theme `v3`.
- **LLM:** `generate_bureau_review(...)` calls local Ollama; try/except; `None` on failure.
- **No web framework** anywhere (incl. `_archive/`); no `requirements.txt`; runs on
  `/Users/ayyoob/anaconda3/bin/python`.

Everything the API needs already exists as callable functions returning structured
data. Our job is transport + delivery + safety.

---

## 4. What we're building

### Outputs (exactly two)
1. **JSON report** — synchronous HTTP response.
2. **HTML report** — async, uploaded to **DMP**; caller notified by **webhook**.

Excel is out of scope for the API (CLI/batch only).

### Decisions locked in
| Decision | Choice | Why |
|----------|--------|-----|
| Sync response | JSON report only | Fast, machine-consumable deliverable |
| HTML | Async → DMP (REST upload) | Heavy artifact belongs in DMP |
| Async completion signal | Webhook to caller URL | Caller learns done/failed without polling |
| Data source | Caller passes a **file path** + CRN | Tiny requests; self-contained calls |
| LLM narration | Optional (`narrate=true`); separated `ai` block in the response, beta-fenced | Keeps the deterministic contract clean; determinism isolated from AI |
| Framework | FastAPI | Pydantic validation + auto OpenAPI docs |
| **Concern separation** | **Light seams — ports at DataLoader / Narrator / DmpClient / WebhookSender**; engine otherwise unchanged | Testability + swappability at the risky edges without a big refactor |
| **Async delivery** | **Full resilient async** — job + retries/backoff + signed webhook + status store + dead-letter + reconciliation | It's the least-deterministic, most-moving part; build it properly |
| UI | None | Out of scope |

### Non-goals (v1)
- Full ports-and-adapters refactor (light seams now; §20).
- Durable external queue (in-process background tasks for v1).
- Inline raw tradeline data in the body (we take a *path*).
- Full OAuth/OIDC (v1: API key + signed webhooks).

---

## 5. The mental model (a request in plain English)

1. Caller sends `POST /v1/summary/consumer-cibil` with the **CRN**, the **path to
   the DMP data file**, optional theme, optional `narrate`, and a **callback URL**;
   authenticates with an API key.
2. We **validate** everything up front: API key, path-safety of `data_file`,
   required columns present, and `callback_url` well-formed **and egress-allowed** (§11).
3. We **pin the data file for this request** (`contextvars`) and call
   `build_bureau_report(crn)`; the loaders consult the pin, so the whole
   deterministic pipeline reads the caller's file.
4. No rows → **404**. Otherwise compute derived views (scorecard/checklist/persona),
   attach an **audit stamp** + **`module_status`**, and **return the JSON report** —
   fast, and with **no hard dependency on DMP or Ollama** (both are Tier-2).
5. In the **background** (Tier-2) we optionally narrate, render the **HTML string**,
   **upload to DMP**, and **POST a signed webhook** with the result. Nothing
   customer-identifying is written to our local disk.

Two phases, two contracts: **sync speaks HTTP status codes; async speaks webhooks.**

---

## 6. Architecture — separation of concerns, ports & reliability tiers

**Chosen stance: light seams.** Keep the engine essentially as-is; introduce
interfaces only at the boundaries that are swappable or failure-prone. A full
domain/adapters refactor is deferred (§20). This buys most of the testability and
resilience benefit for a fraction of the change.

### 6.1 Layer separation — what belongs where (and what must *not* leak)
| Layer | Holds | Must NOT hold |
|-------|-------|---------------|
| **Transport** (`api/`) | HTTP concerns: auth, request validation, serialization, error-mapping, request-id, rate-limit, idempotency | any business/number logic |
| **Domain engine** (existing `pipeline/`, `tools/`) | deterministic computation; framework-agnostic; callable from API, CLI, batch, tests | HTTP, DMP, webhook, or FastAPI imports |
| **Delivery** (async) | render → DMP upload → webhook; retries/status | decisioning logic |

The engine never imports FastAPI; the transport layer never computes a number.
This keeps the CLI, batch, and API all driving the *same* engine.

### 6.2 The four ports (the only new seams)
| Port (interface) | Responsibility | v1 adapter | Why it's a seam |
|------------------|----------------|-----------|-----------------|
| `DataLoader` | fetch a CRN's rows from a source | file loader w/ contextvar + `(path,mtime,size)` cache (§7) | swap to DB / DMP-pull API later without touching compute |
| `Narrator` | produce narrative from a report | Ollama via `generate_bureau_review` | swap LLM/provider; **stub in tests**; disable ⇒ deterministic-only |
| `DmpClient` | upload an artifact, return a ref | httpx multipart (§9) | swap to object-store / signed-URL |
| `WebhookSender` | deliver a signed callback | httpx POST + HMAC + retries (§9) | swap to queue / event-bus |

Everything else stays a direct function call. These four are exactly the parts
that (a) do I/O to the outside world or (b) are non-deterministic — the places you
most want to mock in tests and replace in prod.

### 6.3 Pipeline stages kept separable (even inside one endpoint)
Internally the flow stays five typed, individually-testable functions —
**parse → compute → narrate → render → deliver** — even though v1 exposes one
endpoint. Benefits: per-stage unit tests; response caching at the `compute`
boundary (§17); and a **cheap future split** into distinct endpoints
(`/v1/parse/…`, `/v1beta/ai-summary/…`) if a caller ever needs them.

### 6.4 Two reliability tiers (design and monitor them separately)
- **Tier-1 — synchronous deterministic JSON.** Must-not-fail; tight latency SLO;
  **zero hard dependency on DMP or Ollama.** If DMP *and* Ollama are both down, the
  JSON response still returns `200`. This is the contract a credit decision rests on.
- **Tier-2 — async artifact + delivery.** Best-effort; retried; dead-lettered;
  reconciled; its own (looser) SLO and its own alerts. A Tier-2 outage must never
  degrade Tier-1.

### 6.5 Bulkhead the LLM
Narration runs in its **own bounded pool + semaphore + hard timeout** so a slow or
stuck Ollama can never consume the workers serving Tier-1. The `ai` block simply
comes back absent + a warning.

### 6.6 Read-model vs artifact
The JSON (machine, Tier-1) and the HTML (human, Tier-2) are **two products with
independent SLAs** — not two renderings of one call that must both succeed.

---

## 7. Component design — the data-file injection (the crux)

**Problem.** The loaders cache one file in an unkeyed global; a server handling
different DMP files per request can't use that, and re-reading the same path is
unsafe if the file was overwritten.

**Solution — `contextvars` + a change-aware cache** (the `DataLoader` port's adapter):
- New `api/data_context.py` holds `current_dpd_file` / `current_tl_features_file`
  `ContextVar`s, set at request start and **captured into the background task**.
- Edit `_load_bureau_data` (mirror `_load_tl_features`) to:
  1. `path = current_dpd_file.get() or settings.BUREAU_DPD_FILE` (CLI unchanged).
  2. **Cache keyed by `(path, mtime, size)`** — not path alone *(else a refreshed
     file at the same path serves stale rows: a correctness bug for credit)*.
  3. **Per-path lock** around population (no double-parse on concurrent first-hit).
  4. Keep `force_reload`.

Every downstream calc (`extract_bureau_features`, the three DuckDB tools) reads
through `_load_bureau_data()`, so the per-request file propagates for free. The API
composes the pipeline itself and **skips `ensure_data()`** (`AUTO_GENERATE=False`).

---

## 8. Component design — deterministic build & the JSON response

Reuses unchanged: `build_bureau_report(crn)`, `compute_scorecard`,
`compute_checklist`, `compute_probable_persona`. Adds three API-only things:

- **(a) Not-found detection** — turn an empty report (0 tradelines) into a **404**.
- **(b) Audit stamp** (`api/audit.py`): `engine_version` (git SHA),
  `ruleset_version` (hash of `config/thresholds.py`), `data_fingerprint` (SHA-256
  of the CRN's rows) + `row_count`, `generated_at`, `request_id`. Makes a decision
  reproducible/defensible.
- **(c) `module_status` + `warnings`** — derived from each fail-soft sub-result, so
  a partial report can't masquerade as complete.

**Response shape (separation applied):** a stable, deterministic `summary` block
and a nullable, beta-fenced `ai` block. Flipping `narrate` changes *only* `ai`;
no deterministic number moves. Serialisation via `api/serialization.py::to_jsonable`
(handles the `LoanType` enum keys, nested dataclasses, dates, numpy/Decimal).

---

## 9. Component design — the async HTML → DMP → webhook path (Tier-2)

After the JSON is returned, a **FastAPI `BackgroundTask`** (`api/async_job.py`):
1. **(optional) Narrates** via the `Narrator` port under bulkhead + timeout;
   fail-soft (no narrative + warning).
2. **Renders** `render_combined_report_html(report, theme)` → HTML **string** (no
   disk).
3. **Uploads to DMP** via the `DmpClient` port: multipart to `DMP_ARTIFACTS_URL`
   with `DMP_API_TOKEN`; **bounded retries w/ backoff + jitter** for 5xx/timeout;
   4xx non-retryable; optional circuit-breaker.
4. **Notifies** via the `WebhookSender` port: **HMAC-signed** callback to
   `callback_url` (`done` + `dmp_uri`, or `failed` + stage/error); retries.
5. **Records status** in `api/status_store.py` (PII-free `request_id → {state,
   stage, attempts, dmp_uri?, error?}`) for `GET /status`, idempotency, and
   crash reconciliation.

---

## 10. Failure & error handling (the full matrix)

### 10a. Synchronous phase → HTTP status codes
| Situation | Status |
|-----------|--------|
| Missing/invalid `X-API-Key` | 401 |
| `data_file` escapes `BUREAU_DATA_BASE_DIR` (traversal) | 403 |
| `data_file` missing/unreadable | 400 |
| Missing columns / invalid `theme` / bad or **egress-blocked** `callback_url` | 422 |
| CRN has 0 tradelines | 404 |
| Duplicate `idempotency_key` in-flight/done | 409 (returns original) |
| Unexpected build exception | 500 (+ `request_id`; trace logged) |
| Config invalid / not ready | 503 |

Fail-fast column validation at the boundary (`api/validation.py`) defends the
documented trailing-tab / index-shift data trap.

### 10b. Asynchronous phase → webhook + retries (HTTP already 200)
| Failure | Handling |
|---------|----------|
| Narration times out/errors | Fail-soft: HTML without narrative; webhook `narrated:false` + warning |
| HTML render fails | Webhook `failed(stage:render, retryable:false)`; no upload |
| DMP upload transient (5xx/timeout) | Retries+backoff; exhaustion → `failed(stage:dmp_upload, retryable:true)` + dead-letter |
| DMP upload 4xx (auth/bad) | Non-retryable → `failed` + operator alert |
| Webhook delivery fails | Retries; exhaustion → `log.error` + alert + status `webhook_failed` for reconciliation |
| Job timeout / worker crash | Status store lets a reconciler mark stuck `pending` → `failed`, fire webhook, alert |

### 10c. Cross-cutting
Idempotency (dedup by key; reuse artifact), per-call + overall timeouts, HMAC
webhook signing (at-least-once ⇒ caller idempotent), never a silent partial success.

---

## 11. Security, PII & egress/SSRF control

- **Inbound auth:** `X-API-Key` on every route (→ gateway/mTLS later).
- **Data path safety** (`api/security.py`): `realpath(base_dir / data_file)` must
  stay inside `realpath(base_dir)`; reject absolute paths and `..`.
- **⚠️ Egress / SSRF control on `callback_url` (sharp):** the caller supplies a URL
  we POST to — a classic SSRF vector (they could aim it at internal services /
  metadata endpoints). Enforce an **egress allowlist**: require `https`, resolve
  the host and **deny private/link-local/loopback ranges**, optional host allowlist,
  and cap redirects. Same posture for `DMP_ARTIFACTS_URL` (configured, not caller-supplied).
- **Outbound auth to DMP:** `DMP_API_TOKEN`, least-privilege (upload-only).
- **Webhook authenticity:** HMAC-SHA256 `X-Signature`.
- **No PII at rest:** HTML is an in-memory string streamed to DMP; JSON is returned,
  not stored; only PII-free status records persist.
- **PII-safe logging:** log ids/timings/status/`module_status` — never report body,
  narrative, or raw tradelines.

---

## 12. Configuration reference

Wrap `config/settings.py` constants in `os.getenv(...)` (CLI unchanged) + a pydantic
`Settings` object **validated at startup** (fail-fast). Group by concern:

| Group | Env vars |
|-------|----------|
| **Data** | `BUREAU_DATA_BASE_DIR`, `BUREAU_DPD_FILE`, `TL_FEATURES_FILE`, `AUTO_GENERATE=False` |
| **LLM** | `OLLAMA_BASE_URL`, `SUMMARY_MODEL`, `LLM_TIMEOUT_S`, `MAX_CONCURRENT_NARRATE` |
| **DMP** | `DMP_ARTIFACTS_URL`, `DMP_API_TOKEN`, `DMP_UPLOAD_TIMEOUT_S`, `DMP_UPLOAD_RETRIES` |
| **Webhook** | `WEBHOOK_SIGNING_SECRET`, `WEBHOOK_TIMEOUT_S`, `WEBHOOK_RETRIES`, `WEBHOOK_EGRESS_ALLOWLIST` |
| **Security** | `API_KEYS` (required to boot) |
| **Ops** | `ARTIFACT_JOB_TIMEOUT_S`, `STATUS_STORE_URL` (see §14 multi-worker) |

Pass `base_url=OLLAMA_BASE_URL` to `ChatOllama(...)` in `report_summary_chain.py`.

---

## 13. The API contract

Base path `/v1`; Swagger at `/docs`; all routes require `X-API-Key`; every response
echoes `X-Request-ID`.

### `POST /v1/summary/consumer-cibil` — generate (JSON sync; HTML async)
```jsonc
// request
{ "crn": 698167220,
  "data_file": "2026-08/BU_TL_batch.csv",       // REQUIRED — path relative to BUREAU_DATA_BASE_DIR
  "tl_features_file": "2026-08/BU_Feats.csv",   // optional
  "theme": "v3",                                // optional — v2|v3|original|emerald
  "narrate": false,                             // optional — opt-in LLM (async, feeds HTML + ai block)
  "callback_url": "https://caller/hooks/bureau",// REQUIRED — egress-allowlisted webhook target
  "idempotency_key": "abc-123" }                // optional
```
```jsonc
// 200 — deterministic summary + separated (nullable, beta) ai block
{ "request_id":"b3f1…", "crn":698167220, "status":"ok", "generated_at":"…",
  "audit": { "engine_version":"…","ruleset_version":"…","data_fingerprint":"…","row_count":23 },
  "module_status": { "bureau_income":"ok","sustained_emi":"ok","obligation":"ok","narrative":"pending" },
  "warnings": [],
  "summary": {                       // DETERMINISTIC — identical whether or not the LLM ran
    "verdict":"LOW RISK",
    "kpis": { "tu_score":786,"foir":41.2,"bureau_income":125000,"aff_emi":51000,"max_dpd":0 },
    "scorecard":{…}, "checklist":[…], "persona":{…}, "key_findings":[…],
    "bureau_report":{…} },
  "ai": null,                        // { "beta":true, "narrative":"…", "recommendation":"…" } when narrate=true
  "artifact": { "type":"html", "status":"pending", "delivery":"webhook",
                "intended_dmp_ref":"dmp://artifacts/b3f1…/report.html" } }
```

### Webhook (server → `callback_url`, header `X-Signature: sha256=…`)
```jsonc
// success                                    // failure
{ "request_id":"…","status":"done",           { "request_id":"…","status":"failed",
  "narrated":false,                             "stage":"dmp_upload","error_code":"DMP_5XX",
  "artifact":{"dmp_uri":"…"} }                  "retryable":true }
```

### `GET /v1/summary/{request_id}/status` (optional; observability)
`{ state:"pending|done|failed|webhook_failed", stage, attempts, dmp_uri?, error? }`

### `GET /health` — liveness vs readiness (data dir; DMP reachability advisory)

*(No `GET` for HTML/Excel of a CRN: JSON is the response, HTML lives at DMP.)*

---

## 14. Observability, concurrency & execution model

- **Execution:** Tier-1 sync path <1s. Tier-2 runs as a FastAPI `BackgroundTask`
  in-process for v1; the PII-free status store bridges crash-safety; durable queue
  is the scale upgrade (§20).
- **Caching:** `(path, mtime, size)` loader cache + per-path lock (§7). See §17 for
  optional **response caching keyed by `(crn, data_fingerprint)`**.
- **Isolation:** DuckDB fresh connection per call; `contextvars` per request +
  captured into the task; **LLM bulkhead** pool (§6.5).
- **⚠️ Multi-worker caveat (sharp):** the in-process status store & idempotency
  map are **per-worker** — under `uvicorn --workers N` they don't share. For >1
  worker use a **shared status store** (`STATUS_STORE_URL`: sqlite-on-shared-disk
  or redis) or idempotency/reconciliation break across workers.
- **Observability:** structured JSON logs w/ `X-Request-ID`; **RED metrics per
  tier**; **distributed tracing (OpenTelemetry)** linking the sync request to its
  async job via `request_id`; counters for `crn_not_found`, `validation_failed`,
  `ollama_failed`, `dmp_upload_failed`, `webhook_failed`; alert on Tier-1 SLO
  breach and Tier-2 dead-letters.

---

## 15. Dependencies & packaging

Add **`requirements-api.txt`**: `fastapi`, `uvicorn[standard]`, `pydantic>=2`,
`pydantic-settings`, `httpx` (DMP + webhook), plus pinned existing deps (`pandas`,
`duckdb`, `langchain-core`, `langchain-ollama`, `jinja2`, `pyyaml`, `numpy`).
Optional: `opentelemetry-*` (tracing), `redis` (shared status store if multi-worker).
Install: `/Users/ayyoob/anaconda3/bin/pip install fastapi "uvicorn[standard]" pydantic-settings httpx`.

---

## 16. File-by-file change list

### New files (`api/` package)
| File | Responsibility |
|------|----------------|
| `api/main.py` | FastAPI app, routes, auth dep, exception handlers → error envelope, logging/trace middleware, `/health` |
| `api/settings.py` | pydantic `Settings` (grouped by concern), validated at startup |
| `api/schemas.py` | `ReportRequest` / `SummaryView` / `AiBlock` / webhook models |
| `api/service.py` | Tier-1 orchestration; audit + module_status; schedule Tier-2 |
| `api/async_job.py` | Tier-2 background job: narrate → render → upload → webhook; retries |
| `api/ports.py` | the four **Port** interfaces: `DataLoader`, `Narrator`, `DmpClient`, `WebhookSender` |
| `api/dmp_client.py` | `DmpClient` adapter (httpx multipart, retries) |
| `api/webhook.py` | `WebhookSender` adapter (HMAC, retries, dead-letter) |
| `api/data_context.py` | per-request DMP-data-path `ContextVar`s (backs `DataLoader`) |
| `api/serialization.py` | `to_jsonable(BureauReport)` |
| `api/security.py` | path-allowlist + **egress/SSRF allowlist** |
| `api/validation.py` | DMP required-column check → 422 |
| `api/audit.py` | engine/ruleset version + data-fingerprint |
| `api/status_store.py` | job state (in-proc v1 / shared via `STATUS_STORE_URL`); idempotency + reconciliation |
| `requirements-api.txt`, `tests/test_api_*.py` | deps; determinism + failure-path tests |

### Minimal edits to existing files (the "light seams")
| File | Edit |
|------|------|
| `config/settings.py` | env-var overrides + new grouped vars |
| `pipeline/extractors/bureau_feature_extractor.py` | `_load_bureau_data`: contextvar path; `(path,mtime,size)` cache; per-path lock |
| `pipeline/extractors/tradeline_feature_extractor.py` | `_load_tl_features`: same |
| `pipeline/reports/report_summary_chain.py` | `ChatOllama(base_url=OLLAMA_BASE_URL, …)` (also the `Narrator` adapter seam) |

**Reused unchanged:** `build_bureau_report`, `render_combined_report_html`,
`generate_bureau_review`, `compute_scorecard`/`compute_checklist`/`compute_probable_persona`,
all three DuckDB tools. **Not used by the API:** `render_combined_report` (file
writer), `build_excel_row`/`export_row_to_excel`.

---

## 17. Production API decisioning framework (generalizable checklist)

> A reusable "is this API production-grade?" checklist you can apply to *any* of
> these projects. Each row: the decision to make, this project's v1 stance, and
> what's deferred. ✅ = in v1; ⏳ = later.

| # | Concern | Decision to make | This project (v1) | Later ⏳ |
|---|---------|------------------|-------------------|---------|
| 1 | **Contract & versioning** | URI vs header versioning; how to evolve; deprecation policy | ✅ URI `/v1`, AI beta-fenced in-response; code-first OpenAPI published at `/docs` | ⏳ formal deprecation policy; split `/v1beta/ai-summary` |
| 2 | **Interface granularity** | one endpoint vs staged endpoints | ✅ one endpoint, `summary`/`ai` blocks separated; stages kept separable internally (§6.3) | ⏳ split parse/compute/ai endpoints if a caller needs them |
| 3 | **AuthN / AuthZ** | key vs OAuth vs mTLS; scopes | ✅ `X-API-Key` | ⏳ gateway/OAuth/mTLS; per-key scopes |
| 4 | **Egress / SSRF** | is any outbound URL caller-controlled? | ✅ `callback_url` egress allowlist; deny private ranges (§11) | ⏳ signed egress proxy |
| 5 | **Request governance** | idempotency, rate limits, payload caps, field selection | ✅ idempotency keys; input validation; `?view=summary\|full` | ⏳ per-key rate limits/quotas |
| 6 | **Reliability tiers** | which paths must-not-fail; dependency isolation | ✅ Tier-1 (no hard DMP/Ollama dep) vs Tier-2; LLM bulkhead (§6.4–6.5) | ⏳ per-tier SLOs formalised |
| 7 | **Resilience patterns** | timeouts, retries, circuit breaker, dead-letter, backpressure | ✅ per-stage timeouts; backoff+jitter retries; dead-letter; semaphores | ⏳ circuit breaker on DMP; bulkhead pools tuned |
| 8 | **Reproducibility & caching** | can a result be reproduced/cached? | ✅ audit stamp (engine/ruleset/fingerprint) | ⏳ response cache keyed by `(crn, data_fingerprint)` |
| 9 | **Determinism guardrails** | how to prevent silent numeric drift | ✅ golden/determinism tests vs expected CSVs (§19) | ⏳ drift-detection in CI on ruleset change |
| 10 | **Error taxonomy** | consistent error envelope + codes | ✅ RFC-7807-style `problem+json`, stable codes, `request_id`, no internal leakage | — |
| 11 | **Observability** | logs, metrics, tracing, audit | ✅ structured logs + correlation id; RED metrics; OTel tracing sync→async | ⏳ dashboards + SLO alerting |
| 12 | **Lifecycle & ops** | probes, graceful shutdown, config fail-fast, secrets | ✅ liveness/readiness; startup config validation | ⏳ graceful drain; secrets vault |
| 13 | **State & scale** | statelessness; multi-worker shared state | ✅ stateless compute; note the multi-worker status-store caveat (§14) | ⏳ shared store (redis) + `--workers N`/horizontal scale |
| 14 | **Data governance / PII** | at-rest, in-transit, retention, redaction | ✅ no PII at rest; TLS; redacted logs | ⏳ formal retention/DLP sign-off |
| 15 | **Testing pyramid** | unit / contract / golden / integration / load | ✅ unit + contract(schema) + golden + integration(mock DMP/webhook) | ⏳ load tests; contract tests in CI |
| 16 | **Packaging & CI/CD** | container, 12-factor, quality gates | ⏳ Dockerfile + CI | ⏳ canary/beta channel for AI |
| 17 | **Docs & runbook** | OpenAPI, changelog, on-call runbook | ✅ OpenAPI/Swagger | ⏳ runbook (DMP down, Ollama down, dead-letter drain) |

**Sharpest, non-obvious catches (called out):** (a) **SSRF via `callback_url`**
(#4); (b) **Tier-1 must survive DMP + Ollama both being down** (#6); (c) the
**in-process status store breaks under `--workers N`** (#13); (d) **cache keyed by
path alone serves stale data** — key on `(path,mtime,size)` (§7); (e) **response
caching by `data_fingerprint`** is both a perf win and a reproducibility reinforcement (#8).

---

## 18. Open questions for you (record your requirements here)

1. **DMP upload contract** — endpoint URL/auth (bearer vs mTLS), multipart field
   names, what it returns as `dmp_uri`, per-CRN pathing?
2. **Webhook** — per-request `callback_url` (as designed) or a single configured
   endpoint? HMAC signing OK, or a different scheme your ingress expects?
3. **JSON payload size** — full `bureau_report` vs summary-only? (`?view=` toggle.)
4. **Narration in JSON** — also return the narrative in the response/webhook, or
   HTML-only?
5. **Auth model** — static `X-API-Key` for v1, or gateway/OAuth from day one?
6. **Scale** — single worker (in-proc status store) or multi-worker (needs shared
   store) at launch?
7. **tl_features source** — carried in the DMP dump, or a separate referenced file?
8. **Retention/audit** — must JSON responses be persisted for compliance, or is
   return-and-forget fine?

---

## 19. Verification plan

Test CRN **`698167220`**; mock DMP endpoint + mock webhook receiver.

1. **Happy path** → `200` with `summary`, `audit`, `module_status`, `ai:null`,
   `artifact.status:"pending"`.
2. **Async completion** → mock DMP gets the multipart HTML; webhook gets
   `status:"done"` + `dmp_uri`; `X-Signature` verifies.
3. **Determinism golden test** → API numbers match expected CSVs in
   `tools/bureau_income/` and `tools/sustained_emi/`.
4. **Reproducibility** → identical requests → identical `data_fingerprint` + numbers.
5. **Determinism isolation** → same request with `narrate:true/false` → `summary`
   byte-identical; only `ai` differs.
6. **Tier-1 independence** → with DMP *and* Ollama down, `POST` still returns `200`
   deterministic JSON (artifact just fails async).
7. **Partial result** → force obligation failure → `module_status.obligation:"failed"` + warning; still `200`.
8. **DMP retry / webhook retry** → transient-then-success; always-fail → dead-letter / `webhook_failed`.
9. **Stale-cache fix** → overwrite file at same path → next POST reflects new numbers.
10. **Security** → bad key→401; traversal→403; **SSRF `callback_url` (private IP)→422**;
    missing file→400; bad columns→422; unknown CRN→404; dup key→409.
11. **CLI regression** → `python run_bureau.py 698167220` unchanged output.

---

## 20. Deferred / future work
- Full ports-and-adapters refactor (extract a pure `core/` engine package).
- Durable queue/worker (arq/Celery/RQ) for at-least-once async delivery at scale.
- Split `/v1/parse/*` and `/v1beta/ai-summary/*` into standalone endpoints.
- Full OAuth/OIDC + mTLS; per-caller rate limiting at a gateway.
- Dockerfile / CI; response caching; shared status store for multi-worker.
- Re-expose Excel or a batch endpoint if a use-case appears.
