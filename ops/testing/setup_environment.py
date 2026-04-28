#!/usr/bin/env python3
"""
Test Environment Setup for Cyber Defense Analyst AI Assistant

This script sets up the test environment for the project:
1. Installs required dependencies for testing
2. Sets up environment variables needed for tests
3. Configures test directories and verifies their structure
4. Creates necessary configuration files for testing

Usage:
    python setup_test_environment.py [--component COMPONENT] [--verbose] [--skip-deps]

Options:
    --component COMPONENT    Set up environment only for a specific component (orchestrator, embedding, corpus_svc)
    --verbose                Enable verbose output
    --skip-deps              Skip dependency installation
    --force                  Force overwrite of existing configurations
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

# Define base directory (ops/testing -> project root is parent.parent)
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
TEST_DIR = PROJECT_ROOT / "tests"
ENV_TEST = PROJECT_ROOT / "config" / "env" / "env.test"

# Define component directories (backend -> orchestrator, retrieval -> corpus_svc)
COMPONENTS = {
    "orchestrator": {
        "src_dir": SRC_DIR / "orchestrator",
        "test_dir": TEST_DIR / "orchestrator",
        "dependencies": [
            "pytest==7.3.1",
            "pytest-asyncio==0.21.0",
            "pytest-cov==4.1.0",
            "httpx==0.24.1",
            "python-jose==3.3.0",
            "psycopg[binary,pool]==3.1.9",
            "opentelemetry-api==1.18.0",
            "opentelemetry-sdk==1.18.0",
        ],
        "env_vars": {
            "PYTHONPATH": str(PROJECT_ROOT),
            "JWT_SECRET": "set_in_env",
            "LOG_LEVEL": "DEBUG",
        },
    },
    "embedding": {
        "src_dir": SRC_DIR / "embedding",
        "test_dir": TEST_DIR / "embedding",
        "dependencies": [
            "pytest==7.3.1",
            "pytest-asyncio==0.21.0",
            "pytest-cov==4.1.0",
            "httpx==0.24.1",
            "pyyaml==6.0",
            "python-jose==3.3.0",
            "openai==0.27.8",
        ],
        "env_vars": {
            "PYTHONPATH": str(PROJECT_ROOT),
            "EMBEDDING_API_KEY": "set_in_env",
            "LOG_LEVEL": "DEBUG",
        },
    },
    "corpus_svc": {
        "src_dir": SRC_DIR / "corpus_svc",
        "test_dir": TEST_DIR / "corpus_svc",
        "dependencies": [
            "pytest==7.3.1",
            "pytest-asyncio==0.21.0",
            "pytest-cov==4.1.0",
            "httpx==0.24.1",
            "aiohttp==3.8.5",
            "qdrant-client==1.7.0",
            "asyncpg==0.29.0",
            "psycopg[binary,pool]==3.1.9",
            "pydantic==1.10.12",
            "python-jose==3.3.0",
            "python-multipart==0.0.6",
            "opentelemetry-api==1.18.0",
            "opentelemetry-sdk==1.18.0",
            "opentelemetry-instrumentation-fastapi==0.39b0",
            "pytesseract==0.3.10",
            "pdfplumber==0.9.0",
            "PyPDF2==3.0.1",
            "pillow==9.5.0",
            "python-docx==0.8.11",
            "langdetect==1.0.9",
            "python-json-logger==2.0.7",
        ],
        "env_vars": {
            "PYTHONPATH": str(PROJECT_ROOT),
            "JWT_SECRET": "set_in_env",
            "LOG_LEVEL": "DEBUG",
            "QDRANT_HOST": "localhost",
            "QDRANT_PORT": "6333",
            "PG_HOST": "localhost",
            "PG_PORT": "5432",
            "PG_USER": "postgres",
            "PG_PASSWORD": "postgres",
            "PG_DATABASE": "aio-test",
            "EMBEDDING_SERVICE_URL": "http://localhost:8001",
            "EMBEDDING_SERVICE_API_KEY": "test-key",
        },
    },
}

# Common dependencies for all components
COMMON_DEPENDENCIES = [
    "pytest==7.3.1",
    "pytest-cov==4.1.0",
    "pytest-asyncio==0.21.0",
]


def install_dependencies(component: str | None, verbose: bool, skip_deps: bool) -> bool:
    """Install dependencies for testing."""
    if skip_deps:
        print("Skipping dependency installation")
        return True

    # Determine dependencies to install
    dependencies: list[str] = list(COMMON_DEPENDENCIES)
    if component:
        if component in COMPONENTS:
            deps = COMPONENTS[component]["dependencies"]
            dependencies.extend(cast("list[str]", deps))
        else:
            print(f"Unknown component: {component}")
            return False
    else:
        # Install all dependencies from all components
        for comp_info in COMPONENTS.values():
            deps = comp_info["dependencies"]
            dependencies.extend(cast("list[str]", deps))

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_dependencies: list[str] = []
    for dep in dependencies:
        if dep not in seen:
            seen.add(dep)
            unique_dependencies.append(dep)

    # Install dependencies
    print(f"Installing {len(unique_dependencies)} dependencies...")
    if verbose:
        for dep in unique_dependencies:
            print(f"  - {dep}")

    cmd = [sys.executable, "-m", "pip", "install", *unique_dependencies]
    if verbose:
        print(f"Running: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, capture_output=not verbose, text=True, check=True)
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        if not verbose and e.stderr:
            print(e.stderr)
        return False


def setup_directories(component: str | None, verbose: bool) -> bool:
    """Set up and verify test directories."""
    # Ensure test directory exists
    TEST_DIR.mkdir(exist_ok=True)

    # Create __init__.py file in test directory if it doesn't exist
    init_file = TEST_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Test package."""\n')
        if verbose:
            print(f"Created {init_file}")

    # Set up component-specific directories
    components_to_setup = [component] if component else COMPONENTS.keys()

    for comp in components_to_setup:
        if comp not in COMPONENTS:
            print(f"Unknown component: {comp}")
            continue

        comp_test_dir: Path = cast("Path", COMPONENTS[comp]["test_dir"])
        comp_test_dir.mkdir(exist_ok=True)

        # Create __init__.py in component test directory
        comp_init_file = comp_test_dir / "__init__.py"
        if not comp_init_file.exists():
            comp_init_file.write_text(f'"""Test package for {comp}."""\n')
            if verbose:
                print(f"Created {comp_init_file}")

        # Create unit and integration test directories
        unit_dir = comp_test_dir / "unit"
        unit_dir.mkdir(exist_ok=True)
        unit_init_file = unit_dir / "__init__.py"
        if not unit_init_file.exists():
            unit_init_file.write_text(f'"""Unit tests for {comp}."""\n')
            if verbose:
                print(f"Created {unit_init_file}")

        integration_dir = comp_test_dir / "integration"
        integration_dir.mkdir(exist_ok=True)
        integration_init_file = integration_dir / "__init__.py"
        if not integration_init_file.exists():
            integration_init_file.write_text(f'"""Integration tests for {comp}."""\n')
            if verbose:
                print(f"Created {integration_init_file}")

        # Create pytest.ini for component if it doesn't exist
        pytest_ini = comp_test_dir / "pytest.ini"
        if not pytest_ini.exists():
            if comp == "corpus_svc":
                # Special settings for retrieval tests due to asyncio loop issues
                pytest_ini.write_text(
                    "[pytest]\nasyncio_mode = auto\nasyncio_default_fixture_loop_scope = session\n"
                )
            else:
                pytest_ini.write_text("[pytest]\nasyncio_mode = auto\n")
            if verbose:
                print(f"Created {pytest_ini}")

    print("Test directories set up successfully")
    return True


