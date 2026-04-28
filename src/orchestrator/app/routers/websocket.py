import asyncio
import json
import random
import socket
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.config.loader import (
    load_database_config,
    load_inference_gateway_config,
    load_orchestrator_config,
)
from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)

router = APIRouter()  # No prefix - routes will include /ws in their path

# Track process start time for uptime calculation
_PROCESS_START_TIME = time.time()

# Track active WebSocket connections
_active_connections: set[WebSocket] = set()


def _get_cpu_usage() -> float:
    """Get CPU usage percentage from /proc/stat (Linux only)."""
    try:
        stat_path = Path("/proc/stat")
        if not stat_path.exists():
            return 0.0

        with stat_path.open(encoding="utf-8") as f:
            line = f.readline()
        parts = line.split()
        # cpu user nice system idle iowait irq softirq
        if len(parts) < 5:
            return 0.0

        idle = int(parts[4])
        total = sum(int(p) for p in parts[1:8] if p.isdigit())
        if total == 0:
            return 0.0

        # Store for delta calculation (simplified - just return instant value)
        return round(100.0 * (1.0 - idle / total), 1)
    except Exception:
        return 0.0


def _get_memory_usage() -> float:
    """Get memory usage percentage from /proc/meminfo (Linux only)."""
    try:
        meminfo_path = Path("/proc/meminfo")
        if not meminfo_path.exists():
            return 0.0

        mem_total = 0
        mem_available = 0

        with meminfo_path.open(encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_available = int(line.split()[1])
                if mem_total and mem_available:
                    break

        if mem_total == 0:
            return 0.0

        used = mem_total - mem_available
        return round(100.0 * used / mem_total, 1)
    except Exception:
        return 0.0


def _check_tcp_health(name: str, host: str, port: int) -> dict[str, Any]:
    """Check service health via TCP socket connection."""
    status = "unknown"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((host, port))
        sock.close()
        status = "healthy" if result == 0 else "unreachable"
    except Exception as exc:
        logger.debug("TCP health check failed for %s: %s", name, exc)
        status = "unreachable"

    return {
        "name": name,
        "status": status,
        "uptime": 0,
        "last_check": datetime.now(UTC).isoformat(),
    }


def _load_service_endpoints() -> dict[str, str]:
    """Load service health endpoints from shared orchestrator configuration."""
    settings = load_orchestrator_config()
    return dict(settings.dashboard_health_endpoints)


def _fetch_service_health(name: str, url: str) -> dict[str, Any]:
    """Fetch a single service health endpoint with a short timeout."""
    # Avoid self-HTTP deadlocks in single-worker mode by using a TCP probe
    # for orchestrator self checks.
    if name.lower().startswith("orchestrator"):
        parsed = urlparse(url)
        port = parsed.port or 8000
        return _check_tcp_health(name, "127.0.0.1", port)

    status = "unknown"
    try:
        with httpx.Client(timeout=0.5) as client:
            resp = client.get(url)
            status = "healthy" if resp.status_code < 400 else "unhealthy"
    except Exception as exc:
        logger.debug("Health check failed for %s: %s", name, exc)
        status = "unreachable"

    return {
        "name": name,
        "status": status,
        "uptime": 0,
        "last_check": datetime.now(UTC).isoformat(),
    }


def _derive_overall_status(service_statuses: list[dict[str, Any]]) -> str:
    """Derive overall system status from individual service statuses."""
    if not service_statuses:
        return "healthy"  # No services configured = assume healthy

    statuses = [svc.get("status", "unknown") for svc in service_statuses]

    if any(s in ("unhealthy", "critical") for s in statuses):
        return "critical"
    if any(s in ("unreachable", "unknown") for s in statuses):
        return "warning"
    return "healthy"


def generate_dashboard_data() -> dict[str, Any]:
    """Generate dashboard data with real metrics where available."""
    now = datetime.now(UTC).isoformat()

    def build_threat_event() -> dict[str, Any]:
        return {
            "id": f"evt-{random.randint(1000, 9999)}",
            "title": random.choice(
                [
                    "Suspicious Login Attempt",
                    "Lateral Movement Detected",
                    "Malware Beacon",
                    "Unusual Data Exfil",
                ]
            ),
            "description": random.choice(
                [
                    "Multiple failed login attempts detected",
                    "SMB traffic spike to privileged hosts",
                    "Beacon to rare domain observed",
                    "Large transfer to external endpoint",
                ]
            ),
            "severity": random.choice(["low", "medium", "high", "critical"]),
            "source": random.choice(["192.168.1.100", "10.0.0.5", "vpn.corp", "dmz-fw"]),
            "timestamp": now,
            "category": random.choice(["authentication", "network", "malware", "data"]),
            "tags": random.sample(["auth", "suspicious", "exfil", "lateral", "dns"], k=2),
            "status": random.choice(["new", "investigating", "resolved", "escalated"]),
        }

    def build_alert() -> dict[str, Any]:
        return {
            "id": f"alt-{random.randint(1000, 9999)}",
            "type": random.choice(
                [
                    "authentication_failure",
                    "suspicious_activity",
                    "data_breach",
                    "malware_detected",
                ]
            ),
            "title": random.choice(
                [
                    "Brute Force Attack",
                    "Impossible Travel",
                    "Data Exfil Suspected",
                    "Malware Quarantined",
                ]
            ),
            "description": random.choice(
                [
                    "Repeated password failures from single IP",
                    "User logged in from two countries within 10m",
                    "High-volume transfer to untrusted domain",
                    "EDR quarantined malware on host",
                ]
            ),
            "severity": random.choice(["low", "medium", "high", "critical"]),
            "source": random.choice(["Auth Service", "EDR", "SIEM", "DLP Gateway"]),
            "timestamp": now,
            "status": random.choice(["active", "acknowledged", "resolved"]),
        }

    def build_user_activity() -> dict[str, Any]:
        return {
            "user_id": f"user-{random.randint(1, 9)}",
            "username": random.choice(["analyst_jane", "analyst_lee", "tier1_mia", "soar_bot"]),
            "action": random.choice(
                ["query_execution", "ioc_lookup", "case_update", "playbook_run"]
            ),
            "resource": random.choice(["threat_db", "ioc_feed", "case#1042", "soar:contain-host"]),
            "timestamp": now,
            "ip_address": random.choice(["10.0.0.10", "10.0.2.15", "192.168.50.8"]),
            "user_agent": "Mozilla/5.0",
            "success": random.choice([True, True, False]),
        }

    def build_top_query() -> dict[str, Any]:
        return {
            "query": random.choice(
                [
                    "failed login surge from corp vpn",
                    "detect lateral movement hosts=prod*",
                    "suspicious dns to rare domains",
                    "edr quarantines last 24h",
                    "alerts with severity:high AND status:open",
                ]
            ),
            "count": random.randint(40, 160),
            "avg_response_time": random.uniform(120, 520),
            "success_rate": random.randint(75, 99),
        }

    def build_recent_query() -> dict[str, Any]:
        return {
            "id": f"qry-{random.randint(10000, 99999)}",
            "query": random.choice(
                [
                    "list active incidents severity>=medium",
                    "ioc reputation domain=example.com",
                    "search windows eventid:4625 last 1h",
                    "find hosts with high cpu usage",
                    "summarize siem alerts last 15m",
                ]
            ),
            "user": random.choice(["analyst_jane", "analyst_lee", "tier1_mia"]),
            "timestamp": now,
            "status": random.choice(["success", "failed", "processing"]),
            "response_time": random.uniform(80, 600),
        }

    def build_recent_document() -> dict[str, Any]:
        status = random.choice(["processing", "completed", "failed", "queued"])
        processed_at = now if status == "completed" else None
        processing_time = random.uniform(1.5, 6.5) if processed_at else None

        return {
            "id": f"doc-{random.randint(1000, 9999)}",
            "filename": random.choice(
                [
                    "edr-alerts-2025-12-06.json",
                    "pcap-sample-core-site.pcap",
                    "auth-failures-rolling.csv",
                    "dlp-events.csv",
                    "malware-hashes.txt",
                ]
            ),
            "status": status,
            "uploaded_by": random.choice(["soar_bot", "analyst_jane"]),
            "uploaded_at": now,
            "processed_at": processed_at,
            "processing_time": processing_time,
            "error_message": None,
        }

    service_endpoints = _load_service_endpoints()
    service_statuses = [_fetch_service_health(name, url) for name, url in service_endpoints.items()]

    # Add TCP-based health checks for database services
    database_config = load_database_config()
    postgres_host = database_config.host
    postgres_port = database_config.port
    service_statuses.insert(0, _check_tcp_health("PostgreSQL", postgres_host, postgres_port))

    # Redis (optional - only if configured)
    gateway_config = load_inference_gateway_config()
    redis_url = gateway_config.redis.url
    if redis_url and gateway_config.redis.enabled:
        # Parse redis://host:port format
        try:
            redis_part = redis_url.replace("redis://", "").split("/")[0]
            redis_host, redis_port_str = redis_part.split(":")
            service_statuses.append(_check_tcp_health("Redis", redis_host, int(redis_port_str)))
        except (ValueError, IndexError):
            pass  # Skip if Redis URL is malformed

    overall_status = _derive_overall_status(service_statuses)

    return {
        "type": "dashboard_data",
        "data": {
            "timestamp": now,
            "system_health": {
                "status": overall_status,
                "uptime": int(time.time() - _PROCESS_START_TIME),
                "services": service_statuses,
                "last_check": now,
            },
            "threat_events": [build_threat_event() for _ in range(6)],
            "security_alerts": [build_alert() for _ in range(5)],
            "user_activity": [build_user_activity() for _ in range(10)],
            "query_stats": {
                "total_queries": random.randint(1000, 5000),
                "successful_queries": random.randint(900, 4900),
                "failed_queries": random.randint(0, 100),
                "average_response_time": random.uniform(0.1, 2.0),
                "queries_per_hour": random.randint(100, 500),
                "top_queries": [build_top_query() for _ in range(5)],
                "recent_queries": [build_recent_query() for _ in range(10)],
            },
            "performance_metrics": {
                "response_time": random.uniform(50, 300),  # TODO: track real API latency
                "throughput": random.uniform(10, 100),  # TODO: track real requests/sec
                "error_rate": random.uniform(0, 2),  # TODO: track real error rate
                "cpu_usage": _get_cpu_usage(),  # Real CPU usage
                "memory_usage": _get_memory_usage(),  # Real memory usage
                "disk_io": random.uniform(10, 50),  # TODO: track real disk I/O
                "network_io": random.uniform(20, 100),  # TODO: track real network I/O
                "active_connections": len(_active_connections),  # Real WebSocket count
                "queue_length": 0,  # TODO: track real queue if applicable
            },
            "document_processing": {
                "total_documents": random.randint(100, 1000),
                "processing": random.randint(0, 5),
                "completed": random.randint(90, 990),
                "failed": random.randint(0, 10),
                "average_processing_time": random.uniform(1.0, 5.0),
                "queue_size": random.randint(0, 5),
                "recent_documents": [build_recent_document() for _ in range(5)],
            },
        },
    }


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time dashboard data."""
    try:
        await websocket.accept()
        _active_connections.add(websocket)
        logger.info("Dashboard WebSocket connected (active: %d)", len(_active_connections))

        # Send initial data immediately
        initial_data = generate_dashboard_data()
        await websocket.send_text(json.dumps(initial_data))
        logger.debug("Initial dashboard data sent")

        # Keep sending updates
        while True:
            await asyncio.sleep(5)  # Wait 5 seconds between updates
            data = generate_dashboard_data()
            await websocket.send_text(json.dumps(data))
            logger.debug("Dashboard data update sent")
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected")
    except (OSError, ConnectionError, RuntimeError) as e:
        logger.error("Dashboard WebSocket error: %s", e, exc_info=True)
        with suppress(Exception):
            await websocket.close()
    finally:
        _active_connections.discard(websocket)
