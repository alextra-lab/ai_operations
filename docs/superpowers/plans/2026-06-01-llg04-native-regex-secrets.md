# Native `regex` + `secrets` Scanners Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `llm-guard`-backed `regex` and `secrets` scanners with verbatim native ports (depending on `bc-detect-secrets` + `presidio-anonymizer`, not `llm_guard`), behind per-scanner engine flags defaulting to `llm_guard`, with byte-exact parity proven against the golden baseline.

**Architecture:** Port llm-guard's MIT `regex.py`/`secrets.py` into `src/llm_guard_svc/app/scanners/` (vendoring the 95 bundled detect-secrets plugins), swapping only the `llm_guard` logger/base imports for stdlib. `LLMGuard.__init__` gains `regex_engine`/`secrets_engine` params (sourced from `LLMGuardConfig`) selecting native vs llm-guard per scanner. Parity is validated by unit-level tests that instantiate the native scanners directly — no model stack, no `llm_guard` import.

**Tech Stack:** Python 3.12, `bc-detect-secrets==1.5.43`, `presidio-anonymizer==2.2.358`, pytest, Pydantic config.

**Spec:** `docs/development/specs/llm-guard-native-regex-secrets-spec.md`

**Prerequisites for execution:**
- The current `llm-guard-svc` container is running (source of the vendored files): `docker ps | grep llm-guard-svc`.
- A test venv with the light deps (NOT the full model stack):
  ```bash
  .venv/bin/python -m pip install bc-detect-secrets==1.5.43 presidio-anonymizer==2.2.358 pytest
  ```
  All `pytest` commands below use `.venv/bin/python -m pytest`. The native scanners import only `detect_secrets` + `presidio_anonymizer`, so torch/transformers/llm-guard are NOT required for Tasks 1–4.

**Branch:** `feat/llg04-native-regex-secrets` (already created; the spec is committed there).

---

## File Structure

- Create `src/llm_guard_svc/app/scanners/__init__.py` — package marker + exports.
- Create `src/llm_guard_svc/app/scanners/regex_scanner.py` — native Regex port + `CREDENTIAL_PATTERNS`.
- Create `src/llm_guard_svc/app/scanners/secrets_scanner.py` — native Secrets port (copy + patch).
- Create `src/llm_guard_svc/app/scanners/secrets_plugins/` — 95 vendored plugin modules + `PROVENANCE.md`.
- Modify `src/llm_guard_svc/requirements.txt` — declare the two deps explicitly.
- Modify `src/shared/config/schemas.py` — `regex_engine`/`secrets_engine` fields.
- Modify `src/shared/config/loader.py` — read the two new env vars.
- Modify `src/llm_guard_svc/app/guard.py` — engine selection in `LLMGuard.__init__`.
- Modify `src/llm_guard_svc/app/main.py` — pass engines from config into `LLMGuard`.
- Create `src/llm_guard_svc/tests/parity/test_scanner_parity.py` — per-scanner parity vs golden.
- Create `src/llm_guard_svc/tests/test_engine_config.py` — config flag defaults/override.
- Create `src/llm_guard_svc/tests/test_engine_selection.py` — guard wiring (skips without llm_guard).

---

## Task 1: Dependencies + scanners package + vendored plugins

**Files:**
- Modify: `src/llm_guard_svc/requirements.txt`
- Create: `src/llm_guard_svc/app/scanners/__init__.py`
- Create: `src/llm_guard_svc/app/scanners/secrets_plugins/` (vendored)
- Create: `src/llm_guard_svc/app/scanners/secrets_plugins/PROVENANCE.md`

- [ ] **Step 1: Declare the deps explicitly in `requirements.txt`**

Insert after line 23 (`sentencepiece>=0.2.0`), before the spaCy block:

```
# --- Native scanner stack (LLG-04: regex + secrets ported off llm-guard) ---
# Pinned to the versions llm-guard==0.3.16 already resolves, so the vendored
# detect-secrets plugins behave identically. Currently transitive via llm-guard.
bc-detect-secrets==1.5.43
presidio-anonymizer==2.2.358
```

- [ ] **Step 2: Create the package marker**

