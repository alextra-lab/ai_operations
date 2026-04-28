# Requirements Outdated Assessment (Feb 2025)

Assessment of `pip list --outdated` against the project's service requirements and compatibility constraints.

## Summary

- **Update requirements files:** Only for a small set of safe relaxations and security-related minimums. Most “outdated” packages are either already satisfied by version ranges, or intentionally pinned for ecosystem compatibility.
- **Do not chase “latest” for:** numpy (must stay \<2), transformers (4.53.x / 4.51.3), spacy 3.7.x, spacy-pkuseg, uvicorn pin, openai major, packaging 23.x, passlib, and opentelemetry/prometheus pins until a coordinated upgrade.
- **Optional phased upgrades:** opentelemetry 1.37 → 1.39, prometheus-client 0.23 → 0.24, uvicorn 0.36 → 0.40 (test thoroughly).

---

## 1. Do NOT update (constraints / ecosystem pins)

| Package | Current in reqs | Why leave as-is |
|--------|-----------------|------------------|
| **numpy** | \<2.0.0 (orchestrator, corpus_svc, embedding, llm_guard_svc) | Project-wide constraint; many ML deps not yet numpy 2–compatible. |
| **transformers** | 4.53.x (constraints) / 4.51.3 (llm_guard_svc) | 5.0.0 is major; llm-guard pins 4.51.3. Keep two-version wheelhouse strategy. |
| **spacy** | 3.7.x, \<3.8.0 | Language models (en_core_web_sm-3.7.1, zh_core_web_sm-3.7.0) target 3.7.x. |
| **spacy-pkuseg** | ==0.0.33 | Pinned; 1.0.1 is major, likely breaking. |
| **uvicorn** | ==0.36.0 | Explicit pin across services; 0.40.0 upgrade should be a separate, tested change. |
| **openai** | \>=1.79.0,\<3.0.0 | Intentionally cap at \<3; no need to require latest 2.x in files. |
| **packaging** | \>=23.0,\<24.0 (llm_guard_svc) | llm-guard compatibility. |
| **passlib** | ==1.7.4 | Explicit pin; keep unless doing a dedicated auth stack upgrade. |
| **opentelemetry-***, **prometheus-client** | ==1.37.0, ==0.23.1 | Pinned for consistency; upgrade as a coordinated observability pass if desired. |
| **python-json-logger** | ==2.0.7 (llm_guard_svc) | Pinned for llm-guard set. |
| **cachetools** | \>=4.2.0,\<6.0.0 | 7.0.0 would need constraint change; leave for later. |
| **jsonschema** | \>=4.0.0, \<5.0.0 (inference-gateway) | Keep \<5.0.0 to avoid breaking changes. |

---

## 2. Safe to relax (allow current “latest” within existing strategy)

These are either already minimum bounds (so pip can already install newer) or are strict pins that can be relaxed to minimum versions so patch/minor updates are possible without changing behavior.

| Package | Current in reqs | Recommendation |
|---------|-----------------|----------------|
| **bcrypt** | \>=4.2.0,\<6.0.0 | No change; 5.0.0 already allowed. |
| **fastapi** | \>=0.117.1 | No change; 0.128.0 already in range. |
| **pydantic** | \>=2.11.9,\<3.0.0 | No change. |
| **sqlalchemy** | \>=2.0.43 | No change. |
| **psycopg** / **psycopg[binary]** | \>=3.2.3 | No change. |
| **structlog** | \>=24.1.0 | No change. |
| **asyncpg** | \>=0.30.0 (or \>=0.29.0 shared) | No change. |
| **aiosqlite** | \>=0.19.0 | No change. |
| **tenacity** | \>=8.2.3 / \>=8.2.0 | No change (9.x is major; test before requiring). |
| **requests** | \>=2.31.0 | No change. |
| **aiohttp** | \>=3.9.0 | No change. |
| **qdrant-client** | \>=1.10.0,\<2.0.0 | No change. |
| **nltk** | \>=3.8.1 | No change. |
| **pdfplumber** | \>=0.10.0,\<0.12.0 | No change. |
| **redis** | \>=5.0.0 | No change. |

---

## 3. Optional requirement-file updates (low risk)

Relaxing **strict pins** to **minimum versions** so pip can choose compatible patch/minor updates without you changing files again. Only where we already know the “latest” is compatible.

| Service | Package | Current | Suggested | Note |
|---------|---------|---------|-----------|------|
| corpus_svc | beautifulsoup4 | ==4.13.3 | \>=4.13.3 | Allow 4.14.x. |
| corpus_svc | python-dotenv | ==1.0.1 | \>=1.0.1 | Allow 1.2.x. |
| corpus_svc | psycopg_pool | ==3.2.6 | \>=3.2.6 | Allow 3.3.x if compatible. |
| corpus_svc | python-docx | \>=1.1.2 | (no change) | 1.2.0 already in range. |
| corpus_svc | lxml | \>=4.9.3 | (no change or \>=4.9.3,\<7) | 6.x may be fine; test before requiring. |

---

## 4. Security-related (consider after checking release notes)

| Package | Current | Latest | Action |
|---------|---------|--------|--------|
| **cryptography** | 44.0.3 | 46.0.4 | Check release notes for breaking changes; if none, set e.g. \>=44.0.3 in a central place or leave to range. |
| **bcrypt** | 4.3.0 in env | 5.0.0 | Already allowed by \>=4.2.0,\<6.0.0; no requirement change. |
| **urllib3** / **requests** | (transitive) | 2.6.3 / 2.32.5 | Usually pulled by httpx/requests; ensure requests \>=2.31.0 and run pip-audit. |

Run after any change:

```bash
pip-audit -r requirements-all.txt
```

---

## 5. Dev-only / not in service requirements

Many packages in your `pip list --outdated` are **dev** or **tooling** (e.g. pytest, mypy, black, ruff, streamlit, langchain, coverage). They are not in the service `requirements.txt` files. Updating them is optional and should not drive changes to the service requirements; use a separate dev requirements file or venv and upgrade when convenient.

---

## 6. Recommended next steps

1. **No change required** for most requirements; version ranges already allow the “latest” you care about (e.g. fastapi, pydantic, sqlalchemy, psycopg, asyncpg, tenacity, aiohttp, redis).
2. **Optionally relax pins** in `corpus_svc/requirements.txt` only: beautifulsoup4, python-dotenv, psycopg_pool as in the table above.
3. **Keep** numpy \<2, transformers 4.53/4.51.3, spacy 3.7.x, spacy-pkuseg, uvicorn, openai \<3, packaging 23.x, passlib, and observability pins unless you run a dedicated upgrade phase.
4. **Re-run** `pip list --outdated` and `pip-audit -r requirements-all.txt` after any edits and after rebuilding the wheelhouse.
