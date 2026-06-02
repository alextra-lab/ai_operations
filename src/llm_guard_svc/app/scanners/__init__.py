"""Native scanner ports for the LLG-04 migration off llm-guard.

Each scanner here is a verbatim port of the corresponding MIT-licensed
llm-guard input scanner, depending on its underlying library directly (never
llm_guard):
  * regex / secrets -> detect_secrets + presidio_anonymizer
    (spec: docs/development/specs/llm-guard-native-regex-secrets-spec.md)
  * prompt_injection / gibberish / language -> transformers + optimum.onnxruntime
    via ``_onnx_classifier`` (spec:
    docs/development/specs/llm-guard-native-onnx-classifiers-spec.md)

The ONNX classifier scanners are imported lazily by ``guard.py`` (they pull the
heavy model stack), so they are deliberately not re-exported here.
"""

from .regex_scanner import RegexScanner
from .secrets_scanner import SecretsScanner

__all__ = ["RegexScanner", "SecretsScanner"]