Create `src/llm_guard_svc/app/scanners/__init__.py`:

```python
"""Native scanner ports for the LLG-04 migration off llm-guard.

Each scanner here is a verbatim port of the corresponding MIT-licensed
llm-guard input scanner, depending on detect_secrets / presidio_anonymizer
directly (never llm_guard). See
docs/development/specs/llm-guard-native-regex-secrets-spec.md.
"""

from .regex_scanner import RegexScanner
from .secrets_scanner import SecretsScanner

__all__ = ["RegexScanner", "SecretsScanner"]
```

NOTE: this imports the two modules created in Tasks 2 and 3. If running Task 1
in isolation, temporarily leave `__init__.py` empty and add the exports at the
end of Task 3. (Subagent-driven execution: create the file with exports in Task 3.)

- [ ] **Step 3: Vendor the 95 detect-secrets plugins from the running container**

```bash
mkdir -p src/llm_guard_svc/app/scanners/secrets_plugins
docker cp 'llm-guard-svc:/usr/local/lib/python3.12/site-packages/llm_guard/input_scanners/secrets_plugins/.' \
  src/llm_guard_svc/app/scanners/secrets_plugins/
rm -rf src/llm_guard_svc/app/scanners/secrets_plugins/__pycache__
```

- [ ] **Step 4: Verify the vendoring**

Run:
```bash
ls src/llm_guard_svc/app/scanners/secrets_plugins/*.py | wc -l
grep -rl "from llm_guard" src/llm_guard_svc/app/scanners/secrets_plugins/ || echo "NO llm_guard imports — good"
```
Expected: `96` (95 plugins + `__init__.py`); `NO llm_guard imports — good`.

- [ ] **Step 5: Record provenance**

Create `src/llm_guard_svc/app/scanners/secrets_plugins/PROVENANCE.md`:

```markdown
# Vendored detect-secrets plugins

Copied verbatim from `llm-guard==0.3.16`
(`llm_guard/input_scanners/secrets_plugins/`) on 2026-06-01 as part of LLG-04
(AIO-1), so the native `secrets` scanner reproduces llm-guard's detection set
exactly after llm-guard is removed.

- **License:** MIT (llm-guard). Plugins subclass `detect_secrets.plugins.base`.
- **Do not edit** — refresh by re-copying from the same source if the upstream
  plugin set changes.
```

- [ ] **Step 6: Commit**

```bash
git add src/llm_guard_svc/requirements.txt src/llm_guard_svc/app/scanners/
git commit -m "feat(llm-guard): vendor detect-secrets plugins + declare native scanner deps (AIO-1)"
```

---

## Task 2: Native `RegexScanner` (TDD)

**Files:**
- Create: `src/llm_guard_svc/app/scanners/regex_scanner.py`
- Test: `src/llm_guard_svc/tests/parity/test_scanner_parity.py`

- [ ] **Step 1: Write the failing test**

Create `src/llm_guard_svc/tests/parity/test_scanner_parity.py`:

```python
"""Per-scanner parity for the native regex + secrets scanners (LLG-04 step 1).

Validates the native ports against the golden baseline WITHOUT the heavy model
stack: native scanners import only detect_secrets + presidio_anonymizer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.llm_guard_svc.app.scanners.regex_scanner import RegexScanner
from src.llm_guard_svc.tests.parity.corpus import CORPUS

GOLDEN_PATH = Path(__file__).parent / "golden" / "baseline.json"

# Cases where exactly one of {regex, secrets} redacts and upstream scanners are
# no-ops, so the golden final sanitized_text equals that scanner's own output.
EXPECTED_REDACTION = {
    "regex_password_assignment": ("regex", "[REDACTED]"),
    "regex_api_key_colon": ("regex", "[REDACTED]"),
    "regex_ssh_rsa_key": ("regex", "Deploy key: [REDACTED] admin@host"),
    "secret_aws_keypair": ("secrets", "aws_access_key_id=****** aws_secret_access_key=******"),
    "secret_github_pat": ("secrets", "export GH_TOKEN=************AB"),
}


@pytest.fixture(scope="module")
def golden():
    if not GOLDEN_PATH.exists():
        pytest.skip("no golden baseline; run the parity capture CLI")
    return json.loads(GOLDEN_PATH.read_text())["cases"]


@pytest.fixture(scope="module")
def regex_scanner():
    return RegexScanner()


@pytest.mark.parametrize("case", CORPUS, ids=[c.id for c in CORPUS])
def test_regex_verdict_matches_golden(case, regex_scanner, golden):
    g = golden[case.id]["response"]["details"]["regex"]
    sanitized, passed, score = regex_scanner.scan(case.text)
    assert passed == g["passed"]
    assert score == g["score"]
    if passed:
        assert sanitized == case.text  # passed -> no redaction
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest src/llm_guard_svc/tests/parity/test_scanner_parity.py -q`
Expected: collection error / FAIL — `ModuleNotFoundError: ...regex_scanner`.

