# Port Management Reference

This document clearly defines which ports are used for different environments and use cases to avoid confusion.

## Overview

The system uses two distinct port configurations:

- **Production/Development Environment**: Standard ports for normal operation
- **Test Environment**: Isolated ports to prevent conflicts during testing

All port mappings follow the format: `host_port:container_port` (e.g., `5433:5432`)

## Key Rules

1. **Internal Docker network** uses container names and internal ports for service-to-service communication
2. **External access** uses localhost with mapped ports for:
   - UI access (browser)
   - Database migrations (psql, Python scripts)
   - Unit tests (direct database access)
   - API testing (curl, Postman)
3. **No default values** - all ports must be explicitly configured
4. **Test ports** are completely isolated from non-test ports to avoid conflicts
5. **Port mapping format**: `host_port:container_port` (e.g., `5433:5432`)

## Quick Reference Table

### External Host Access Ports

| Service | Production Port | Test Port | Source Code Location | Notes |
|---------|----------------|-----------|---------------------|-------|
| **Corpus Service** | `localhost:8003` | `localhost:8004` | `src/corpus_svc/` | API testing |
| **Embedding Service** | `localhost:8002` | `localhost:8005` | `src/embedding/` | API testing |
| **LLM Guard Service** | `localhost:8081` | `localhost:8082` | `src/llm_guard_svc/` | API testing |
| **Orchestrator API** | `localhost:8000` | `localhost:8006` | `src/orchestrator/` | API testing |
| **Inference Gateway** | `localhost:8008` | `localhost:8007` | `src/inference-gateway/` | API testing (P2-T4) |
| **PostgreSQL** | `localhost:5532` | `localhost:5433` | External service | Database migrations & unit tests |
| **Qdrant gRPC** | `localhost:6334` | `localhost:6336` | External service | Vector database gRPC API |
| **Qdrant REST** | `localhost:6333` | `localhost:6335` | External service | Vector database REST API |
| **Redis** | `localhost:6379` | `localhost:6380` | External service | Cache & rate limiting (P2-T4) |
| **UI Webapp** | `localhost:4200` | `localhost:4201` | `src/frontend-angular/` | Browser access |

### Internal Docker Network Ports

| Service | Production Container | Test Container | Internal Port | Source Code Location | Notes |
|---------|---------------------|----------------|---------------|---------------------|-------|
| **Corpus Service** | `corpus-service:8001` | `corpus-service-test:8001` | `8001` | `src/corpus_svc/` | Document retrieval |
| **Embedding Service** | `embedding-service:8000` | `embedding-service-test:8000` | `8000` | `src/embedding/` | Text embedding |
| **LLM Guard Service** | `llm-guard-svc:8081` | `llm-guard-svc-test:8081` | `8081` | `src/llm_guard_svc/` | Security filtering |
| **Orchestrator API** | `orchestrator-api:8000` | `orchestrator-api-test:8000` | `8000` | `src/orchestrator/` | Main API service |
| **Inference Gateway** | `inference-gateway:8002` | `inference-gateway-test:8002` | `8002` | `src/inference-gateway/` | LLM provider access (P2-T4) |
| **PostgreSQL** | `postgres-db:5432` | `postgres-test:5432` | `5432` | External service | Database |
| **Qdrant gRPC** | `vector-db:6334` | `qdrant-test:6334` | `6334` | External service | Vector database gRPC |
| **Qdrant REST** | `vector-db:6333` | `qdrant-test:6333` | `6333` | External service | Vector database REST |
| **Redis** | `redis-cache:6379` | `redis-test:6379` | `6379` | External service | Cache & rate limiting (P2-T4) |
| **UI Webapp** | `ui-webapp:80` | `ui-webapp-test:80` | `80` | `src/frontend-angular/` | Frontend application |

### Environment Variables Reference

| Variable | Production Value | Test Value | Usage |
|----------|------------------|------------|-------|
| **POSTGRES_HOST** | `postgres-db` | `postgres-test` | Docker internal network |
| **POSTGRES_PORT** | `5432` | `5432` | Database port |
| **QDRANT_HOST** | `vector-db` | `qdrant-test` | Docker internal network |
| **QDRANT_PORT** | `6333` | `6333` | Vector database port |
| **REDIS_URL** | `redis://redis-cache:6379` | `redis://redis-test:6379` | Docker internal network (P2-T4) |
| **GATEWAY_PORT** | `8002` | `8002` | Inference Gateway internal port (P2-T4) |
| **POSTGRES_HOST** (external) | `localhost` | `localhost` | External access |
| **POSTGRES_PORT** (external) | `5532` | `5433` | External database access |
| **QDRANT_HOST** (external) | `localhost` | `localhost` | External access |
| **QDRANT_PORT** (external) | `6333` | `6335` | External vector database access |
| **REDIS_HOST** (external) | `localhost` | `localhost` | External access (P2-T4) |
| **REDIS_PORT** (external) | `6379` | `6380` | External Redis access (P2-T4) |

## Update History

- **P2-T4 (Nov 2025)**: Added Inference Gateway (port 8002/8007) and Redis (port 6379/6380)
