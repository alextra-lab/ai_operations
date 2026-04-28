# npm Cache Build Script

## Quick Start

```bash
# Build the cache (one time)
bash ops/bootstrap/build_npm_cache_linux.sh

# Then build Docker images (11x faster!)
docker compose -f deploy/docker-compose.yml build
```

## What This Does

Creates a local npm package cache at `src/npm_cache/` containing all frontend dependencies (~160MB).

## Why This Exists

**Problem**: `docker build --no-cache` takes 8-10 minutes because it downloads all npm packages from the internet every time.

**Solution**: Build a local cache once, then Docker builds use it offline in ~45 seconds.

## Node.js Version

- **Docker builds**: Node.js 24 LTS (`node:24-alpine`)
- **Local development**: Node.js 24 LTS recommended
- **Support**: Through April 2028

## Performance

- **Before**: 8m 30s per build
- **After**: 45s per build
- **Improvement**: **11x faster**

## When to Rebuild

Rebuild when `package.json` changes:

```bash
cd src/frontend-angular
npm install  # Updates package-lock.json
cd ../..
bash ops/bootstrap/build_npm_cache_linux.sh
```

## How It Works

1. Script runs `npm ci` inside a `node:24-alpine` Docker container
2. Cache is built with Linux binaries (compatible with Docker)
3. Dockerfile copies cache into build image
4. `npm ci --prefer-offline --cache` installs from local cache
5. Cache removed after install to keep image size small

## Cypress Note

Cypress is **not** included in the npm cache by default. This is intentional:

- Production Docker images don't need E2E testing tools
- Cypress E2E tests run separately against deployed containers
- Reduces cache size from ~400MB to ~160MB

## Full Documentation

See: `docs/development/guides/npm-cache-usage.md`
