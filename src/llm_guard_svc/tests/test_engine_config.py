"""LLMGuardConfig per-scanner engine flags (LLG-04).

Since the LLG-04 finale (AIO-73) the llm-guard library is removed and ``native``
is the only engine; the flags default to ``native``. A stale ``llm_guard`` value
is still accepted by config (it is tolerated and resolves to native at scanner
build time — see ``guard._warn_if_legacy_engine``).
"""

from shared.config.loader import load_llm_guard_config

_ENGINE_VARS = [
    "LLM_GUARD_REGEX_ENGINE",
    "LLM_GUARD_SECRETS_ENGINE",
    "LLM_GUARD_PROMPT_INJECTION_ENGINE",
    "LLM_GUARD_GIBBERISH_ENGINE",
    "LLM_GUARD_LANGUAGE_ENGINE",
    "LLM_GUARD_ANONYMIZE_ENGINE",
]


def test_engine_defaults_to_native(monkeypatch):
    for var in _ENGINE_VARS:
        monkeypatch.delenv(var, raising=False)
    cfg = load_llm_guard_config()
    assert cfg.regex_engine == "native"
    assert cfg.secrets_engine == "native"
    assert cfg.prompt_injection_engine == "native"
    assert cfg.gibberish_engine == "native"
    assert cfg.language_engine == "native"
    assert cfg.anonymize_engine == "native"


def test_engine_env_override_is_preserved(monkeypatch):
    # The flag is vestigial but still round-trips through config.
    monkeypatch.setenv("LLM_GUARD_REGEX_ENGINE", "llm_guard")
    cfg = load_llm_guard_config()
    assert cfg.regex_engine == "llm_guard"


def test_pii_thresholds_have_defaults(monkeypatch):
    for var in ("LLM_GUARD_PII_SCORE_THRESHOLD", "LLM_GUARD_PII_GLINER_THRESHOLD"):
        monkeypatch.delenv(var, raising=False)
    cfg = load_llm_guard_config()
    assert cfg.pii_score_threshold == 0.4
    assert cfg.pii_gliner_threshold == 0.5
