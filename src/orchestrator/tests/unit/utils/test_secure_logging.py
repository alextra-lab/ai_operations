"""
Unit tests for Secure Logging Utilities.

Tests redaction, hash generation, and configuration handling.
"""

import os
from unittest.mock import patch

from src.orchestrator.app.utils.secure_logging import (
    _hash_value,
    get_redaction_status,
    redact_session_id,
)


class TestHashGeneration:
    """Test hash utility function."""

    def test_hash_value_basic(self):
        """Test basic hash generation."""
        hash1 = _hash_value("test", length=8)
        assert len(hash1) == 8
        assert isinstance(hash1, str)

    def test_hash_value_deterministic(self):
        """Test hash is deterministic."""
        hash1 = _hash_value("test")
        hash2 = _hash_value("test")
        assert hash1 == hash2

    def test_hash_value_unique(self):
        """Test different inputs produce different hashes."""
        hash1 = _hash_value("test1")
        hash2 = _hash_value("test2")
        assert hash1 != hash2

    def test_hash_empty_string(self):
        """Test empty string handling."""
        result = _hash_value("")
        assert result == "[empty]"


class TestQueryRedaction:
    """Test query redaction with different settings."""

    @patch.dict(os.environ, {"REDACT_LOGS": "false"})
    def test_query_no_redaction(self):
        """Test query is not redacted when REDACT_LOGS=false."""
        # Reload module to pick up env var
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        query = "What is a SOC?"
        result = secure_logging.redact_query(query)
        assert result == query  # Unchanged

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "full"})
    def test_query_full_redaction(self):
        """Test query fully redacted in full mode."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        query = "Investigate alert #12345"
        result = secure_logging.redact_query(query)
        assert result == "[REDACTED]"

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "partial"})
    def test_query_partial_redaction(self):
        """Test query partially redacted with length and hash."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        query = "What is threat intelligence?"
        result = secure_logging.redact_query(query)

        assert "[REDACTED:" in result
        assert "chars" in result
        assert "hash=" in result
        assert "threat intelligence" not in result


class TestResponseRedaction:
    """Test response redaction."""

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "partial"})
    def test_response_redaction(self):
        """Test response content is redacted."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        response = "Here are the IOCs: IP 192.168.1.1, Hash abc123..."
        result = secure_logging.redact_response(response)

        assert "[REDACTED:" in result
        assert "192.168.1.1" not in result


class TestSessionIdRedaction:
    """Test session ID redaction."""

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "partial"})
    def test_session_id_partial_redaction(self):
        """Test session ID shows prefix + hash."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        session_id = "session_1761410740520_tovg41p15"
        result = secure_logging.redact_session_id(session_id)

        assert "session_" in result
        assert "hash=" in result
        assert "tovg41p15" not in result  # Unique part redacted

    def test_session_id_none_handling(self):
        """Test None session ID handling."""
        result = redact_session_id(None)
        assert result == "none"


class TestRequestBodyRedaction:
    """Test full request body redaction."""

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "partial"})
    def test_request_body_redacts_sensitive_fields(self):
        """Test sensitive fields are redacted in request body."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        body = {
            "query": "Investigate incident #12345",
            "session_id": "session_abc123",
            "use_case_id": "uuid-123",
            "stream": True,
        }

        redacted = secure_logging.redact_request_body(body)

        # Sensitive fields redacted
        assert "[REDACTED:" in redacted["query"]
        assert "incident #12345" not in str(redacted)

        # Non-sensitive fields preserved
        assert redacted["stream"] is True
        assert redacted["use_case_id"] == "uuid-123"

    @patch.dict(os.environ, {"REDACT_LOGS": "false"})
    def test_request_body_no_redaction(self):
        """Test no redaction when disabled."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        body = {"query": "Sensitive data", "context": {"key": "value"}}
        redacted = secure_logging.redact_request_body(body)

        assert redacted == body  # Unchanged

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "partial"})
    def test_request_body_redacts_multiple_fields(self):
        """Test all sensitive fields are redacted."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        body = {
            "query": "Query text",
            "response": "Response text",
            "content": "Content text",
            "message": "Message text",
            "context": "Context text",
        }

        redacted = secure_logging.redact_request_body(body)

        for field in ["query", "response", "content", "message", "context"]:
            assert "[REDACTED:" in redacted[field]


class TestRedactionStatus:
    """Test redaction status reporting."""

    def test_get_redaction_status(self):
        """Test redaction status returns current config."""
        status = get_redaction_status()

        assert "redaction_enabled" in status
        assert "redaction_level" in status
        assert isinstance(status["redaction_enabled"], bool)
        assert status["redaction_level"] in ["none", "partial", "full"]


class TestRedactionLevels:
    """Test all redaction levels work correctly."""

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "none"})
    def test_redaction_level_none(self):
        """Test level=none does not redact."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        query = "Sensitive query"
        result = secure_logging.redact_query(query)
        assert result == query

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "partial"})
    def test_redaction_level_partial(self):
        """Test level=partial shows length and hash."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        query = "Sensitive query"
        result = secure_logging.redact_query(query)
        assert "[REDACTED:" in result
        assert "chars" in result
        assert "hash=" in result

    @patch.dict(os.environ, {"REDACT_LOGS": "true", "LOG_REDACTION_LEVEL": "full"})
    def test_redaction_level_full(self):
        """Test level=full completely redacts."""
        import importlib

        from src.orchestrator.app.utils import secure_logging

        importlib.reload(secure_logging)

        query = "Sensitive query"
        result = secure_logging.redact_query(query)
        assert result == "[REDACTED]"
