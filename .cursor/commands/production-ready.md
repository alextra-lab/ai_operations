# Production ready: [TASK_ID]

Make implementation production-ready. Fix issues, don't just report them.

## 1. Create Missing Tests

- Frontend: `.spec.ts` co-located (Jest, NOT Jasmine)
- Backend: `test_*.py` in `src/{service}/tests/unit/` (pytest)
- Target: >90% coverage for new code
- Unit Tests use Mocks
- Integration Tests use true connectivity (database connections)

## 2. Fix Compilation

```bash
cd src/frontend-angular && npm run build
# Backend: run per service, e.g. cd src/orchestrator && python -m py_compile ...
```

## 3. Fix Linter Issues

```bash
cd src/frontend-angular && npm run lint --fix && npm run format
# Backend: ruff/black per service, e.g. cd src/orchestrator && ruff check app/ --fix && black app/
```

## 4. Rebuild Container

```bash
export $(grep -v '^#' config/env/env.test | xargs)
docker-compose down
docker-compose build --no-cache [service-name]
docker-compose up -d
```

## 5. Verify Health

```bash
docker-compose -f deploy/docker-compose.test.yml ps
docker-compose logs [service-name]  # if unhealthy
```

## 6. Run All Tests

```bash
cd src/frontend-angular && npm test
python ops/testing/run_all_tests.py
```

## Report

```
✅ Tests: X created, Y/Y passing, Z% coverage
✅ Compilation: Clean
✅ Linting: Clean
✅ Container: [service-name] healthy
✅ All tests: Y/Y passing

READY FOR: update-plans
```