def setup_environment_variables(component: str | None, verbose: bool) -> bool:
    """Set up environment variables for testing."""
    # Determine which environment variables to set
    env_vars: dict[str, str] = {}
    if component:
        if component in COMPONENTS:
            env_vars.update(cast("dict[str, str]", COMPONENTS[component]["env_vars"]))
        else:
            print(f"Unknown component: {component}")
            return False
    else:
        # Set environment variables for all components
        env_vars = {"PYTHONPATH": str(PROJECT_ROOT), "LOG_LEVEL": "DEBUG"}

        # Add component-specific vars with component-specific prefixes to avoid conflicts
        for comp, comp_info in COMPONENTS.items():
            comp_env = cast("dict[str, str]", comp_info["env_vars"])
            for key, value in comp_env.items():
                if key != "PYTHONPATH" and key != "LOG_LEVEL":
                    env_vars[f"{comp.upper()}_{key}"] = value

    # Print environment variables
    print(f"Setting up {len(env_vars)} environment variables...")
    if verbose:
        for key, value in env_vars.items():
            print(f"  - {key}={value}")

    # Write to canonical test env file (gitignored; credentials only in env files)
    env_file = ENV_TEST
    env_file.parent.mkdir(parents=True, exist_ok=True)
    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"Environment variables written to {env_file}")
    print("To use: set -a && source config/env/env.test && set +a")
    print("Or from Python: use ops/testing/load_test_env.load_test_env()\n")

    return True


