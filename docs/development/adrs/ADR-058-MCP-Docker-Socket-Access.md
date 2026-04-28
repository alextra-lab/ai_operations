# ADR-058: MCP Docker Socket Access for STDIO-based MCP Servers

## Status

**Accepted** - November 2025

## Context

The AI Operations Platform application needs to connect to MCP (Model Context Protocol) servers for tool integration. MCP servers come in three transport types:

1. **STDIO** - Server runs as subprocess, communicates via stdin/stdout
2. **HTTP** - Server exposes HTTP POST endpoint
3. **SSE** - Server exposes Server-Sent Events endpoint

The **Docker MCP Gateway** (`docker mcp gateway run`) is a particularly valuable MCP server because it:
- Aggregates multiple MCP servers into a single gateway
- Supports dynamic discovery via `mcp-find`, `mcp-add`, etc.
- Is the standard for Docker Desktop MCP Toolkit integration

However, Docker MCP Gateway only supports **STDIO transport**, which requires the ability to spawn subprocesses. When the orchestrator runs in a Docker container, it cannot execute `docker mcp gateway run` because:
1. The Docker CLI is not installed in the container
2. The container has no access to the Docker daemon

## Decision

**We will add Docker CLI and socket access to the orchestrator container** to enable direct STDIO-based MCP server execution.

### Implementation

1. **Dockerfile changes** (`src/orchestrator/Dockerfile`):
   - Install `docker.io` package
   - Add `appuser` to the `docker` group (GID 999)

2. **docker-compose changes** (`deploy/docker-compose.test.yml`):
   - Mount `/var/run/docker.sock:/var/run/docker.sock`

### Security Considerations

Mounting the Docker socket grants the orchestrator container significant privileges:
- Can start/stop any container on the host
- Can access host filesystem via Docker volume mounts
- Potential container escape vector

**Mitigations:**
- Application runs as non-root user (`appuser`)
- Docker group membership limits to Docker API access only
- This is acceptable for internal SOC admin tools
- Production deployments should evaluate threat model

## Alternatives Considered

### Alternative 1: Sidecar Container (Future Evolution)

A separate "mcp-bridge" container would:
- Have Docker CLI and socket access
- Run Supergateway to expose STDIO MCPs as SSE
- Orchestrator connects via HTTP/SSE (no Docker access)

```yaml
# Future sidecar approach
mcp-bridge:
  image: michlyn/supergateway
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  command: ["--stdio", "docker mcp gateway run", "--port", "8765"]
  ports:
    - "8765:8765"
```

**Pros:** Better security isolation, orchestrator stays "clean"
**Cons:** Additional container, network hop, complexity

**Decision:** Defer to future iteration if security requirements tighten.

### Alternative 2: HTTP/SSE Only MCPs

Only support MCP servers that expose HTTP or SSE endpoints.

**Pros:** No Docker access needed
**Cons:** Cannot use Docker MCP Gateway or many popular STDIO-only MCPs

**Decision:** Rejected - too limiting for functionality.

### Alternative 3: Run Orchestrator on Host

Run orchestrator outside Docker where it can access Docker CLI natively.

**Pros:** Simple, direct access
**Cons:** Loses containerization benefits, inconsistent deployment model

**Decision:** Rejected - contradicts containerized architecture.

## Consequences

### Positive
- Full support for STDIO-based MCP servers including Docker MCP Gateway
- Dynamic MCP discovery via `mcp-find`, `mcp-add` tools
- Consistent with how Claude Desktop, Cursor, and VS Code integrate MCPs

### Negative
- Increased security surface (Docker socket access)
- Container image size increases (~50MB for Docker CLI)
- Tighter coupling between container and host Docker daemon

### Neutral
- Build time slightly increased
- Documentation needed for deployment requirements

## Platform-Specific Notes

### Linux (Production - amd64)
- Docker MCP Toolkit installs natively as a CLI plugin
- `docker mcp gateway run` works from within containers
- This is the target production environment

### macOS (Development - Docker Desktop)
- Docker MCP Toolkit is a macOS binary inside Docker.app
- `docker mcp gateway run` does NOT work from within containers
- **Workaround for development**: Use Supergateway on host:
  ```bash
  npx -y supergateway --stdio "docker mcp gateway run" --port 8765
  ```
  Then register as SSE endpoint: `http://host.docker.internal:8765`

### Alternative for Development
- Use standalone HTTP/SSE MCPs which work on all platforms
- Docker CLI inside container still enables other `docker` commands

## Future Evolution

If security requirements change (e.g., multi-tenant deployment, external-facing), consider:

1. **Sidecar approach** with Supergateway for isolation
2. **MCP server allowlist** to restrict which STDIO commands can be executed
3. **Network policy** to limit what the orchestrator can access via Docker

## Related

- [ADR-056: MCP Tool Registration Workflow](ADR-056-MCP-Tool-Registration-Workflow.md)
- [ADR-057: MCP Tool Security Classification](ADR-057-MCP-Tool-Security-Classification.md)
- [Docker MCP Gateway Documentation](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/)
- [Supergateway](https://github.com/supercorp-ai/supergateway) - STDIO to SSE bridge
