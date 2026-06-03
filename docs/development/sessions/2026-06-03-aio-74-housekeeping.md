# Development Session - 2026-06-03
**Focus:** AIO-74 guard client fix + documentation/Linear housekeeping   **Status:** Complete

## Work Completed

- **AIO-74** (PR #98, merged): `LLMGuardClient` was sending `{"query":…}` → 422 → guard silently off in Pipeline+Steps path. Fixed: `input_text` key, context stringification, `strict_mode` wired end-to-end through all 3 router sites. 7 unit tests + 4 integration tests added. (files: `llm_guard_client.py`, `guard_validate.py`, `orchestrator.py`, `use_cases.py`)
- **BUILD_BOOTSTRAP_PLAN.md** synced (PR #100, merged): M1 + M2 marked complete with AIO ticket IDs; LLG-04 impact notes; M3 tickets aligned to Linear (AIO-51–57); "train" profile retired; AIO-67/68 captured.
- **Linear housekeeping:** AIO-68 cancelled (HF-gated model moot — aiprotect models removed for licensing); AIO-43 (M2 EPIC) marked Done; AIO-55/53/56 descriptions updated for post-LLG-04 reality.
- **Docs housekeeping:** CLAUDE.md ports corrected to 18-band scheme; ADR README count/pointer/profile updated; docs/README.md date + ADR-074 status; MASTER_ROADMAP_V2 status footer updated.

## Key Decisions

- "train" profile was a misunderstanding — removed entirely; offline path = `make build-offline` / `OFFLINE=1` ARG only.
- Stream order confirmed: LLG (AIO-75, AIO-76) → security vulnerabilities (Dependabot) → M3.

## Next Steps

- AIO-75: `LLM_GUARD_ENABLED=false` bypass not forwarded to `GuardValidate`
- AIO-76: Secrets scanner temp file with raw prompt left on disk on exception
- Security vulnerabilities: triage/resolve Dependabot alerts post-AIO-73 (7 in `llm_guard_svc/requirements.txt` should auto-close; 7 phantom `uv.lock` may need dismissal)
- Then M3: start AIO-51 (capture enterprise build specifics)
