# Data Volume Structure

## Overview

This document outlines the data storage approach used in the AI Operations Platform project, detailing how persistent data is managed for PostgreSQL and Qdrant databases.

## Directory Structure

The project uses bind mounted volumes for database persistence, with the following structure:

```
project_root/
├── data/
│   ├── postgres/      # PostgreSQL data files
│   ├── qdrant/        # Qdrant vector database files
│   ├── postgres_backup/ # PostgreSQL backups
│   └── qdrant_backup/   # Qdrant backups
```

## Bind Mounted Volumes

The project uses bind mounted volumes instead of Docker named volumes for the following advantages:

- Direct access to data files for inspection and backup
- Clear visibility of data usage within project structure
- Easier integration with host-based backup tools
- Simplified data management across environments

## Backup and Recovery

Regular backups should be implemented for:

- PostgreSQL: Create a pg_dump of the database
- Qdrant: Create a tar archive of the data directory

Recommended backup storage locations:

- PostgreSQL: `data/postgres_backup/`
- Qdrant: `data/qdrant_backup/`

## Docker Compose Configuration

The docker-compose.yml maps these directories as bind mounts:

```yaml
# PostgreSQL
volumes:
  - ./data/postgres:/var/lib/postgresql/data

# Qdrant
volumes:
  - ./data/qdrant:/qdrant/storage
```

## Permissions

- PostgreSQL data directory requires specific permissions (owner: 999:999, mode: 700)
- These should be set before starting the containers

## Data Management

When working with the bind mounted volumes:

- Ensure proper permissions before starting containers
- Back up data regularly using Docker utilities or direct file system operations
- When upgrading, make sure to preserve the data directories

## Maintenance Guidelines

- Implement regular backup procedures for both databases
- When deploying to new environments, ensure the data directories exist with proper permissions
- Monitor disk space usage in the data directories
- Consider implementing automated health checks for the database services