- [ ] **Step 3: Implement `regex_scanner.py`**

Create `src/llm_guard_svc/app/scanners/regex_scanner.py`:

```python
"""Native port of llm-guard's Regex input scanner (MIT).

Verbatim from llm_guard.input_scanners.regex (llm-guard==0.3.16), with only the
dependency swaps needed to drop the llm_guard import:
  * llm_guard.util.get_logger      -> stdlib logging
  * the structural `Scanner` Protocol base is dropped (not needed at runtime)
Match type, redaction, and the signed score convention are unchanged.
"""

from __future__ import annotations

import logging
import re
from enum import Enum

from presidio_anonymizer.core.text_replace_builder import TextReplaceBuilder

LOGGER = logging.getLogger(__name__)

# The two production patterns, verbatim from app/guard.py (single source of truth;
# guard.py imports this for the llm-guard branch too).
CREDENTIAL_PATTERNS: list[str] = [
    r"(password|api_key|secret|token)[\s]*[=:][\s]*[\w\d]{8,}",
    r"ssh-rsa[\s]+[A-Za-z0-9+/]+={0,2}",
]


class MatchType(Enum):
    SEARCH = "search"
    FULL_MATCH = "fullmatch"
    ALL = "all"

    def match(self, pattern: re.Pattern[str], text: str) -> list[re.Match[str]]:
        if self.value == "all":
            return list(pattern.finditer(text))[::-1]  # reverse to keep indices valid
        m = None
        if self.value == "search":
            m = pattern.search(text)
        if self.value == "fullmatch":
            m = pattern.fullmatch(text)
        if m is None:
            return []
        return [m]


class RegexScanner:
    """Detects configured patterns; redacts matches to ``[REDACTED]``."""

    def __init__(
        self,
        patterns: list[str] | None = None,
        *,
        is_blocked: bool = True,
        match_type: MatchType = MatchType.SEARCH,
        redact: bool = True,
    ) -> None:
        self._patterns = [re.compile(p) for p in (patterns or CREDENTIAL_PATTERNS)]
        self._match_type = match_type
        self._is_blocked = is_blocked
        self._redact = redact

    def scan(self, prompt: str) -> tuple[str, bool, float]:
        builder = TextReplaceBuilder(original_text=prompt)
        for pattern in self._patterns:
            matches = self._match_type.match(pattern, prompt)
            if not matches:
                continue
            if self._is_blocked:
                if self._redact:
                    for match in matches:
                        builder.replace_text_get_insertion_index(
                            "[REDACTED]", match.start(), match.end()
                        )
                return builder.output_text, False, 1.0
            return builder.output_text, True, -1.0
        if self._is_blocked:
            return builder.output_text, True, -1.0
        return builder.output_text, False, 1.0
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest src/llm_guard_svc/tests/parity/test_scanner_parity.py -q`
Expected: PASS (22 parametrized cases for `test_regex_verdict_matches_golden`).

- [ ] **Step 5: Commit**

```bash
git add src/llm_guard_svc/app/scanners/regex_scanner.py src/llm_guard_svc/tests/parity/test_scanner_parity.py
git commit -m "feat(llm-guard): native RegexScanner with golden parity (AIO-1)"
```

---

## Task 3: Native `SecretsScanner` (TDD)

