# Python Protocol and Typing Patterns

Guidelines for `typing.Protocol`, structural subtyping, and keeping type checkers and linters (Ruff, Pyright, mypy) aligned.

## Protocol parameter names and implementations

When a class implements a `typing.Protocol`, **parameter names matter** for structural subtyping: the type checker expects the same names so that callers can use keyword arguments (e.g. `obj.method(x=1)`). If an implementation uses a different name (e.g. `_payload` for an intentionally unused argument), the checker reports an incompatible type.

### Recommended approach: positional-only in the Protocol

For parameters that **implementations may leave unused** (e.g. no-op or stub implementations), declare them as **positional-only** in the Protocol using `/`:

- After `/`, the parameter name is not part of the contract. Implementations may use any name (e.g. `_payload`, `_evidence`).
- Callers must pass the argument by position; keyword form is not allowed for that parameter.
- Ruff’s ARG002 (unused method argument) accepts underscore-prefixed names as intentionally unused, so implementations can use `_param` without noqa.

**Example (Protocol):**

```python
from typing import Any, Protocol
from uuid import UUID

class HistoryProvider(Protocol):
    async def append(
        self, run_id: UUID, payload: dict[str, Any], /
    ) -> None:
        ...
```

**Example (implementation with intentionally unused argument):**

```python
class EdgeOnlyHistory:
    async def append(self, run_id: UUID, _payload: dict[str, Any]) -> None:
        # _payload intentionally unused; name not fixed by Protocol
        ...
```

### When to use this pattern

- No-op or stub implementations of a Protocol that must match the protocol signature but do not use every argument.
- You want to avoid `cast()` and noqa while satisfying both the type checker and Ruff.

### References

- PEP 544 (Protocols), PEP 570 (positional-only parameters).
- Type checkers: parameter names in Protocol methods are part of the contract unless the parameter is positional-only.
- Ruff: ARG002 exempts names matching `dummy-variable-rgx` (e.g. leading underscore).