def setup_mock_configs(component: str | None, verbose: bool, force: bool) -> bool:
    """Set up mock configuration files for testing."""
    mocks_dir = TEST_DIR / "mocks"
    mocks_dir.mkdir(exist_ok=True)

    # Create mock configuration files
    if component is None or component == "embedding":
        # Create mock embedding service config
        embedding_config = mocks_dir / "embedding_config.yaml"
        if not embedding_config.exists() or force:
            with open(embedding_config, "w") as f:
                f.write(
                    """
providers:
  - name: openai
    type: openai
    connection:
      api_key: ${EMBEDDING_API_KEY}
      base_url: https://api.openai.com/v1
    models:
      - id: text-embedding-ada-002
        dimensions: 1536
        max_input_length: 8191
        token_limit: 8191
        pricing:
          per_token: 0.0000001
          per_1k_tokens: 0.0001
  - name: local
    type: huggingface
    connection:
      model_path: /opt/models/all-MiniLM-L6-v2
    models:
      - id: all-MiniLM-L6-v2
        dimensions: 384
        max_input_length: 512
        token_limit: 512
        pricing:
          per_token: 0.0
          per_1k_tokens: 0.0
defaults:
  provider: openai
  model: text-embedding-ada-002
                """
                )
            if verbose:
                print(f"Created {embedding_config}")

    if component is None or component == "corpus_svc":
        # Create mock Qdrant client responses
        qdrant_mocks = mocks_dir / "qdrant_responses.json"
        if not qdrant_mocks.exists() or force:
            with open(qdrant_mocks, "w") as f:
                json.dump(
                    {
                        "search": {
                            "result": [
                                {
                                    "id": "chunk1",
                                    "score": 0.95,
                                    "payload": {
                                        "document_id": "doc1",
                                        "chunk_index": 0,
                                        "content": "This is a test chunk content.",
                                    },
                                },
                                {
                                    "id": "chunk2",
                                    "score": 0.85,
                                    "payload": {
                                        "document_id": "doc1",
                                        "chunk_index": 1,
                                        "content": "This is another test chunk content.",
                                    },
                                },
                            ]
                        },
                        "collection_info": {
                            "status": "green",
                            "vectors_count": 1000,
                            "points_count": 1000,
                            "config": {"params": {"vectors": {"size": 384, "distance": "Cosine"}}},
                        },
                    },
                    f,
                    indent=2,
                )
            if verbose:
                print(f"Created {qdrant_mocks}")

        # Create mock document templates
        doc_templates = mocks_dir / "document_templates.json"
        if not doc_templates.exists() or force:
            with open(doc_templates, "w") as f:
                json.dump(
                    {
                        "pdf": {
                            "id": "test-pdf-id",
                            "title": "Test PDF Document",
                            "source": "Test Source",
                            "author": "Test Author",
                            "file_type": "application/pdf",
                            "checksum": "abc123checksum",
                            "file_size": 12345,
                            "state": "PENDING",
                            "content_compressed": "compressed_content_placeholder",
                            "compression_ratio": 0.5,
                            "metadata": {"pages": 10, "created_date": "2025-05-17"},
                            "tags": ["test", "pdf", "mock"],
                            "classification": "public",
                        },
                        "txt": {
                            "id": "test-txt-id",
                            "title": "Test Text Document",
                            "source": "Test Source",
                            "author": "Test Author",
                            "file_type": "text/plain",
                            "checksum": "def456checksum",
                            "file_size": 5678,
                            "state": "PENDING",
                            "content_compressed": "compressed_content_placeholder",
                            "compression_ratio": 0.7,
                            "metadata": {"encoding": "utf-8", "created_date": "2025-05-17"},
                            "tags": ["test", "txt", "mock"],
                            "classification": "internal",
                        },
                    },
                    f,
                    indent=2,
                )
            if verbose:
                print(f"Created {doc_templates}")

    return True


