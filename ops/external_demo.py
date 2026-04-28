#!/usr/bin/env python3
"""
External Demonstration Script for AI Operations Platform

This script demonstrates how to interact with the AI Operations Platform API
from an external system (like a SOAR playbook). It respects the containerization
boundaries by only using the public API endpoints.

Usage:
    # When running from your host machine (outside Docker):
    # Assumes 'testuser' has the 'user' role (see ops/database/seed/001_seed_users.sql)
    python ops/external_demo.py --username testuser --password <test-password>

    # When running from INSIDE the 'deploy-dev-environment-1' Docker container:
    # Assumes 'testuser' has the 'user' role (see ops/database/seed/001_seed_users.sql)
    python ops/external_demo.py --api-url http://orchestrator-api:8000 --username testuser --password <test-password>

    # To skip authentication (if API allows for specific paths):
    python external_demo.py --no-auth

Environment variables:
    API_BASE_URL: Base URL of the API (default: http://localhost:8000 for host execution)
    API_USERNAME: Username for authentication
    API_PASSWORD: Password for authentication
"""

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
from typing import Any, cast

import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default configuration (override with environment variables or command line arguments)
DEFAULT_CONFIG = {
    "api_base_url": "http://localhost:8000",
    "username": None,
    "password": None,
}

# Sample questions for each intent type
SAMPLE_QUESTIONS = {
    "QUERY": "What are the indicators of compromise for the Lazarus Group?",
    "RULE_GENERATION": "Create a Yara rule to detect Cobalt Strike beacons",
    "SUMMARIZATION": "Summarize the latest Apache Log4j vulnerability",
    "ENRICHMENT": "Enrich this IP address: 185.193.141.248",
}

# Sample context for each intent type (simplified for demonstration)
SAMPLE_CONTEXT = {
    "QUERY": """
    The Lazarus Group, also known as APT38, is a North Korean state-sponsored threat actor.
    Common indicators of compromise include:
    - IP addresses: 192.0.2.0/24 (example range)
    - Command and control domains: akdls88.com, webbfind.info
    - File hashes: 8c4fa86a95977e3d7e5d321b9e67ad14, 4d4bb9f511db2968970321afc6a1b2ad
    - User-Agent strings: Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/545.36
    """,
    "RULE_GENERATION": """
    Cobalt Strike beacons often use:
    - XOR encryption with a rolling key
    - Default sleep time of 60 seconds
    - Specific byte sequences like 0x0001fc2e
    - HTTP GET requests with specific URI patterns
    - Common C2 domains registered within the last 3 months
    """,
    "SUMMARIZATION": """
    Apache Log4j Vulnerability (CVE-2021-44228)

    On December 9, 2021, a critical zero-day vulnerability was discovered in Apache Log4j, a widely used Java logging library.
    The vulnerability, known as Log4Shell, allows attackers to execute arbitrary code by manipulating log messages.
    It affects Log4j versions 2.0 through 2.14.1. The vulnerability is easy to exploit and can lead to complete system takeover.

    Mitigation steps include:
    1. Upgrading to Log4j 2.15.0 or later
    2. Setting system property -Dlog4j2.formatMsgNoLookups=true
    3. Removing the JndiLookup class from the classpath

    Multiple threat actors have been observed exploiting this vulnerability in the wild, including nation-state groups.
    """,
    "ENRICHMENT": """
    IP: 192.0.2.1
    ASN: 64512
    Organization: Example Org
    Country: XX
    City: Example City
    First seen: 2021-03-15
    Last seen: 2023-11-02
    Associated malware: Emotet, TrickBot
    Known for: Command and control server, phishing campaign infrastructure
    """,
}