**Files:**
- Create: `src/llm_guard_svc/app/scanners/secrets_scanner.py` (copy + patch)
- Modify: `src/llm_guard_svc/app/scanners/__init__.py` (add `SecretsScanner` export)
- Test: `src/llm_guard_svc/tests/parity/test_scanner_parity.py` (extend)

- [ ] **Step 1: Extend the test (failing)**

Append to `src/llm_guard_svc/tests/parity/test_scanner_parity.py`:

```python
from src.llm_guard_svc.app.scanners.secrets_scanner import SecretsScanner


@pytest.fixture(scope="module")
def secrets_scanner():
    return SecretsScanner()


@pytest.mark.parametrize("case", CORPUS, ids=[c.id for c in CORPUS])
def test_secrets_verdict_matches_golden(case, secrets_scanner, golden):
    g = golden[case.id]["response"]["details"]["secrets"]
    sanitized, passed, score = secrets_scanner.scan(case.text)
    assert passed == g["passed"]
    assert score == g["score"]
    if passed:
        assert sanitized == case.text


@pytest.mark.parametrize(
    "case_id,expected", list(EXPECTED_REDACTION.items()), ids=list(EXPECTED_REDACTION)
)
def test_redaction_matches_golden(case_id, expected, regex_scanner, secrets_scanner, golden):
    scanner_name, expected_text = expected
    text = golden[case_id]["input_text"]
    scanner = regex_scanner if scanner_name == "regex" else secrets_scanner
    sanitized, passed, _ = scanner.scan(text)
    assert not passed
    assert sanitized == expected_text
    # Upstream scanners are no-ops for these inputs, so this equals the golden
    # final sanitized_text too.
    assert sanitized == golden[case_id]["response"]["sanitized_text"]
```

NOTE: the top-of-file import added in Task 2 must stay; add the new
`SecretsScanner` import line (shown above) near it.

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest src/llm_guard_svc/tests/parity/test_scanner_parity.py -q`
Expected: FAIL — `ModuleNotFoundError: ...secrets_scanner`.

- [ ] **Step 3: Copy the source then apply the dependency-swap patch**

Copy llm-guard's `secrets.py` verbatim, then patch the 5 llm_guard-specific lines:

```bash
docker cp 'llm-guard-svc:/usr/local/lib/python3.12/site-packages/llm_guard/input_scanners/secrets.py' \
  src/llm_guard_svc/app/scanners/secrets_scanner.py
```

Apply exactly these edits to `src/llm_guard_svc/app/scanners/secrets_scanner.py`:

1. Add `import logging` to the stdlib import block at the top (alongside `import hashlib`, `import os`, `import tempfile`).
2. Delete the line `from llm_guard.util import get_logger`.
3. Delete the line `from .base import Scanner`.
4. Replace `LOGGER = get_logger()` with `LOGGER = logging.getLogger(__name__)`.
5. Replace `class Secrets(Scanner):` with `class SecretsScanner:`.
6. In `scan()`, replace `LOGGER.warning("Detected secrets in prompt", secret_types=secret_types)` with `LOGGER.warning("Detected secrets in prompt: %s", secret_types)` (stdlib logging takes no structlog kwargs).

Prepend this module docstring above the imports:

```python
"""Native port of llm-guard's Secrets input scanner (MIT).

Verbatim from llm_guard.input_scanners.secrets (llm-guard==0.3.16) with only the
dependency swaps needed to drop the llm_guard import (logger -> stdlib logging,
the Scanner Protocol base dropped, class renamed to SecretsScanner). The
detect-secrets plugin config and REDACT_ALL redaction are unchanged, and the
bundled custom plugins are vendored alongside in ``secrets_plugins/`` — so
detection and the exact redaction (e.g. ``************AB``) match the current
service byte-for-byte.
"""
```

- [ ] **Step 4: Verify no `llm_guard` references remain + add the export**

Run:
```bash
grep -n "llm_guard" src/llm_guard_svc/app/scanners/secrets_scanner.py || echo "clean — no llm_guard refs"
```
Expected: `clean — no llm_guard refs`.

Ensure `src/llm_guard_svc/app/scanners/__init__.py` exports both classes (see Task 1 Step 2 content).

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest src/llm_guard_svc/tests/parity/test_scanner_parity.py -q`
Expected: PASS — all `test_regex_*`, `test_secrets_*`, and `test_redaction_matches_golden` cases green. In particular `secret_github_pat` redacts to `export GH_TOKEN=************AB`.

