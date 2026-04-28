# Air-Gapped Deployment Guide

This guide provides procedures for deploying AI Operations Platform in air-gapped environments where internet access is not available.

## Overview

Air-gapped deployment requires:

- Offline tokenizer bundling for all supported models
- Pre-configured pricing tiers
- Complete Docker image with all dependencies
- Python wheelhouse for backend dependencies
- npm cache for frontend dependencies
- Secure transfer procedures

## Supported Models & Tokenizers

The following models are supported in air-gapped mode:


- Mistral Small
- GPT-oss
- Llama 3.3 (Codestral/Llama)

## Deployment Procedure

### 1. Prepare Dependency Caches (Internet-Connected Machine)

Build both Python and npm dependency caches on a machine with internet access:

```bash
# Navigate to project root
cd /path/to/ai_operations

# Build Python wheelhouse (backend services)
bash ops/bootstrap/build_wheelhouse.sh

# Build npm cache (frontend)
bash ops/bootstrap/build_npm_cache_linux.sh

# Verify caches
ls -lh src/wheelhouse/ | wc -l    # Python packages
du -sh src/npm_cache/              # npm cache size
```

### 2. Prepare Tokenizer Bundle (Internet-Connected Machine)

Run the tokenizer bundling script:

```bash
# Navigate to project root
cd /path/to/ai_operations

# Run the tokenizer bundling script
bash ops/bootstrap/prepare_tokenizers.sh

# This creates a bundle file
ls -la tokenizer_bundle.tar.gz
```

### 3. Package for Transfer

Create a single archive with all dependencies:

```bash
# Create comprehensive deployment package
tar -czf aio-airgapped-deps.tar.gz \
  src/wheelhouse \
  src/npm_cache \
  tokenizer_bundle.tar.gz

# Verify package
ls -lh aio-airgapped-deps.tar.gz
```

### 4. Transfer to Air-Gapped Environment

Use secure transfer methods (USB, secure file transfer, etc.):

```bash
# On internet-connected machine
scp aio-airgapped-deps.tar.gz user@air-gapped-server:/tmp/

# Or copy to USB drive
cp aio-airgapped-deps.tar.gz /media/usb-drive/
```

### 5. Extract Dependencies (Air-Gapped Environment)

```bash
# Extract all dependencies
cd /path/to/aio
tar -xzf /tmp/aio-airgapped-deps.tar.gz

# Extract tokenizer bundle
tar -xzf tokenizer_bundle.tar.gz

# Verify extraction
ls -la src/wheelhouse/         # Python packages
ls -la src/npm_cache/          # npm cache
ls -la data/tokenizers/        # Tokenizers
```

### 6. Build Docker Images (Fully Offline)

```bash
# All Docker builds now use local caches (no internet required)
# Backend services use src/wheelhouse/
# Frontend uses src/npm_cache/

docker-compose build

# Verify builds completed offline
docker images | grep aio
```

**Build Performance:**

- Backend services: ~2-3 minutes (vs 10-15 minutes online) - **fully offline**
- Frontend: ~1-2 minutes (vs 8-10 minutes online) - **requires internet for ~2 native packages**
- **Total improvement: ~5-8x faster**

**Note**: npm cache is cross-platform for most packages, but native binaries (like `lmdb`) must be downloaded for the target platform (Linux). For truly air-gapped deployment, build the npm cache inside a Linux Docker container.

### 7. Initialize Database

```bash
# Run database migrations
docker-compose exec backend python -m alembic upgrade head

# Seed initial pricing data
docker-compose exec backend python ops/migrations/seed_pricing_tiers.py
```

### 8. Verify Deployment

```bash
# Test tokenizer functionality
docker-compose exec backend python -c "
from src.backend.app.services.context_compaction_service import ContextCompactionService
service = ContextCompactionService('mistral-large', '/app/data/tokenizers')
print('Tokenizer test:', service.count_tokens('Hello world'))
"

# Test offline operation
docker-compose exec backend python tests/integration/test_offline_tokenizers.py
```

## Configuration

### Environment Variables

Set the following environment variables for air-gapped deployment:

```bash
# .env file
AIR_GAPPED_MODE=true
TOKENIZER_PATH=/app/data/tokenizers
ENABLE_INTERNET_ACCESS=false
```

### Docker Compose Configuration

Update `docker-compose.yml` for air-gapped mode:

```yaml
services:
  backend:
    environment:
      - AIR_GAPPED_MODE=true
      - TOKENIZER_PATH=/app/data/tokenizers
    volumes:
      - ./data/tokenizers:/app/data/tokenizers:ro
```

## Troubleshooting

### Tokenizer Loading Issues

If tokenizers fail to load:

1. Check file permissions:

   ```bash
   ls -la data/tokenizers/
   ```

2. Verify file integrity:

   ```bash
   sha256sum data/tokenizers/*
   ```

3. Check logs:

   ```bash
   docker-compose logs backend | grep -i tokenizer
   ```

### Database Connection Issues

If database initialization fails:

1. Check PostgreSQL connectivity:

   ```bash
   docker-compose exec backend psql -h postgres -U aio -d aio
   ```

2. Verify migration files:

   ```bash
   ls -la ops/migrations/
   ```

### Pricing Tier Issues

If pricing tiers are not loaded:

1. Check database tables:

   ```bash
   docker-compose exec backend python -c "
   from src.backend.app.db.database import get_db
   from src.backend.app.db.models import PricingTier
   db = next(get_db())
   print('Pricing tiers:', db.query(PricingTier).count())
   "
   ```

2. Re-run seeding script:

   ```bash
   docker-compose exec backend python ops/migrations/seed_pricing_tiers.py
   ```

## Security Considerations

### File Transfer Security

- Use encrypted USB drives for file transfer
- Verify file checksums before extraction
- Use secure file transfer protocols (SFTP, SCP)
- Maintain chain of custody documentation

### Access Control

- Limit access to tokenizer files
- Use read-only mounts in Docker
- Implement proper file permissions
- Monitor file access logs

### Compliance

- Document all transfer procedures
- Maintain audit logs of file transfers
- Verify deployment integrity
- Test offline functionality before production

## Maintenance

### Adding New Models

To add new models to air-gapped deployment:

1. Update tokenizer bundle on internet-connected machine
2. Transfer new bundle to air-gapped environment
3. Extract and verify new tokenizer files
4. Update model configuration in database
5. Restart services

### Updating Pricing Tiers

Pricing tiers can be updated via the admin UI without redeployment:

1. Access admin pricing management interface
2. Update tier configurations
3. Verify changes in audit log
4. Monitor rate limit metrics

## Support

For issues with air-gapped deployment:

1. Check logs in `logs/` directory
2. Run diagnostic scripts in `ops/diagnostics/`
3. Verify all prerequisites are met
4. Contact support with deployment logs

## References

- [npm Cache Usage Guide](../development/guides/npm-cache-usage.md)
- [ADR-019: Offline Tokenizer Strategy](../development/adrs/ADR-019-Offline-Tokenizer-Strategy.md)
- [Deployment Constraints](../architecture/DEPLOYMENT_CONSTRAINTS.md)
- [Pricing Management Guide](../admin/PRICING_MANAGEMENT.md)
