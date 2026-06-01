"""Response schema contract for ``POST /api/validate``.

Parity is checked on *schema* first (field names / nesting / types), per the
replacement evaluation §5.2 — string equality of the whole payload is too
brittle across engines. A hand-rolled validator keeps the harness dependency
free (no ``jsonschema``).

The contract mirrors ``ValidationResponse`` in ``app/main.py`` and the
per-scanner detail shape produced by ``LLMGuard.validate_input`` in
``app/guard.py``.
"""

from __future__ import annotations

from typing import Any

# Scanners the current service runs, in declaration order (guard.py).
EXPECTED_SCANNERS: tuple[str, ...] = (
    "anonymize",
    "prompt_injection",
    "secrets",
    "gibberish",
    "language",
    "regex",
)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_response_schema(payload: Any) -> list[str]:
    """Return a list of schema violations (empty == valid).

    Accepts both response shapes:
      * **scanning** — ``details`` maps each scanner -> ``{passed, score}``
        (or an ``{error, passed, score}`` object when a scanner raised).
      * **disabled / bypass** — ``details`` is ``{status, message}`` and the
        bypass returns ``risk_score=0.0, modified=False``.
    """
    errors: list[str] = []

    if not isinstance(payload, dict):
        return [f"top-level payload must be an object, got {type(payload).__name__}"]

    # Top-level fields.
    if not isinstance(payload.get("sanitized_text"), str):
        errors.append("sanitized_text must be a string")
    if not _is_number(payload.get("risk_score")):
        errors.append("risk_score must be a number")
    elif not (0.0 <= float(payload["risk_score"]) <= 1.0):
        errors.append(f"risk_score out of [0,1]: {payload['risk_score']}")
    if not isinstance(payload.get("modified"), bool):
        errors.append("modified must be a boolean")

    details = payload.get("details")
    if not isinstance(details, dict):
        errors.append("details must be an object")
        return errors

    # Disabled / bypass shape.
    if "status" in details:
        if details.get("status") == "disabled":
            if not isinstance(details.get("message"), str):
                errors.append("disabled details must carry a string 'message'")
            return errors
        errors.append(f"unexpected details.status: {details.get('status')!r}")
        return errors

    # Scanning shape: validate each scanner entry.
    for name, result in details.items():
        if not isinstance(result, dict):
            errors.append(f"details.{name} must be an object")
            continue
        if "error" in result:
            # Scanner-failure shape from guard.py: {error, passed, score}.
            if not isinstance(result["error"], str):
                errors.append(f"details.{name}.error must be a string")
            continue
        if "passed" in result and not isinstance(result["passed"], bool):
            errors.append(f"details.{name}.passed must be a boolean")
        if "score" in result and not _is_number(result["score"]):
            errors.append(f"details.{name}.score must be a number")
        if "passed" not in result and "score" not in result:
            errors.append(f"details.{name} must carry 'passed' and/or 'score'")

    return errors


def scanner_names(payload: dict[str, Any]) -> set[str]:
    """Scanner keys present in a scanning-shape response (empty for bypass)."""
    details = payload.get("details", {})
    if not isinstance(details, dict) or "status" in details:
        return set()
    return set(details.keys())