- [ ] **Step 6: Commit**

```bash
git add src/llm_guard_svc/app/scanners/secrets_scanner.py src/llm_guard_svc/app/scanners/__init__.py src/llm_guard_svc/tests/parity/test_scanner_parity.py
git commit -m "feat(llm-guard): native SecretsScanner with golden parity (AIO-1)"
```

---

## Task 4: Engine flags in `LLMGuardConfig` (TDD)

**Files:**
- Modify: `src/shared/config/schemas.py:253-256` (end of `LLMGuardConfig`)
- Modify: `src/shared/config/loader.py:276-279` (inside `load_llm_guard_config`)
- Test: `src/llm_guard_svc/tests/test_engine_config.py`

- [ ] **Step 1: Write the failing test**

Create `src/llm_guard_svc/tests/test_engine_config.py`:

```python
"""LLMGuardConfig per-scanner engine flags (LLG-04)."""

from shared.config.loader import load_llm_guard_config


def test_engine_defaults_to_llm_guard(monkeypatch):
    monkeypatch.delenv("LLM_GUARD_REGEX_ENGINE", raising=False)
    monkeypatch.delenv("LLM_GUARD_SECRETS_ENGINE", raising=False)
    cfg = load_llm_guard_config()
    assert cfg.regex_engine == "llm_guard"
    assert cfg.secrets_engine == "llm_guard"


def test_engine_env_override(monkeypatch):
    monkeypatch.setenv("LLM_GUARD_REGEX_ENGINE", "native")
    monkeypatch.setenv("LLM_GUARD_SECRETS_ENGINE", "native")
    cfg = load_llm_guard_config()
    assert cfg.regex_engine == "native"
    assert cfg.secrets_engine == "native"
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=.:src .venv/bin/python -m pytest src/llm_guard_svc/tests/test_engine_config.py -q`
Expected: FAIL — `AttributeError: 'LLMGuardConfig' object has no attribute 'regex_engine'`.

- [ ] **Step 3: Add the fields to `LLMGuardConfig`**

In `src/shared/config/schemas.py`, immediately after the `prompt_injection_model_dir` field (currently ending at line 256), add:

```python
    regex_engine: str = Field(
        default="llm_guard",
        description="Engine for the regex scanner: 'llm_guard' or 'native' (LLG-04)",
    )
    secrets_engine: str = Field(
        default="llm_guard",
        description="Engine for the secrets scanner: 'llm_guard' or 'native' (LLG-04)",
    )
```

- [ ] **Step 4: Read the env vars in the loader**

In `src/shared/config/loader.py`, inside the `LLMGuardConfig(...)` construction, after the `prompt_injection_model_dir=...` argument (line 276-279) and before the closing `)`, add:

```python
        regex_engine=os.environ.get("LLM_GUARD_REGEX_ENGINE", "llm_guard"),
        secrets_engine=os.environ.get("LLM_GUARD_SECRETS_ENGINE", "llm_guard"),
```

- [ ] **Step 5: Run to verify it passes**

Run: `PYTHONPATH=.:src .venv/bin/python -m pytest src/llm_guard_svc/tests/test_engine_config.py -q`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add src/shared/config/schemas.py src/shared/config/loader.py src/llm_guard_svc/tests/test_engine_config.py
git commit -m "feat(config): per-scanner engine flags for llm-guard (AIO-1)"
```

---

## Task 5: Wire engine selection into `LLMGuard` (TDD, env-gated)

**Files:**
- Modify: `src/llm_guard_svc/app/guard.py:228-310` (`LLMGuard.__init__`)
- Modify: `src/llm_guard_svc/app/main.py:94-100` (`get_llm_guard` construction)
- Test: `src/llm_guard_svc/tests/test_engine_selection.py`

- [ ] **Step 1: Write the failing test (skips without the full stack)**

Create `src/llm_guard_svc/tests/test_engine_selection.py`:

```python
"""LLMGuard selects native vs llm-guard scanner engines per config (LLG-04).

Skipped where the full llm-guard stack is unavailable (runs in the service image
/ CI), since constructing LLMGuard imports llm_guard.
"""

