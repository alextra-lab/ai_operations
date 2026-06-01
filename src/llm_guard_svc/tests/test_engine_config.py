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