def setup_conftest(component: str | None, verbose: bool, force: bool) -> bool:
    """Set up the conftest.py files with pytest fixtures."""

    # Handle global conftest.py
    global_conftest = TEST_DIR / "conftest.py"
    if not global_conftest.exists() or force:
        with open(global_conftest, "w") as f:
            f.write(
                '''"""
Global pytest fixtures for all tests.
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Add the project root to the Python path if not already there
project_root = Path(__file__).resolve().parent.parent
# Load environment variables from config/env/env.test (credentials only in env files)
load_dotenv(project_root / "config" / "env" / "env.test")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def base_dir():
    """Return the base directory of the project."""
    return project_root

@pytest.fixture(scope="session")
def test_dir():
    """Return the test directory of the project."""
    return project_root / "tests"

@pytest.fixture(scope="session")
def mocks_dir():
    """Return the mocks directory for test fixtures."""
    return project_root / "tests" / "mocks"
'''
            )
        if verbose:
            print(f"Created {global_conftest}")

    # Create component-specific conftest.py files if needed
    components_to_setup = [component] if component else COMPONENTS.keys()

    for comp in components_to_setup:
        if comp not in COMPONENTS:
            print(f"Unknown component: {comp}")
            continue

        comp_test_dir = cast("Path", COMPONENTS[comp]["test_dir"])
        comp_conftest = comp_test_dir / "conftest.py"

        if comp == "corpus_svc" and (not comp_conftest.exists() or force):
            with open(comp_conftest, "w") as f:
                f.write(
                    '''"""
Retrieval service pytest fixtures.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# Add the project root to the Python path if not already there
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import needed modules
from src.corpus_svc.app.db.connection import get_db_pool, close_db_pool
from src.corpus_svc.app.db.models import setup_db_schema
from src.corpus_svc.app.main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def db_pool():
    """Create a database pool for tests."""
    # Use test database settings
    os.environ["PG_DATABASE"] = "aio-test"

    # Get the database pool
    pool = await get_db_pool()

    # Set up the database schema
    await setup_db_schema(pool)

    yield pool

    # Close the database pool
    await close_db_pool()

@pytest_asyncio.fixture
async def db_connection(db_pool):
    """Get a database connection from the pool."""
    async with db_pool.acquire() as conn:
        transaction = conn.transaction()
        await transaction.start()
        yield conn
        await transaction.rollback()

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def qdrant_mock_responses():
    """Load mock Qdrant responses from JSON file."""
    mocks_file = project_root / "tests" / "mocks" / "qdrant_responses.json"
    if mocks_file.exists():
        with open(mocks_file, "r") as f:
            return json.load(f)
    return {}

@pytest.fixture
def document_templates():
    """Load document templates from JSON file."""
    templates_file = project_root / "tests" / "mocks" / "document_templates.json"
    if templates_file.exists():
        with open(templates_file, "r") as f:
            return json.load(f)
    return {}
'''
                )
            if verbose:
                print(f"Created {comp_conftest}")

        elif comp == "embedding" and (not comp_conftest.exists() or force):
            with open(comp_conftest, "w") as f:
                f.write(
                    '''"""
Embedding service pytest fixtures.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path if not already there
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import needed modules
from src.embedding.app.main import app
from src.embedding.app.config.models import Config, ProviderConfig, ModelConfig, OpenAIConnectionConfig

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def embedding_config():
    """Load embedding configuration from YAML file."""
    config_file = project_root / "tests" / "mocks" / "embedding_config.yaml"
    if config_file.exists():
        from src.embedding.app.config.loader import load_config
        return load_config(config_file)

    # Return a default test configuration
    return Config(
        providers=[
            ProviderConfig(
                name="test-openai",
                type="openai",
                connection=OpenAIConnectionConfig(
                    api_key="test-key",
                    base_url="https://api.openai.com/v1"
                ),
                models=[
                    ModelConfig(
                        id="text-embedding-ada-002",
                        dimensions=1536,
                        max_input_length=8191,
                        token_limit=8191,
                        pricing={"per_token": 0.0000001, "per_1k_tokens": 0.0001}
                    )
                ]
            )
        ],
        defaults={
            "provider": "test-openai",
            "model": "text-embedding-ada-002"
        }
    )

@pytest.fixture
def openai_mock_responses():
    """Mock responses for OpenAI API calls."""
    return {
        "embedding": {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1, 0.2, 0.3, 0.4] * 384,
                    "index": 0
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {
                "prompt_tokens": 5,
                "total_tokens": 5
            }
        }
    }
'''
                )
            if verbose:
                print(f"Created {comp_conftest}")

        elif comp == "orchestrator" and (not comp_conftest.exists() or force):
            with open(comp_conftest, "w") as f:
                f.write(
                    '''"""
Backend service pytest fixtures.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient

# Add the project root to the Python path if not already there
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import needed modules
from src.orchestrator.app.main import app
from src.orchestrator.app.utils.auth import jwt_validator

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def test_token():
    """Create a test JWT token."""
    payload = {
        "sub": "test-user",
        "name": "Test User",
        "email": "test@example.com",
        "roles": ["user"]
    }
    return jwt_validator.create_access_token(data=payload)

@pytest.fixture
def test_admin_token():
    """Create a test admin JWT token."""
    payload = {
        "sub": "admin-user",
        "name": "Admin User",
        "email": "admin@example.com",
        "roles": ["admin", "user"]
    }
    return jwt_validator.create_access_token(data=payload)

@pytest.fixture
def llm_mock_responses():
    """Mock responses for LLM API calls."""
    return {
        "text_completion": {
            "id": "cmpl-test123",
            "object": "text_completion",
            "created": 1684862334,
            "model": "gpt-3.5-turbo",
            "choices": [
                {
                    "text": "This is a mock LLM response.",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18
            }
        }
    }
'''
                )
            if verbose:
                print(f"Created {comp_conftest}")

    return True


