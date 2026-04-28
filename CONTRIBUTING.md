# Contributing to the AI Operations Platform

Thanks for your interest in contributing. This document describes the
development workflow, coding standards, and how to submit changes.

By participating in this project you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Quick links

- [Project README](README.md) — project overview and quick start.
- [Architecture documentation](docs/architecture/) — system design.
- [Developer Guide](docs/development/guidelines/Developer_Guide.md) — deeper
  development reference.
- [Testing Guide](docs/testing/TESTING_GUIDE.md) — how to run and write tests.
- [Documentation Organization](docs/development/guidelines/) — where new docs
  belong.

## Ways to contribute

- **Bug reports** — please use the
  [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include the
  exact reproduction steps, expected vs. actual behaviour, and your
  environment.
- **Feature requests** — please use the
  [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).
  Describe the problem first, then propose a solution.
- **Pull requests** — see the workflow below.
- **Documentation** — improvements to existing docs are very welcome.

## Development setup

The project targets **Python 3.12** and **Angular 21** (Node 24).

```bash
# 1. Clone
git clone https://github.com/alextra-lab/ai_operations.git
cd ai_operations

# 2. Python virtual environment
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements-all.txt
pip install -e ".[dev]"

# 3. Pre-commit hooks (Python)
pre-commit install

# 4. Frontend dependencies (also installs Husky pre-commit hooks)
cd src/frontend-angular
npm install
cd ../..

# 5. Environment variables
cp config/env/env.template config/env/.env
# Edit config/env/.env with your values, then:
export $(grep -v '^#' config/env/.env | xargs)

# 6. Verify configuration
python ops/validate_configuration.py

# 7. Start the stack (requires the external observability network)
docker network create observability   # one-time
docker compose -f deploy/docker-compose.yml up
```

## Coding standards

### Python

- **Style**: PEP 8 enforced by [Ruff](pyproject.toml) and [Black]
  (`line-length = 100`, `target-version = py312`).
- **Type hints**: mandatory for all public functions, methods, and class
  attributes. Type-checking is enforced by `mypy` (configuration in
  [`mypy.ini`](mypy.ini)).
- **Docstrings**: required for all public modules, classes, and functions
  (PEP 257). Use one-line summaries for trivial cases; multi-line with
  `Args` / `Returns` / `Raises` for non-obvious APIs.
- **Logging**: use the structured logger from `shared.logging_utils`. Log
  identifiers (request IDs, user IDs) — **never** request bodies, response
  bodies, prompts, or full credentials. See
  [ADR-048: Secure Logging Redaction](docs/development/adrs/ADR-048-Secure-Logging-Redaction.md).
- **Imports**: absolute, e.g. `from src.{service}.app.X import Y`.

### TypeScript / Angular

- **Style**: enforced by [`.eslintrc.json`](.eslintrc.json) and
  [`.prettierrc`](.prettierrc).
- **JSDoc / TSDoc**: required on services, public component methods, and
  exported symbols.
- **Components**: prefer `OnPush` change detection; lazy-load feature modules.

### File layout

| Layer    | Pattern                                               |
|----------|-------------------------------------------------------|
| Frontend | `src/frontend-angular/src/app/{pages,components}/...` |
| Backend  | `src/{service}/app/{module}/...`                      |
| Shared   | `src/shared/{auth,config,logging_utils,...}/...`      |
| Tests    | `src/{service}/tests/{unit,integration}/...`          |
| Cross-service tests | `tests/{integration,e2e,fixtures}/...`     |
| Operations | `ops/{bootstrap,ci,cli,database,operations,testing}/...` |

## Testing

- **Run all tests:** `python ops/testing/run_all_tests.py`
- **Service tests:** `python ops/testing/run_service_tests.py <service>` or
  `bash src/<service>/run_tests.sh`
- **Integration:** `pytest tests/integration/`
- **End-to-end:** `pytest tests/e2e/`
- **Coverage target:** 80%+ for critical components.

When adding a feature or fixing a bug, include unit tests in the same PR.
Mock external dependencies (HTTP calls, the database, the vector store) so
tests stay deterministic.

## Pull request workflow

1. **Fork** the repository and create a feature branch from `main`:
   `git checkout -b feat/short-description`.
2. **Write tests first** when fixing a bug or adding behaviour.
3. **Run the full pre-commit suite locally** before pushing:
   `pre-commit run --all-files`.
4. **Open a PR** using the
   [PR template](.github/PULL_REQUEST_TEMPLATE.md).
   Reference any related issue (e.g. `Fixes #123`).
5. **Keep PRs focused.** One logical change per PR makes review faster and
   safer to merge.
6. **CI must pass.** Lint, type-check, and tests run on every push.

### Branch naming

| Type           | Prefix      |
|----------------|-------------|
| Feature        | `feat/`     |
| Bug fix        | `fix/`      |
| Documentation  | `docs/`     |
| Refactor       | `refactor/` |
| Tests          | `test/`     |
| Chore / build  | `chore/`    |

### Commit messages

Conventional Commits style is preferred but not enforced:

```
type(scope): short summary

Optional longer description that explains the why, not the what.
```

## Security

If you discover a security vulnerability, please follow
[`SECURITY.md`](SECURITY.md) — do not open a public issue.

## Questions

Open a GitHub Discussion or a low-priority issue. We aim to respond within a
few business days.
