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
- `../secrets_scanner.py` — `md5(...)` → `sha256(...)` in the unused
  `REDACT_HASH` path (default `redact_mode` is `REDACT_ALL`, so this output is
  never produced here); the detection log emits a secret *count* instead of the
  type list. Neither affects scan verdicts or redaction in our configuration.
- `../secrets_scanner.py` `plugins_used` (AIO-73 review finding) — upstream
  llm-guard 0.3.16 ships `BittrexDetector` paired with `beamer_api_token.py` and
  `BeamerApiTokenDetector` paired with `bittrex.py` (the two name→path entries are
  swapped). detect-secrets imports every custom-plugin path into a shared registry
  before resolving names, so upstream tolerates it, but it is fragile and
  mislabels. Corrected so each `name` matches the class defined at its `path`.
- `../secrets_scanner.py` temp-file cleanup (AIO-76) — upstream llm-guard 0.3.16
  calls `os.remove(temp_file.name)` only on the happy path, so a raised
  `scan_file()` (or any error between write and remove) leaves a file containing
  the raw user prompt on disk indefinitely. Wrapped in `try/finally` with
  `contextlib.suppress(FileNotFoundError)` so cleanup is guaranteed regardless of
  scan outcome. No effect on detection verdicts or redaction.