def setup_test_vectors_file(verbose: bool, force: bool) -> bool:
    """Set up a test vectors file with sample embeddings."""
    mocks_dir = TEST_DIR / "mocks"
    mocks_dir.mkdir(exist_ok=True)

    vectors_file = mocks_dir / "test_vectors.json"
    if not vectors_file.exists() or force:
        # Create a sample embedding vector (384 dimensions for all-MiniLM-L6-v2)
        # Values are between -1 and 1, normalized
        import random

        random.seed(42)  # For reproducibility

        # Create 5 sample vectors
        vectors = {}
        for i in range(5):
            # Create a normalized vector
            vector = [random.uniform(-1, 1) for _ in range(384)]
            # Normalize to unit length
            magnitude = sum(x * x for x in vector) ** 0.5
            normalized_vector = [x / magnitude for x in vector]

            vectors[f"test_document_{i}"] = {
                "id": f"doc{i}",
                "vector": normalized_vector,
                "metadata": {
                    "title": f"Test Document {i}",
                    "content": f"This is test document {i} with sample content.",
                },
            }

        with open(vectors_file, "w") as f:
            json.dump(vectors, f)

        if verbose:
            print(f"Created {vectors_file} with 5 sample embedding vectors")

    return True


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Set up the test environment")
    parser.add_argument(
        "--component",
        choices=["orchestrator", "embedding", "corpus_svc"],
        help="Component to set up the environment for",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument(
        "--force", action="store_true", help="Force overwrite of existing configurations"
    )

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print(" Test Environment Setup ".center(80, "="))
    print("=" * 80 + "\n")

    if args.component:
        print(f"Setting up environment for component: {args.component.upper()}")
    else:
        print("Setting up environment for ALL COMPONENTS")

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Source directory: {SRC_DIR}")
    print(f"Tests directory: {TEST_DIR}")
    print("")

    # Run the setup steps
    # 1. Install dependencies
    if not install_dependencies(args.component, args.verbose, args.skip_deps):
        print("Failed to install dependencies")
        return 1

    # 2. Set up directories
    if not setup_directories(args.component, args.verbose):
        print("Failed to set up directories")
        return 1

    # 3. Set up environment variables
    if not setup_environment_variables(args.component, args.verbose):
        print("Failed to set up environment variables")
        return 1

    # 4. Set up mock configurations
    if not setup_mock_configs(args.component, args.verbose, args.force):
        print("Failed to set up mock configurations")
        return 1

    # 5. Set up conftest.py files
    if not setup_conftest(args.component, args.verbose, args.force):
        print("Failed to set up conftest.py files")
        return 1

    # 6. Set up test vectors file
    if not setup_test_vectors_file(args.verbose, args.force):
        print("Failed to set up test vectors file")
        return 1

    print("\n" + "=" * 80)
    print(" Test Environment Setup Complete ".center(80, "="))
    print("=" * 80 + "\n")

    print("Next Steps:")
    print("1. Run fix_test_imports.py to resolve repository method signature issues:")
    print("   python temp_scripts/fix_test_imports.py")
    print("2. Run component-specific tests:")
    print("   python temp_scripts/run_comprehensive_tests.py --component corpus_svc")
    print("3. Run the full test suite:")
    print("   python temp_scripts/run_full_test_suite.py")
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