import importlib.util
import logging

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("llm_guard") is None,
    reason="requires the full llm-guard stack (service image / CI)",
)


def _guard(**engines):
    from src.llm_guard_svc.app.guard import LLMGuard

    return LLMGuard(logger=logging.getLogger("test"), **engines)


def test_native_engines_select_native_classes():
    from src.llm_guard_svc.app.scanners import RegexScanner, SecretsScanner

    g = _guard(regex_engine="native", secrets_engine="native")
    assert isinstance(g.scanners["regex"], RegexScanner)
    assert isinstance(g.scanners["secrets"], SecretsScanner)


def test_default_engines_select_llm_guard():
    from src.llm_guard_svc.app.scanners import RegexScanner, SecretsScanner

    g = _guard()
    assert not isinstance(g.scanners["regex"], RegexScanner)
    assert not isinstance(g.scanners["secrets"], SecretsScanner)
```

- [ ] **Step 2: Run to verify it fails (in the full-stack env)**

Run (inside the service image or a venv with llm-guard installed):
`python -m pytest src/llm_guard_svc/tests/test_engine_selection.py -q`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'regex_engine'`.
(If `llm_guard` is absent locally, the test SKIPS — that is expected; it runs in CI.)

- [ ] **Step 3: Add engine params + selection to `LLMGuard.__init__`**

In `src/llm_guard_svc/app/guard.py`, extend the `__init__` signature (after `cache_ttl_seconds: int = 3600,`):

```python
        regex_engine: str = "llm_guard",
        secrets_engine: str = "llm_guard",
```

Then, just before the `self.scanners = {` dict literal, build the two swappable scanners:

```python
        # Per-scanner engine selection (LLG-04). Native ports drop the llm_guard
        # dependency; default keeps the original llm-guard scanners.
        from .scanners.regex_scanner import CREDENTIAL_PATTERNS

        if regex_engine == "native":
            from .scanners.regex_scanner import RegexScanner

            regex_scanner: Any = RegexScanner()
        else:
            regex_scanner = Regex(
                patterns=CREDENTIAL_PATTERNS,
                match_type=RMatchType.SEARCH,
            )

        if secrets_engine == "native":
            from .scanners.secrets_scanner import SecretsScanner

            secrets_scanner: Any = SecretsScanner()
        else:
            secrets_scanner = Secrets()
```

Then in the `self.scanners = { ... }` dict, replace the inline `"secrets": Secrets(),`
with `"secrets": secrets_scanner,` and replace the inline `"regex": Regex(...)`
entry (the multi-line `Regex(patterns=[...], match_type=RMatchType.SEARCH)`)
with `"regex": regex_scanner,`. Leave `anonymize`, `prompt_injection`,
`gibberish`, `language` untouched.

- [ ] **Step 4: Pass the engines from config in `main.py`**

In `src/llm_guard_svc/app/main.py`, the `get_llm_guard()` function returns
`LLMGuard(...)` (lines 94-100). Add two arguments to that call:

```python
        regex_engine=llm_guard_config.regex_engine,
        secrets_engine=llm_guard_config.secrets_engine,
```

- [ ] **Step 5: Run to verify it passes (full-stack env)**

Run: `python -m pytest src/llm_guard_svc/tests/test_engine_selection.py -q`
Expected: PASS (2 tests) where llm-guard is installed; SKIP otherwise.

- [ ] **Step 6: Commit**

```bash
git add src/llm_guard_svc/app/guard.py src/llm_guard_svc/app/main.py src/llm_guard_svc/tests/test_engine_selection.py
git commit -m "feat(llm-guard): select regex/secrets engine per config (AIO-1)"
```

---

## Task 6: Full verification, lint, and PR

**Files:**
- Modify: `docs/development/specs/llm-guard-native-regex-secrets-spec.md` (status)
- Modify: `docs/development/analysis/llm-guard-replacement-evaluation.md` (§10.2 progress note)

