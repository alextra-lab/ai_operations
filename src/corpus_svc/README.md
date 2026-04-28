# Retrieval Service

## Overview

The Retrieval Service manages document processing, vector storage, and retrieval functionality for the RAG (Retrieval-Augmented Generation) architecture within the AI Operations Platform platform. It's designed as an independent microservice that works in conjunction with the Embedding Service.

## Features

- Document processing and storage
- Vector search via Qdrant
- Document metadata management in PostgreSQL
- JWT-based authentication with role-based access control
- Structured JSON logging with request ID tracking
- OpenTelemetry integration for distributed tracing
- Health check endpoint for monitoring
- Containerized deployment

## Architecture

The Retrieval Service follows a layered architecture:

```
src/corpus_svc/
  ├── app/                # Application code
  │   ├── main.py         # Application entry point
  │   ├── clients/        # External service clients (e.g. embedding)
  │   ├── config/         # Configuration
  │   ├── db/             # Database connections
  │   ├── middleware/     # Request middleware
  │   ├── processing/     # Document processing and extraction
  │   ├── repositories/   # Vector and document storage
  │   ├── routers/       # API endpoints
  │   ├── schemas/        # Data models
  │   ├── services/       # Business logic
  │   └── utils/          # Utility modules (auth, embeddings)
  │       └── auth.py     # Authentication utilities
  ├── Dockerfile          # Container definition
  └── requirements.txt    # Python dependencies
```

## Authentication

The service uses JWT-based authentication to secure its endpoints. Authentication is handled by the `utils/auth.py` module, which provides:

- JWT token validation
- Role-based access control
- FastAPI dependency integration
- Standardized error responses

For more information, see the [Authentication Patterns](../../docs/architecture/authentication_patterns.md) documentation.

## Observability

The service implements comprehensive observability features through:

- Structured JSON logging from `shared.logging_utils`
- Distributed tracing via OpenTelemetry from `shared.telemetry_utils`
- Request ID propagation across service boundaries
- Detailed error logging with exception information
- Health check endpoint reporting database connectivity

For more information, see the [Observability Patterns](../../docs/architecture/observability_patterns.md) documentation.

## API Endpoints

### Health Check

```
GET /health
```

Returns the service health status with database and Qdrant connection status.

### Document Management (examples)

```
POST /documents
```

Processes and stores a document, generating vector embeddings through the Embedding Service.

```
GET /documents/{document_id}
```

Retrieves a document by ID.

### Vector Search (example)

```
POST /query
```

Performs a vector search using the embedding generated from the query text.

## Configuration

The service is configured through environment variables:

- `JWT_SECRET`: The secret key used for JWT validation
- `DEBUG`: Enable/disable debug mode
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry exporter endpoint
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name
- `POSTGRES_HOST`: PostgreSQL host
- `POSTGRES_PORT`: PostgreSQL port
- `QDRANT_HOST`: Qdrant host
- `QDRANT_PORT`: Qdrant port
- `EMBEDDING_SERVICE_URL`: URL for the Embedding Service
- `DOCUMENTS_PATH`: Path for document storage
- `TEMP_PATH`: Path for temporary processing files
- `COLLECTION_NAME`: Qdrant collection name
- `VECTOR_SIZE`: Embedding vector dimension size (384)
- `HNSW_M`: HNSW index parameter (16)
- `HNSW_EF_CONSTRUCT`: HNSW index parameter (100)

## Database Schema

The service uses PostgreSQL for structured metadata:

- `documents`: Stores document metadata, source information, and classification
- `chunks`: Stores document chunks with positions and metadata
- `entities`: Stores extracted entities from documents (IPs, CVEs, etc.)

## Vector Database

The service uses Qdrant for vector storage:

- Collections organized by document type
- Vector dimension: 384 (all-minilm-l6-v2)
- Index: HNSW with M=16, ef_construct=100
- Payload: document metadata, source reference, timestamps

## Deployment

The service is designed to be deployed as a containerized service. The Dockerfile and deployment configuration can be found in:

- `src/corpus_svc/Dockerfile`
- `deploy/docker-compose.yml`

## Development

To run the service locally during development:

```bash
# From the project root
cd src/corpus_svc
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

For more information on the service decoupling and design decisions, see the [Service Decoupling](../../docs/architecture/service_decoupling.md) documentation.
