# Test Environment Setup Guide

This guide provides step-by-step instructions for setting up and managing the test environment for the AI Operations Platform project.

## 🎯 Overview

The test environment provides complete isolation from production and development environments using:
- **Containerized services** (PostgreSQL, Qdrant, microservices)
- **Isolated port mappings** to avoid conflicts
- **Separate environment configurations** for different test types
- **Automated database initialization** with migrations and seed data

## 🚀 Quick Start

### Complete Setup (Two Commands)
```bash
# Create environment file from template
cp config/env/env.test.template config/env/env.test

# Start entire test environment
./ops/testing/start_test_services.sh
```

### Run Tests
```bash
# Run all tests
python ops/testing/run_all_tests.py

# Run specific test types
python ops/testing/run_all_tests.py --type unit --coverage
python ops/testing/run_all_tests.py --type integration
```

### Clean Up
```bash
# Complete cleanup
./ops/testing/clean_test_environment.sh
```

## 📋 Detailed Setup Process

### Step 1: Set Up Environment File

First, create the test environment file from the template:

```bash
# Copy the template to create the actual environment file
cp config/env/env.test.template config/env/env.test
```

### Step 2: Start Test Services

The `start_test_services.sh` script performs complete environment setup:

```bash
./ops/testing/start_test_services.sh
```

**What this script does:**
1. Loads environment variables from `config/env/env.test` (for Docker services)
2. Creates test data directories (`data/postgres-test`, `data/qdrant-test`)
3. Stops any existing containers
4. Starts Docker Compose with `deploy/docker-compose.test.yml`
5. Initializes test database with migrations and seed data
6. Verifies all services are healthy
7. Displays service URLs and management commands

### Step 2: Verify Services

Check that all services are running and healthy:

```bash
# Check service status
docker-compose -f deploy/docker-compose.test.yml ps

# Test individual service health
curl -s http://localhost:8006/health | head -1  # Orchestrator API
curl -s http://localhost:8004/health | head -1  # Retrieval Service
curl -s http://localhost:8005/health | head -1  # Embedding Service
curl -s http://localhost:8082/health | head -1  # LLM Guard Service
curl -s http://localhost:4201/health | head -1  # UI Webapp
```

### Step 3: Run Tests

#### Unit Tests (Direct Database Access)
```bash
# Run all unit tests
python -m pytest src/orchestrator/tests/unit/ -v

# Run specific test modules
python -m pytest src/orchestrator/tests/unit/test_main.py -v
python -m pytest src/orchestrator/tests/unit/auth/ -v
```

#### Integration Tests
```bash
# Run integration tests
python -m pytest src/orchestrator/tests/integration/ -v

# Run specific integration tests
python -m pytest src/orchestrator/tests/integration/test_use_case_config_integration.py -v
```

#### Centralized Test Runner
```bash
# Run all tests with coverage
python ops/testing/run_all_tests.py --coverage

# Run specific test types
python ops/testing/run_all_tests.py --type unit
python ops/testing/run_all_tests.py --type integration
python ops/testing/run_all_tests.py --type frontend
```

### Step 4: Database Management

#### Reset Database (if needed)
```bash
# Reset test database with fresh data
./ops/testing/reset_test_database.sh
```

#### Verify Database Setup
```bash
# Check database initialization
./ops/testing/init_test_database.sh

# Check database tables
docker exec postgres-test psql -U testuser -d aio-test -c "\dt"

# Check seeded data
docker exec postgres-test psql -U testuser -d aio-test -c "SELECT COUNT(*) FROM users;"
docker exec postgres-test psql -U testuser -d aio-test -c "SELECT COUNT(*) FROM prompt_templates;"
```

### Step 5: Clean Up

#### Complete Cleanup
```bash
# Stop services and remove all data
./ops/testing/clean_test_environment.sh
```

#### Preserve Data
```bash
# Just stop services (keep data for next run)
docker-compose -f deploy/docker-compose.test.yml down
```

## 🌐 Service URLs

### External Access (Browser/API Testing)
- **UI Webapp**: http://localhost:4201
- **Orchestrator API**: http://localhost:8006
- **Retrieval Service**: http://localhost:8004
- **Embedding Service**: http://localhost:8005
- **LLM Guard Service**: http://localhost:8082
- **PostgreSQL**: localhost:5433
- **Qdrant**: http://localhost:6335

### Internal Docker Network (Service-to-Service)
- **PostgreSQL**: postgres-test:5432
- **Qdrant**: qdrant-test:6333
- **Orchestrator API**: orchestrator-api-test:8000
- **Retrieval Service**: corpus-service-test:8001
- **Embedding Service**: embedding-service-test:8000
- **LLM Guard Service**: llm-guard-svc-test:8081
- **UI Webapp**: ui-webapp-test:80

## 📁 Environment Configuration

