# npm Cache Usage Guide

## Overview

The npm cache provides a local package repository for the Angular frontend, similar to Python's wheelhouse. This dramatically speeds up Docker builds, especially when using `docker build --no-cache`.

## Node.js Version

| Environment | Version | Image |
|-------------|---------|-------|
| Docker builds | Node.js 24 LTS | `node:24-alpine` |
| npm cache build | Node.js 24 LTS | `node:24-alpine` (in Docker) |
| Local development | Node.js 24 LTS | Recommended |
| Support | Through April 2028 | Active LTS |

## Benefits

- **Faster builds**: No network downloads during Docker builds
- **Offline capability**: Build images without internet access
- **Consistent builds**: Same package versions every time
- **Bandwidth savings**: Download packages once, use many times

## Usage

### 1. Build the npm Cache

On a machine with internet access:

```bash
# Build the cache (downloads all npm packages inside node:24-alpine container)
bash ops/bootstrap/build_npm_cache_linux.sh
```

This creates `src/npm_cache/` containing all frontend dependencies (~160MB).

### 2. Build Docker Image

The Dockerfile automatically uses the cache if present:

```bash
# Fast build using cache (no network access needed)
docker build --no-cache -t aio-frontend:latest src/frontend-angular
```

**Build time comparison:**

- Without cache: ~8-10 minutes (downloads all packages)
- With cache: ~1-2 minutes (uses cache for most packages)

**Note**: Cache is built inside a `node:24-alpine` Docker container to ensure Linux binary compatibility. This eliminates cross-platform issues between macOS/Windows development machines and Linux Docker builds.

### 3. Update the Cache

When `package.json` or `package-lock.json` changes:

```bash
# Rebuild cache with new dependencies
bash ops/bootstrap/build_npm_cache_linux.sh
```

## Air-Gapped Deployment

For deploying to air-gapped environments:

### Step 1: Prepare on Internet-Connected Machine

```bash
# Build both Python and npm caches
bash ops/bootstrap/build_wheelhouse.sh           # Python dependencies
bash ops/bootstrap/build_npm_cache_linux.sh      # npm dependencies

# Verify cache contents
ls -lh src/wheelhouse/
ls -lh src/npm_cache/

# Create deployment archive
tar -czf aio-deps.tar.gz src/wheelhouse src/npm_cache
```

### Step 2: Transfer to Air-Gapped Environment

```bash
# Copy archive to air-gapped server
scp aio-deps.tar.gz user@airgapped-server:/tmp/

# Or use USB drive
cp aio-deps.tar.gz /media/usb-drive/
```

### Step 3: Deploy on Air-Gapped Server

```bash
# Extract caches
cd /path/to/aio
tar -xzf /tmp/aio-deps.tar.gz

# Build all images (fully offline)
docker-compose build
```

## Cache Directory Structure

```
src/npm_cache/
├── _cacache/           # npm's internal cache format
│   ├── content-v2/     # Package tarballs
│   ├── index-v5/       # Package metadata
│   └── tmp/            # Temporary files
└── _logs/              # npm operation logs
```

## Cypress and E2E Testing

**Cypress is intentionally excluded** from the npm cache. This follows CI/CD best practices:

1. **Production images should be lean** - No test tools in production Docker images
2. **Tests run before Docker build** - Unit tests and linting validate code first
3. **E2E tests run externally** - Cypress tests the deployed container, not inside it

### Recommended Testing Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Lint &    │ →  │    Unit     │ →  │   Build     │ →  │   E2E       │
│   Type Check│    │    Tests    │    │   Docker    │    │   Tests     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     Node 24           Node 24          node:24-alpine      Cypress vs
   (local/CI)        (local/CI)        (production)      running container
```

### Test Environment Summary

| Test Type | Where | Node Version |
|-----------|-------|--------------|
| Linting | Local / CI | Node 24 |
| Unit Tests (Jest) | Local / CI | Node 24 |
| Docker Build | Container | node:24-alpine |
| E2E Tests | CI | Cypress against running container |

## Troubleshooting

### Cache Not Being Used

If Docker builds still download packages:

1. **Check cache exists:**

   ```bash
   ls -la src/npm_cache/
   ```

2. **Verify COPY path in Dockerfile:**

   ```dockerfile
   COPY ../../npm_cache /app/npm_cache
   ```

3. **Check Docker build context:**

   ```bash
   # Build from frontend directory
   docker build -f src/frontend-angular/Dockerfile .
   ```

### Cache Size Too Large

The cache typically uses 200-500 MB:

```bash
# Check cache size
du -sh src/npm_cache/

# Clean old cache entries (if needed)
npm cache clean --force
bash ops/bootstrap/build_npm_cache_linux.sh
```

### Corrupted Cache

If you see cache errors:

```bash
# Delete and rebuild
rm -rf src/npm_cache
bash ops/bootstrap/build_npm_cache_linux.sh
```

## Comparison: npm Cache vs Python Wheelhouse

| Aspect | Python Wheelhouse | npm Cache |
|--------|------------------|-----------|
| Location | `src/wheelhouse/` | `src/npm_cache/` |
| Format | `.whl` files | npm cache format |
| Build script | `ops/bootstrap/build_wheelhouse.sh` | `ops/bootstrap/build_npm_cache_linux.sh` |
| Install flag | `--no-index --find-links` | `--prefer-offline --cache` |
| Typical size | 1-2 GB | ~160 MB |

## Maintenance

### Regular Updates

Update caches when dependencies change:

```bash
# When package.json/requirements.txt change
bash ops/bootstrap/build_wheelhouse.sh
bash ops/bootstrap/build_npm_cache_linux.sh
```

### CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/build.yml
- name: Build dependency caches
  run: |
    bash ops/bootstrap/build_wheelhouse.sh
    bash ops/bootstrap/build_npm_cache_linux.sh

- name: Build Docker images
  run: docker-compose build
```

## Performance Metrics

Real-world measurements from development:

| Operation | Without Cache | With Cache | Improvement |
|-----------|--------------|------------|-------------|
| `docker build --no-cache` | 8m 30s | 1-2m | **5-8x faster** |
| Bandwidth used | ~400 MB | ~10-20 MB | **95% savings** |
| Packages from cache | 0/87 | ~85/87 | **98% cached** |

## Security Considerations

- **Cache integrity**: npm cache includes checksums
- **No credentials**: Cache contains only public packages
- **Gitignored**: Cache not committed to repository (in `.gitignore`)
- **Transfer security**: Use encrypted channels for air-gapped transfer

## References

- [npm cache documentation](https://docs.npmjs.com/cli/v11/commands/npm-cache)
- [Node.js Release Schedule](https://nodejs.org/en/about/releases/)
- [Air-Gapped Deployment Guide](../../operations/AIR_GAPPED_DEPLOYMENT.md)
- [Python Wheelhouse Build Script](../../../ops/bootstrap/build_wheelhouse.sh)

## Support

For issues with npm cache:

1. Check this guide's troubleshooting section
2. Review Docker build logs: `docker build --progress=plain`
3. Verify package.json and package-lock.json are in sync
4. Rebuild cache from scratch if needed
