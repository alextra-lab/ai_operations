# Vendored detect-secrets plugins

Copied verbatim from `llm-guard==0.3.16`
(`llm_guard/input_scanners/secrets_plugins/`) on 2026-06-01 as part of LLG-04
(AIO-1), so the native `secrets` scanner reproduces llm-guard's detection set
exactly after llm-guard is removed.

- **License:** MIT (llm-guard). Plugins subclass `detect_secrets.plugins.base`.
- **Do not edit** — refresh by re-copying from the same source if the upstream
  plugin set changes.

## Deviations from verbatim (documented)

Minimal, behaviour-preserving security fixes applied to silence CodeQL HIGH
alerts on this vendored code (the repo uses CodeQL default setup, so paths can't
be excluded via config). None change detection for any realistic/SOC input or
any parity-tested case:

- `sidekiq.py` — escaped the literal dots in the Sidekiq sensitive-URL hostname
  regex (`gems.contribsys.com` → `gems\.contribsys\.com`, and the `enterprise`
  variant). Fixes `py/incomplete-hostname-regexp`; only narrows matching of
  Sidekiq enterprise URLs with non-dot hostname characters (not present in our
  corpus).
- `../secrets_scanner.py` — `md5(...)` in the unused `REDACT_HASH` path gains
  `usedforsecurity=False` (identical output); the detection log emits a secret
  *count* instead of the type list. Neither affects scan verdicts or redaction.