class AIOPClient:
    """API client for interacting with AI Operations Platform as an external system."""

    def __init__(self, base_url: str, username: str | None = None, password: str | None = None):
        """
        Initialize the AI Operations Platform (AIOP) API client.

        Args:
            base_url: Base URL of the API (e.g., http://localhost:8000)
            username: Username for authentication
            password: Password for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.session = requests.Session()

        # Add proper user agent
        self.session.headers.update(
            {
                "User-Agent": "AI Operations Platform (AIOP)-External-Demo/1.0",
                "Content-Type": "application/json",
            }
        )

        logger.info(f"Initialized AI Operations Platform (AIOP) client with base URL: {base_url}")

    def authenticate(self) -> bool:
        """
        Authenticate with the API and get access token.

        Returns:
            True if authentication was successful, False otherwise.
        """
        if not self.username or not self.password:
            logger.warning("Username or password not provided. Authentication skipped.")
            return False

        try:
            auth_url = f"{self.base_url}/auth/token"
            auth_data = {"username": self.username, "password": self.password}

            logger.info("Authenticating with API")
            # FastAPI expects form data for OAuth2 authentication, not JSON
            # Store the original content type and set it to form data for this request
            original_content_type = self.session.headers.get("Content-Type")
            self.session.headers["Content-Type"] = "application/x-www-form-urlencoded"
            response = self.session.post(auth_url, data=auth_data)
            # Restore the original content type
            if original_content_type:
                self.session.headers["Content-Type"] = original_content_type
            else:
                self.session.headers.pop("Content-Type", None)

            if response.status_code == 200:
                auth_result = response.json()
                self.access_token = auth_result.get("access_token")
                self.refresh_token = auth_result.get("refresh_token")

                # Add token to session headers
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"

                logger.info("Authentication successful")
                return True
            logger.error("Authentication failed with status code: %s", response.status_code)
            return False

        except RequestException as e:
            logger.error("Error during authentication: %s", type(e).__name__)
            return False

    def refresh_auth_token(self) -> bool:
        """
        Refresh the authentication token.

        Returns:
            True if refresh was successful, False otherwise.
        """
        if not self.refresh_token:
            logger.warning("No refresh token available. Cannot refresh authentication.")
            return False

        try:
            refresh_url = f"{self.base_url}/auth/refresh"
            refresh_data = {"token": self.refresh_token}

            logger.info("Refreshing authentication token")
            response = self.session.post(refresh_url, json=refresh_data)

            if response.status_code == 200:
                refresh_result = response.json()
                self.access_token = refresh_result.get("access_token")

                # Update token in session headers
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"

                logger.info("Token refresh successful")
                return True
            logger.error("Token refresh failed with status code: %s", response.status_code)
            return False

        except RequestException as e:
            logger.error("Error during token refresh: %s", type(e).__name__)
            return False

    def process_request(
        self, query: str, request_type: str, context: str | None = None, stream: bool = False
    ) -> dict:
        """
        Process a request through the orchestrator API.

        Args:
            query: The question or request to process
            request_type: The type of request (QUERY, RULE_GENERATION, SUMMARIZATION, ENRICHMENT)
            context: Additional context for the request (optional)
            stream: Whether to use streaming response (optional)

        Returns:
            The API response as a dictionary
        """
        try:
            # Prepare request data
            request_data: dict[str, Any] = {"query": query, "request_type": request_type}

            # Add context if provided - convert string context to expected format
            if context:
                request_data["context"] = {
                    "text": context
                }  # This is the format expected by the API

            # Use the same API endpoint for both streaming and non-streaming
            process_url = f"{self.base_url}/api/v1/process"

            # Log the appropriate message
            if stream:
                logger.info(f"Processing {request_type} request with streaming")
            else:
                logger.info(f"Processing {request_type} request synchronously")

            # Include 'stream' parameter in the request data
            request_data["stream"] = stream

            # Make the API request (do not log request body; may contain user content)
            if stream:
                # Streaming response handling
                with self.session.post(process_url, json=request_data, stream=True) as response:
                    if response.status_code != 200:
                        logger.error(
                            "Request failed with status code: %s",
                            response.status_code,
                        )
                        return {"error": f"Request failed with status {response.status_code}"}

                    # Process streaming response
                    full_response = None
                    for line in response.iter_lines():
                        if line:
                            # Parse SSE format
                            line = line.decode("utf-8")
                            if line.startswith("data: "):
                                try:
                                    chunk_data = json.loads(line[6:])
                                    # Changed from logger.info to logger.debug to reduce verbosity
                                    logger.debug(
                                        f"Received chunk, response length: {len(chunk_data.get('response', ''))}"
                                    )
                                    full_response = chunk_data
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error parsing streaming response: {e}")

                    return full_response or {"error": "No complete response received"}
            else:
                # Synchronous response handling
                response = self.session.post(process_url, json=request_data)

                if response.status_code != 200:
                    logger.error("Request failed with status code: %s", response.status_code)
                    return {"error": f"Request failed with status {response.status_code}"}

                response_data = response.json()
                logger.info(
                    f"Received response of length: {len(response_data.get('response', ''))}"
                )
                return cast("dict[Any, Any]", response_data)

        except RequestException as e:
            logger.error("Error during request processing: %s", type(e).__name__)
            return {"error": type(e).__name__}

    def check_health(self) -> bool:
        """
        Check if the API is healthy.

        Returns:
            True if the API is healthy, False otherwise.
        """
        try:
            health_url = f"{self.base_url}/health"
            logger.info("Checking API health")

            response = self.session.get(health_url)

            if response.status_code == 200:
                logger.info("API is healthy")
                return True
            logger.error(f"API health check failed with status code: {response.status_code}")
            return False

        except RequestException as e:
            logger.error("Error during health check: %s", type(e).__name__)
            return False


def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a port is open on the given host.

    Args:
        host: The host to check
        port: The port to check
        timeout: Timeout in seconds

    Returns:
        True if the port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except OSError:
        return False


def get_docker_container_ip(container_name: str) -> str | None:
    """
    Get the IP address of a Docker container by name.

    Args:
        container_name: The name of the Docker container

    Returns:
        The IP address of the container, or None if not found
    """
    try:
        # Try to get the container's IP address using docker inspect
        cmd = [
            "docker",
            "inspect",
            "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            container_name,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Failed to get container IP: {e}")

    return None


def run_connection_diagnostics(base_url: str) -> dict[str, Any]:
    """
    Run network diagnostics to help troubleshoot connection issues.

    Args:
        base_url: The base URL that's failing

    Returns:
        A dictionary with diagnostic information
    """
    alternatives_to_try: list[str] = []
    diagnostics: dict[str, Any] = {
        "original_url": base_url,
        "alternatives_to_try": alternatives_to_try,
        "port_open": False,
        "container_ip": None,
        "docker_running": False,
        "docker_networks": [],
    }

    # Parse the URL to extract host and port
    try:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        # Check if port is open
        diagnostics["port_open"] = check_port_open(host, port)

        # Try to get container IP for orchestrator-api
        diagnostics["container_ip"] = get_docker_container_ip("orchestrator-api")

        # Check if container IP is directly accessible
        container_ip = diagnostics["container_ip"]
        if container_ip and isinstance(container_ip, str):
            container_port_open = check_port_open(container_ip, 8000)
            diagnostics["container_port_open"] = container_port_open

            if container_port_open:
                alternatives_to_try.append(f"http://{container_ip}:8000")

        # Check for docker-machine environment
        try:
            cmd = ["docker", "ps"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            diagnostics["docker_running"] = result.returncode == 0

            # If Docker is running, try to get network information
            if diagnostics["docker_running"]:
                cmd = ["docker", "network", "ls"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    networks = [line.split()[1] for line in result.stdout.strip().split("\n")[1:]]
                    diagnostics["docker_networks"] = networks

                    # Try to get more information about each network
                    for network in networks:
                        cmd = ["docker", "network", "inspect", network]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            network_info = json.loads(result.stdout)
                            if network_info and "Containers" in network_info[0]:
                                for _container_id, container_info in network_info[0][
                                    "Containers"
                                ].items():
                                    if "orchestrator-api" in container_info.get("Name", ""):
                                        ip = container_info.get("IPv4Address", "").split("/")[0]
                                        if ip:
                                            alternatives_to_try.append(f"http://{ip}:8000")
        except Exception as e:
            logger.warning(f"Error getting Docker information: {e}")

        # Add alternative URLs to try
        alternatives_to_try.extend(
            ["http://localhost:8000", "http://127.0.0.1:8000", "http://0.0.0.0:8000"]
        )

        # If on Mac, try host.docker.internal
        if sys.platform == "darwin":
            alternatives_to_try.append("http://host.docker.internal:8000")

    except Exception as e:
        logger.warning(f"Error during diagnostics: {e}")

    return diagnostics


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "AI Operations Platform External Demo.\n\n"
            "IMPORTANT:\n"
            "- Authentication (e.g., --username testuser --password password) is typically required.\n"
            "  The 'testuser' should have the 'user' role (see ops/database/seed/001_seed_users.sql).\n"
            "- If running this script INSIDE the project's dev Docker container (e.g., 'deploy-dev-environment-1'),\n"
            "  you MUST use '--api-url http://orchestrator-api:8000' for the orchestrator service."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--api-url",
        help="Base URL of the API (e.g., http://localhost:8000 or http://orchestrator-api:8000 if in dev container)",
        default=os.environ.get("API_BASE_URL", DEFAULT_CONFIG["api_base_url"]),
    )

    parser.add_argument(
        "--username",
        help="Username for authentication (e.g., testuser)",
        default=os.environ.get("API_USERNAME", DEFAULT_CONFIG["username"]),
    )

    parser.add_argument(
        "--password",
        help="Password for authentication",
        default=os.environ.get("API_PASSWORD", DEFAULT_CONFIG["password"]),
    )

    parser.add_argument("--no-auth", help="Skip authentication", action="store_true")

    parser.add_argument(
        "--auto-detect", help="Automatically try to detect the correct API URL", action="store_true"
    )

    parser.add_argument(
        "--debug", help="Enable debug mode with more verbose output", action="store_true"
    )

    return parser.parse_args()


def display_response(request_type: str, response: dict):
    """Display the formatted response."""
    print(f"\n{'#' * 80}")
    print(f"## {request_type} RESPONSE")

    if "error" in response:
        error_message = response["error"]
        status_code = None
        if isinstance(error_message, str) and "status" in error_message:
            try:
                # Attempt to parse status code if embedded like "Request failed with status XXX"
                parts = error_message.split("status ")
                if len(parts) > 1:
                    status_code_str = parts[1].split(" ")[0]
                    if status_code_str.isdigit():
                        status_code = int(status_code_str)
            except Exception:
                pass  # Ignore parsing errors

        print(f"## ERROR: {error_message}")
        if status_code == 401:
            print("## Suggestion: Authentication failed. Check your --username and --password.")
            print(
                "## Default demo credentials (ensure 'testuser' has 'user' role via seed data): --username testuser --password <test-password>"
            )
        elif status_code == 403:
            print(
                "## Suggestion: Authorization failed. The authenticated user may not have the required role."
            )
            print(
                "## The API endpoint likely requires the 'user' role. Check the user's roles in the database (see ops/database/seed/)."
            )
            print("## Ensure 'testuser' is assigned the 'user' role.")
        elif "Connection refused" in str(
            error_message
        ) or "Failed to establish a new connection" in str(error_message):
            print(
                "## Suggestion: Connection refused. Ensure the API service is running and accessible."
            )
            print(
                "## If running this script in a Docker container, use the service name as hostname (e.g., --api-url http://orchestrator-api:8000)."
            )
            print(
                "## If running from host, ensure Docker containers are up (docker-compose ps) and port mapping is correct."
            )
        elif "No complete response received" in str(error_message) and "STREAMING" in request_type:
            print(
                "## Suggestion: This often indicates an issue with the server-side streaming implementation (e.g., data not being sent correctly or an unterminated stream)."
            )
        elif "Error processing request. Please try again later." in str(
            error_message
        ) and request_type in ["RULE_GENERATION", "ENRICHMENT"]:
            print(
                "## Suggestion: This generic error for RULE_GENERATION or ENRICHMENT might indicate a backend processing issue, such as an LLM timeout or an internal error."
            )

        print(f"{'#' * 80}\n")
        return

    confidence = response.get("confidence", 0.0)
    print(f"## Confidence: {confidence:.2f}")
    print(f"{'#' * 80}\n")

    response_text = response.get("response", "No response")
    print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
    print("\n")

    sources = response.get("sources", [])
    if sources:
        print("SOURCES:")
        for i, source in enumerate(sources, 1):
            print(
                f"{i}. {source.get('title')} (Relevance: {source.get('relevance_score', 0.0):.2f})"
            )
        print("\n")


def demonstrate_api(client: AIOPClient):
    """Demonstrate API functionality with sample requests."""
    # Process a request for each intent type
    for request_type, question in SAMPLE_QUESTIONS.items():
        # Get context for this request type
        context = SAMPLE_CONTEXT.get(request_type, "")

        # Process synchronously
        response = client.process_request(question, request_type, context)
        display_response(request_type, response)

        # Process one request type with streaming for demonstration
        if request_type == "QUERY":
            streaming_response = client.process_request(
                question, request_type, context, stream=True
            )
            print(f"\n{'#' * 80}")
            print(f"## {request_type} STREAMING RESPONSE")
            print(f"{'#' * 80}\n")
            display_response(request_type, streaming_response)


def try_alternative_urls(base_url: str) -> tuple[str, AIOPClient] | None:
    """
    Try alternative URLs to connect to the API.

    Args:
        base_url: The original base URL

    Returns:
        A tuple of (working_url, client) if successful, None otherwise
    """
    print("Running network diagnostics...")
    diagnostics = run_connection_diagnostics(base_url)

    # Print diagnostic information
    print(f"Original URL: {diagnostics['original_url']}")
    print(f"Port open: {diagnostics['port_open']}")
    print(f"Docker running: {diagnostics['docker_running']}")

    if diagnostics["container_ip"]:
        print(f"Container IP: {diagnostics['container_ip']}")

    print("\nTrying alternative URLs:")

    # Try each alternative URL
    for alt_url in diagnostics["alternatives_to_try"]:
        if alt_url == base_url:
            continue

        print(f"Trying {alt_url}...")
        client = AIOPClient(base_url=alt_url)

        try:
            if client.check_health():
                print(f"SUCCESS: Connected to {alt_url}")
                return alt_url, client
        except Exception as e:
            print(f"Failed to connect to {alt_url}: {e}")

    print("\nCould not connect to any alternative URLs.")
    print("\nPossible solutions:")
    print("1. Ensure Docker containers are running: docker-compose ps")
    print("2. Check Docker logs: docker-compose logs orchestrator-api")
    print("3. Try running this script inside the container network:")
    print("   docker exec -it ui-webapp python ops/external_demo.py")
    print("4. Check if there are any firewall or network issues blocking the connection")
    print("5. Verify the API endpoint is correctly configured in docker-compose.yml")
    print("6. Try connecting to the API using curl from inside and outside the container:")
    print("   curl http://localhost:8000/health")

    return None


def main():
    """Main entry point for the demonstration script."""
    print(f"\n{'=' * 80}")
    print("AI Operations Platform External API Demonstration")
    print(f"{'=' * 80}\n")

    # Parse command line arguments
    args = parse_args()

    # Set log level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        # Also set requests logging to DEBUG
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    # Initialize the client
    client = AIOPClient(
        base_url=args.api_url,
        username=args.username if not args.no_auth else None,
        password=args.password if not args.no_auth else None,
    )

    # Check API health
    connected = False
    try:
        connected = client.check_health()
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        connected = False

    # If not connected and auto-detect is enabled, try alternative URLs
    if not connected:
        if args.auto_detect:
            print("API health check failed. Attempting to auto-detect the correct URL...")
            result = try_alternative_urls(args.api_url)

            if result:
                working_url, client = result
                print(f"Successfully connected to the API at {working_url}")
                print(f"Use this URL in future requests: --api-url {working_url}")
                connected = True
            else:
                print("\nERROR: Could not auto-detect the correct API URL.")
                print("Please check that the service is running and try again.")
                print("Run with --debug for more detailed error information.")
                sys.exit(1)
        else:
            print("\nERROR: API is not healthy. Please check that the service is running.")
            print("You can run with --auto-detect to try alternative URLs automatically.")
            print("Run with --debug for more detailed error information.")

            # Automatically run diagnostics to help the user
            run_connection_diagnostics(args.api_url)
            sys.exit(1)

    # Authenticate if credentials are provided
    if (
        connected
        and not args.no_auth
        and (args.username and args.password)
        and not client.authenticate()
    ):
        print("ERROR: Authentication failed. Please check your credentials.")
        sys.exit(1)

    # Demonstrate API functionality
    if connected:
        print("\nSuccessfully connected to the API. Running demonstration...")
        demonstrate_api(client)


if __name__ == "__main__":
    main()
