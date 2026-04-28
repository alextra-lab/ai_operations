---
name: backend-standards
description: Python and FastAPI standards for AI Operations backend services. Use when editing src/backend, src/retrieval, or any **/*.py outside frontend or tests.
---

# Backend Standards (Python / FastAPI)

Apply these when working on backend code in this project.

## When to Use

- Editing files under `src/backend/`, `src/retrieval/`, or other Python services
- Adding or changing API routes, services, or database access
- Writing or updating backend tests

## Language and Style

- **Python 3.12** only; use 3.12 syntax and features
- **Type hints mandatory** for all function signatures, parameters, return types, and class attributes
- **PEP 8** with **Black** and **Ruff** formatting
- **Modular design**; keep reusable logic in shared modules under `src/{service}/app/`

## Documentation (Docstrings)

- **Modules:** One-line or short docstring describing the module’s purpose.
- **Classes:** Docstring describing responsibility; document public methods.
- **Functions:** Docstring for all public functions (summary; use Args/Returns/Raises for non-obvious parameters or behavior).
- Follow **PEP 257**; prefer one-line for simple cases, multi-line for complex APIs.

## Layout

- Backend code: `src/{service}/app/{module}` (e.g. `src/backend/app/routers/`, `src/backend/app/services/`)
- Tests: `src/<service>/tests/unit/` and `src/<service>/tests/integration/`; cross-service: `tests/integration/`
- Use **absolute imports**: `from src.{service}.app.X import Y`

## Logging and Errors

- Use **structured JSON logging** with context: request IDs, user info, module/function names
- Do not log secrets, tokens, or full request/response bodies
- Implement error handling that does not leak sensitive information

## Security

- **Never** read or modify `.env`, `**/config/secrets.*`, or any file with credentials
- **Validate input** on all external-facing APIs
- Use **LLM-Guard** for external-facing LLM or user-content APIs where required by project
- No hardcoded API keys or passwords

## Testing

- Unit tests: `test_*.py` or `*_test.py` in `src/<service>/tests/unit/`; use mocks for external deps
- Integration: `tests/integration/` or service `tests/integration/`; real DB/HTTP where appropriate
- Run tests: `python ops/testing/run_all_tests.py` or `python ops/testing/run_service_tests.py <service>`
- Target **80%+ coverage** for critical paths; test Pydantic validation and edge cases

## Database and Migrations

- **UUID-based schema** for entities
- Migrations: sequential numbering (001, 002, …); review before running; preserve backward compatibility when possible

## Protocols and typing

- **`typing.Protocol`**: For parameters that implementations may leave unused, declare them **positional-only** in the Protocol (e.g. `def method(self, x: T, /) -> None`). Implementations can then use underscore-prefixed names (e.g. `_x`) so Ruff ARG002 does not flag them and the type checker accepts the implementation. See `docs/development/guidelines/PYTHON_PROTOCOL_PATTERNS.md`.
