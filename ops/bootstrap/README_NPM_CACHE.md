# npm Cache Build Script

## Node.js Version

- **Docker builds**: Node.js 24 LTS (`node:24-alpine`)
- **Local development**: Node.js 24 LTS recommended
- **Support**: Through April 2028

## Quick Reference

```bash
# Build cache (recommended - fast mode)
bash ops/bootstrap/build_npm_cache_linux.sh
```

## Why Fast Mode Only (No Cypress)

**Cypress is intentionally excluded** from the Docker build cache:

1. **Production images should be lean** - No test tools in production
2. **Proper CI/CD flow** - Tests run BEFORE building the Docker image
3. **E2E tests run externally** - Cypress tests the deployed container, not inside it

### Correct Testing Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Lint &    │ →  │    Unit     │ →  │   Build     │ →  │   E2E       │
│   Type Check│    │    Tests    │    │   Docker    │    │   Tests     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     Node 24           Node 24          node:24-alpine      Cypress vs
   (local/CI)        (local/CI)        (production)      running container
```

### Where Tests Run

| Test Type | Environment | Tool |
|-----------|-------------|------|
| Linting | Local / CI (Node 24) | ESLint |
| Unit Tests | Local / CI (Node 24) | Jest |
| Build | Docker (`node:24-alpine`) | Angular CLI |
| E2E Tests | CI (against container) | Cypress |

## Cache Details

- **Time**: ~2-3 minutes to build
- **Size**: ~160MB
- **Includes**: All npm packages + native Linux binaries
- **Excludes**: Cypress binary (not needed in production)

## Performance Comparison

| Scenario | Time | Downloads | Notes |
|----------|------|-----------|-------|
| No cache | 8-10 min | ~800MB | Full download |
| With cache | 1-2 min | ~10-20MB | Native binaries only |

## When to Rebuild Cache

Rebuild when `package.json` or `package-lock.json` changes:

```bash
bash ops/bootstrap/build_npm_cache_linux.sh
```

## Documentation

Full guide: `docs/development/guides/npm-cache-usage.md`
