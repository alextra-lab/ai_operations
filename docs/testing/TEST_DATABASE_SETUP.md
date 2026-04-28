# Test Database Setup Guide

This guide explains how to set up and manage the test database for the AI Operations Platform application.

## Overview

The test database setup uses a local PostgreSQL instance running on `localhost:5432` with the user `aio` and database name `aio-test`. This setup is designed for local development and testing.

## Test Environment Configuration

The project uses a dedicated test environment file (`config/env/env.test`) that contains all the necessary environment variables for testing. This file is separate from the main `.env` file to avoid conflicts between test and production configurations.

### Key Test Environment Variables

- **Database**: `aio-test` on `localhost:5432`
- **User**: `testuser` with password `test_password_123`
- **JWT Secret**: `test_jwt_secret_for_testing_only_32_chars`
- **Logging**: Debug level enabled
- **External Services**: Disabled or mocked where possible

The test environment file is automatically loaded by test scripts and runners.

## Prerequisites

1. **PostgreSQL Server**: Ensure PostgreSQL is running on your local machine
   ```bash
   # Check if PostgreSQL is running
   brew services list | grep postgresql

   # Start PostgreSQL if needed
   brew services start postgresql
   ```

2. **Database Access**: Ensure the `aio` user has permission to create databases
   ```sql
   -- Connect to PostgreSQL as superuser and grant permissions
   psql -U postgres
   GRANT CREATEDB TO "aio";
   ```

3. **Python Dependencies**: Ensure all required Python packages are installed
   ```bash
   pip install -r requirements-all.txt
   ```

## Quick Start

### 1. Set Up Test Database

Run the comprehensive setup script:

```bash
python ops/testing/setup_test_database.py
```

This will:
- Create the `aio-test` database
- Run all database migrations
- Verify the setup
- Create a test environment file (`.env.test`)

### 2. Verify Setup

Check that everything is working:

```bash
python ops/testing/verify_test_database.py
```

### 3. Run Tests

Execute the test suite:

```bash
# Run all tests
python ops/testing/run_all_tests.py

# Run specific service tests
python ops/testing/run_service_tests.py backend
python ops/testing/run_service_tests.py retrieval
```

## Database Management Commands

The `manage_test_database.py` script provides comprehensive database management:

### Setup Commands

```bash
# Set up database from scratch
python ops/testing/manage_test_database.py setup

# Reset database (drop, recreate, migrate)
python ops/testing/manage_test_database.py reset

# Verify database health
python ops/testing/manage_test_database.py verify
```

### Status and Maintenance

```bash
# Check database status
python ops/testing/manage_test_database.py status

# Clean up test data (keep structure)
python ops/testing/manage_test_database.py cleanup

# Drop database completely
python ops/testing/manage_test_database.py drop
```

## Configuration

### Environment Variables

The test setup uses these environment variables:

```bash
POSTGRES_USER=aio
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aio-test
TESTING=true
```

### Database Schema

The test database includes these tables:

- **Authentication**: `users`, `refresh_tokens`, `user_roles`
- **Document Management**: `documents`, `usage_stats`
- **Use Cases**: `use_cases`, `user_use_case_assignments`
- **Templates**: `prompt_templates`
- **Security**: `encryption_keys`, `audit_logs`

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   ❌ Failed to connect to PostgreSQL: connection refused
   ```
   **Solution**: Start PostgreSQL service
   ```bash
   brew services start postgresql
   ```

2. **Permission Denied**
   ```
   ❌ Failed to create database: permission denied
   ```
   **Solution**: Grant database creation permissions
   ```sql
   psql -U postgres
   GRANT CREATEDB TO "aio";
   ```

3. **Database Already Exists**
   ```
   ℹ️  Database already exists
   ```
   **Solution**: Use `--recreate` flag or reset command
   ```bash
   python ops/testing/setup_test_database.py --recreate
   python ops/testing/manage_test_database.py reset
   ```

4. **Migration Failures**
   ```
   ❌ Migration failed: relation "users" already exists
   ```
   **Solution**: Reset the database to start fresh
   ```bash
   python ops/testing/manage_test_database.py reset
   ```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python ops/testing/manage_test_database.py status --verbose
```

## Test Environment Files

The setup creates a `.env.test` file with test-specific configuration:

```bash
# Test Database Configuration
POSTGRES_USER=aio
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=aio-test
TESTING=true
DEVELOPMENT=false
OPENAI_API_KEY=test_key_for_testing
LOG_LEVEL=INFO
```

## Integration with Test Runners

All test runners have been updated to use the new test database configuration:

- `ops/testing/run_all_tests.py` - Centralized test runner
- `ops/testing/run_service_tests.py` - Service-specific tests
- `ops/run_retrieval_tests.py` - Retrieval service tests

## Best Practices

1. **Always verify setup** before running tests
2. **Use cleanup command** to reset test data between test runs
3. **Check status** if tests are failing unexpectedly
4. **Reset database** if you encounter schema issues
5. **Keep test data minimal** to avoid test interdependencies

## Manual Database Operations

If you need to perform manual operations on the test database:

```bash
# Connect to test database
psql -U aio -d aio-test

# List tables
\dt

# Check table structure
\d users

# View sample data
SELECT * FROM users LIMIT 5;

# Exit
\q
```

## Support

If you encounter issues not covered in this guide:

1. Check the logs for detailed error messages
2. Verify PostgreSQL is running and accessible
3. Ensure the `aio` user has proper permissions
4. Try resetting the database with `manage_test_database.py reset`
5. Check the main project documentation for additional troubleshooting steps
