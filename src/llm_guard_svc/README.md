# LLM-Guard Service

An API service that validates and sanitizes text inputs (e.g. user prompts) before
they reach an LLM. The service name, container name (`llm-guard-svc`), API
(`POST /api/validate`), and `LLM_GUARD_*` configuration are unchanged, but as of the
**LLG-04 finale** it no longer depends on the `llm-guard` PyPI library — every
scanner runs a native, permissively-licensed implementation (see `app/scanners/`).
This removed the library's hard `transformers==4.51.3` pin and closed 7 CVEs.

## Scanners (all native)

| Scanner | Implementation | License |
|---|---|---|
| `regex` | stdlib `re` + presidio TextReplaceBuilder | MIT |
| `secrets` | `detect-secrets` (vendored plugins) | MIT |
| `prompt_injection` | ONNX (deberta-v3) via transformers + optimum | Apache-2.0 |
| `gibberish` | ONNX classifier | Apache-2.0 |
| `language` | ONNX (xlm-roberta) | MIT |
| `anonymize` (PII) | Presidio pattern recognizers + GLiNER `gliner_multi_pii-v1` | MIT / Apache-2.0 |

The previous PII model (`distilbert_finetuned_ai4privacy_v2`) was **removed** — it is
`cc-by-nc-4.0` (non-commercial). PII now uses Presidio pattern recognizers (email,
credit card, US SSN, phone, IBAN) plus GLiNER for free-text `PERSON`/`LOCATION`.

## ⚠️ Disabled by default

`LLM_GUARD_ENABLED` defaults to **`false`**. The service returns a pass-through
response and the orchestrator skips it. Enable it **only after** staging the models
(below). The native PII engine is **not supported on the enterprise profile**.

## Prerequisite: stage the models (manual, before enabling)

Models are **not** downloaded during the image build. They are staged once into
`data/llm-guard-models/` (mounted read-only to `/app/models`, which is also
`HF_HOME`) by the operator:

```bash
python ops/bootstrap/download_llm_guard_models.py --output-dir data/llm-guard-models
```

This stages:
- the three ONNX classifiers (gibberish, language, prompt-injection), ONNX files only;
- GLiNER `urchade/gliner_multi_pii-v1` (PyTorch weights kept);
- **the GLiNER backbone tokenizer** `microsoft/mdeberta-v3-base` into `data/llm-guard-models/hub`
  (the HF cache). GLiNER ships no tokenizer and loads its backbone's at runtime, so
  without this it cannot load offline (`local_files_only=True` / `HF_HUB_OFFLINE=1`).

PII thresholds are calibrated against `tests/parity/pii_labelled.py`
(`LLM_GUARD_PII_SCORE_THRESHOLD=0.3`, `LLM_GUARD_PII_GLINER_THRESHOLD=0.93`) and can be
overridden via env.

## Building and running

```bash
# Build just this service (local profile)
make build                       # or: docker compose ... build llm-guard-svc

# Stage models (see above), then enable + start
#   set LLM_GUARD_ENABLED=true in config/env/.env
make up
```

Lazy loading: no model loads at import, startup, or `/health`. The native scanners
are built once (process singleton) on the first `/api/validate` call.

## API

`POST /api/validate` — body `{"input_text": "...", "context": {...}, "strict_mode": false}`
→ `{"sanitized_text", "risk_score", "modified", "details": {<scanner>: {"passed", "score"}}}`.

`GET /health` — liveness (does not load models).

## Validation

- Native-scanner parity vs the frozen golden + latency budget:
  `PARITY_CANDIDATE_URL=<url> pytest src/llm_guard_svc/tests/parity/test_parity.py`.
- PII recall/precision against the labelled set (needs the model stack, runs in-container):
  `pytest tests/parity/test_pii_metrics_container.py -q -s`.

## Troubleshooting

- **GLiNER fails to load offline** — the backbone tokenizer
  (`microsoft/mdeberta-v3-base`) is not staged under `data/llm-guard-models/hub`; re-run
  the download script.
- **Service returns `status: disabled`** — `LLM_GUARD_ENABLED` is `false` (the default);
  set it to `true` after staging models.
- **"Cannot access files in /app/models"** — the models volume is not mounted / empty.
