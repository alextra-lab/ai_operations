"""LLMGuardConfig PII threshold defaults (LLG-04 finale).

Since the LLG-04 finale (AIO-73) the llm-guard library is removed and the
per-scanner ``*_engine`` knobs have been deleted entirely. Only the PII
threshold fields (``pii_score_threshold``, ``pii_gliner_threshold``) remain
as config-driven calibration knobs.
"""

from shared.config.loader import load_llm_guard_config


def test_pii_thresholds_have_defaults(monkeypatch):
    for var in ("LLM_GUARD_PII_SCORE_THRESHOLD", "LLM_GUARD_PII_GLINER_THRESHOLD"):
        monkeypatch.delenv(var, raising=False)
    cfg = load_llm_guard_config()
    assert cfg.pii_score_threshold == 0.3
    assert cfg.pii_gliner_threshold == 0.93
