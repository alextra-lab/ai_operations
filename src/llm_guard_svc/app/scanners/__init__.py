"""Native scanner ports for the LLG-04 migration off llm-guard.

Each scanner here is a verbatim port of the corresponding MIT-licensed
llm-guard input scanner, depending on detect_secrets / presidio_anonymizer
directly (never llm_guard). See
docs/development/specs/llm-guard-native-regex-secrets-spec.md.
"""
# Exports added in the secrets-scanner task once both modules exist.