- [ ] **Step 1: Lint + format the new/changed Python**

Run:
```bash
ruff check --fix src/llm_guard_svc/app/scanners/ src/llm_guard_svc/tests/ src/shared/config/
black --line-length 100 src/llm_guard_svc/app/scanners/regex_scanner.py src/llm_guard_svc/app/scanners/secrets_scanner.py src/llm_guard_svc/tests/parity/test_scanner_parity.py src/llm_guard_svc/tests/test_engine_config.py src/llm_guard_svc/tests/test_engine_selection.py
```
Expected: `All checks passed!` and no reformatting needed on re-run.
NOTE: do NOT reformat the vendored `secrets_plugins/` or the copied
`secrets_scanner.py` body beyond the documented patch — keep them verbatim. If
ruff flags the vendored plugins, add `src/llm_guard_svc/app/scanners/secrets_plugins/`
to `extend-exclude` in `pyproject.toml`'s `[tool.ruff]` and note it in the commit.

- [ ] **Step 2: Run the parity + config tests (light env)**

Run:
```bash
PYTHONPATH=.:src .venv/bin/python -m pytest \
  src/llm_guard_svc/tests/parity/test_scanner_parity.py \
  src/llm_guard_svc/tests/test_engine_config.py -v
```
Expected: all PASS (regex 22 + secrets 22 + redaction 5 + config 2).

- [ ] **Step 3: Update the spec status**

In `docs/development/specs/llm-guard-native-regex-secrets-spec.md`, change the
`**Status:**` line to `Implemented (2026-06-01) — native regex+secrets behind flags, parity green`.

- [ ] **Step 4: Add a progress note to the evaluation doc**

In `docs/development/analysis/llm-guard-replacement-evaluation.md`, under §10
(Suggested sequencing) item 2, append:

```markdown
   - **DONE (2026-06-01):** native `regex` + `secrets` ported off llm-guard
     (`app/scanners/`), behind `LLM_GUARD_REGEX_ENGINE` / `LLM_GUARD_SECRETS_ENGINE`
     (default `llm_guard`). Unit parity green vs golden. See the spec.
```

- [ ] **Step 5: Commit docs**

```bash
git add docs/development/specs/llm-guard-native-regex-secrets-spec.md docs/development/analysis/llm-guard-replacement-evaluation.md
git commit -m "docs(llm-guard): mark native regex+secrets implemented (AIO-1)"
```

- [ ] **Step 6: Push and open the PR**

```bash
git push -u origin feat/llg04-native-regex-secrets
gh pr create --base main --head feat/llg04-native-regex-secrets \
  --title "feat(llm-guard): native regex+secrets scanners behind engine flags (AIO-1)" \
  --body "First per-scanner LLG-04 cutover. Verbatim MIT ports of llm-guard's regex/secrets (95 detect-secrets plugins vendored), behind LLM_GUARD_REGEX_ENGINE / LLM_GUARD_SECRETS_ENGINE (default llm_guard — zero behaviour change). Byte-exact parity vs golden baseline. No transformers change; llm-guard still installed. Spec: docs/development/specs/llm-guard-native-regex-secrets-spec.md"
```
Expected: PR URL printed. Confirm CI runs the full `llm_guard_svc` suite (incl. `test_engine_selection.py`) in the image.

---

## Self-Review notes

- **Spec coverage:** §3 port → Tasks 1–3; §5.1 package → Tasks 1–3; §5.2 flags → Task 4; §5.3 wiring → Task 5; §5.4 deps → Task 1; §6 validation → Tasks 2,3 (+ §6 service-level harness unchanged); §7 acceptance → Task 6; §8 rollback → flags default `llm_guard` (Tasks 4–5). Covered.
- **Type consistency:** `RegexScanner` / `SecretsScanner` / `CREDENTIAL_PATTERNS` names are consistent across Tasks 1–5; `.scan() -> tuple[str, bool, float]` matches the existing loop in `guard.py`.
- **No placeholders:** every code/edit step shows exact content; vendored files are copied (not retyped) with explicit patch edits.