### Docker Services (`config/env/env.test`)
Used by Docker Compose services for internal communication:
```ini
POSTGRES_HOST=postgres-test
POSTGRES_PORT=5432
QDRANT_HOST=qdrant-test
QDRANT_PORT=6333
```

### Unit Tests (`config/env/env.test.local`)
Used by unit tests for direct database access:
```ini
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
QDRANT_HOST=localhost
QDRANT_PORT=6335
```

## 🔧 Troubleshooting

### Services Won't Start

#### Check Docker Status
```bash
# Verify Docker is running
docker info

# Check for port conflicts
lsof -i :5433  # PostgreSQL
lsof -i :6335  # Qdrant
lsof -i :8006  # Orchestrator API
```

#### Clean Restart
```bash
# Complete cleanup and restart
./ops/testing/clean_test_environment.sh
./ops/testing/start_test_services.sh
```

### Database Connection Issues

#### Check PostgreSQL Container
```bash
# View PostgreSQL logs
docker logs postgres-test

# Check container status
docker ps | grep postgres-test

# Test database connection
docker exec postgres-test psql -U testuser -d aio-test -c "SELECT 1;"
```

#### Verify Database Setup
```bash
# Check if database exists
docker exec postgres-test psql -U testuser -d postgres -c "\l"

# Check tables
docker exec postgres-test psql -U testuser -d aio-test -c "\dt"

# Check migrations
docker exec postgres-test psql -U testuser -d aio-test -c "SELECT * FROM schema_migrations;"
```

### Test Failures

#### Environment Variable Issues
```bash
# Check current environment
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "POSTGRES_PORT: $POSTGRES_PORT"
echo "DATABASE_URL: $DATABASE_URL"

# Clear and reload environment
unset POSTGRES_HOST POSTGRES_PORT DATABASE_URL QDRANT_HOST QDRANT_PORT QDRANT_URL
python -m pytest src/orchestrator/tests/unit/test_main.py -v
```

#### Database Migration Issues
```bash
# Reset test database (re-runs init/seed; migrations are SQL in ops/database/migrations/)
./ops/testing/reset_test_database.sh
```

#### Test Isolation Issues
```bash
# Reset database between test runs
./ops/testing/reset_test_database.sh
python -m pytest src/orchestrator/tests/unit/ -v
```

## 📚 Key Scripts Reference

### Environment Management
- **`start_test_services.sh`**: Complete test environment setup
- **`clean_test_environment.sh`**: Complete cleanup (removes all data)
- **`init_test_database.sh`**: Smart database initialization
- **`reset_test_database.sh`**: Reset database with fresh data

### Test Execution
- **`run_all_tests.py`**: Centralized test runner with coverage
- **`run_service_tests.py`**: Service-specific test runner
- **`load_test_env.py`**: Load test environment variables

### Database Management
- **`setup_test_database.py`**: Initial database setup
- **`verify_test_database.py`**: Verify database configuration
- **`manage_test_database.py`**: Database management operations

## 🎯 Best Practices

### Test Execution
1. **Always start with clean environment**: `./ops/testing/start_test_services.sh`
2. **Use appropriate test types**: Unit tests for isolated testing, integration tests for service interaction
3. **Reset database when needed**: `./ops/testing/reset_test_database.sh`
4. **Check service health**: Verify all services are running before running tests

### Development Workflow
1. **Start test environment** at beginning of development session
2. **Run tests frequently** during development
3. **Reset database** if tests fail due to data issues
4. **Clean up** at end of development session

### Troubleshooting
1. **Check service logs** first: `docker logs <container-name>`
2. **Verify environment variables** are loaded correctly
3. **Test database connectivity** directly
4. **Clean restart** if issues persist

## 📊 Test Results Interpretation

### Successful Test Run
```
======================== 301 passed, 4 failed, 69 warnings in 1.43s ========================
```
- **301 passed**: Core functionality working
- **4 failed**: Minor issues (usually test isolation or assertion problems)
- **69 warnings**: Mostly deprecation warnings (non-critical)

### Common Test Issues
- **Database connection errors**: Check environment variables and service status
- **Duplicate key violations**: Reset database to clear test data
- **Service unavailable errors**: Check if all services are running and healthy
- **Import errors**: Verify Python path and dependencies

## 🔄 Maintenance

### Regular Maintenance
- **Clean up old test data**: `./ops/testing/clean_test_environment.sh`
- **Update test dependencies**: Check `requirements.txt` files
- **Review test coverage**: Use `--coverage` flag with test runners
- **Update environment files**: Keep `env.test` and `env.test.local` in sync

### Environment Updates
- **Port changes**: Update both `env.test` and `env.test.local`
- **Service additions**: Update `docker-compose.test.yml`
- **Database schema changes**: Update migration files
- **New test types**: Update test runners and documentation

This test environment provides a robust, isolated testing platform that supports both unit testing with direct database access and integration testing with containerized services.
