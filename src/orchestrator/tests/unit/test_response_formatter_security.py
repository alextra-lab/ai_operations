"""
Unit tests for response_formatter security flag parsing.

Tests the enhanced security flag parsing functionality for P2-FIX-09.
"""

from src.orchestrator.app.orchestrator.response_formatter import ResponseFormatter


class TestSecurityFlagParsing:
    """Test suite for security flag parsing in response formatter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResponseFormatter()

    def test_parse_security_flags_empty_details(self):
        """Test parsing security flags with empty details."""
        # Arrange
        guard_details = {}

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert result["pii_detected"] is False
        assert result["toxicity_detected"] is False
        assert result["jailbreak_attempt"] is False
        assert result["content_filtered"] is False
        assert result["blocked_categories"] == []

    def test_parse_security_flags_with_scanners(self):
        """Test parsing security flags with actual LLM Guard scanner names."""
        # Arrange
        guard_details = {
            "scanners": {
                "anonymize": {"passed": False, "score": 0.8},  # Actual scanner name
                "gibberish": {"passed": True, "score": 0.2},  # Actual scanner name
            }
        }

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert result["pii_detected"] is True
        assert result["gibberish_detected"] is False
        assert "anonymize" in result["blocked_categories"]

    def test_parse_security_flags_pii_detection(self):
        """Test PII detection flag parsing with actual anonymize scanner."""
        # Arrange
        guard_details = {"scanners": {"anonymize": {"passed": False, "score": 0.8}}}

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert result["pii_detected"] is True
        assert "anonymize" in result["blocked_categories"]
        assert result["content_filtered"] is True  # Should be true since PII detected

    def test_parse_security_flags_toxicity_detection(self):
        """Test toxicity flag (legacy - not implemented in current LLM Guard)."""
        # Arrange - No toxicity scanner exists in actual implementation
        guard_details = {"scanners": {"language": {"passed": True, "score": 0.1}}}

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert result["toxicity_detected"] is False  # Legacy flag always False
        assert result["content_filtered"] is False

    def test_parse_security_flags_jailbreak_detection(self):
        """Test jailbreak/prompt injection detection with actual scanner."""
        # Arrange
        guard_details = {
            "scanners": {
                "prompt_injection": {"passed": False, "score": 0.9},
            }
        }

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert result["jailbreak_attempt"] is True
        assert "prompt_injection" in result["blocked_categories"]
        assert result["content_filtered"] is True

    def test_parse_security_flags_secrets_detection(self):
        """Test secrets detection with actual scanners."""
        # Arrange
        guard_details = {
            "scanners": {
                "secrets": {"passed": False, "score": 1.0},
                "regex": {"passed": False, "score": 0.8},
            }
        }

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert result["secrets_detected"] is True
        assert "secrets" in result["blocked_categories"]
        assert "regex" in result["blocked_categories"]
        assert result["content_filtered"] is True

    def test_parse_security_flags_multiple_blocked_categories(self):
        """Test parsing multiple actual LLM Guard scanners."""
        # Arrange - Use actual scanner names
        guard_details = {
            "scanners": {
                "anonymize": {"passed": False, "score": 0.7},
                "prompt_injection": {"passed": False, "score": 0.9},
                "secrets": {"passed": False, "score": 1.0},
            }
        }

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert len(result["blocked_categories"]) == 3
        assert "anonymize" in result["blocked_categories"]
        assert "prompt_injection" in result["blocked_categories"]
        assert "secrets" in result["blocked_categories"]
        assert result["pii_detected"] is True
        assert result["jailbreak_attempt"] is True
        assert result["secrets_detected"] is True
        assert result["content_filtered"] is True

    def test_parse_security_flags_no_blocked_categories(self):
        """Test parsing when nothing is blocked."""
        # Arrange
        guard_details = {
            "scanners": {
                "pii": {"blocked": False, "risk_score": 0.1},
                "toxicity": {"blocked": False, "risk_score": 0.05},
            }
        }

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert result["pii_detected"] is False
        assert result["toxicity_detected"] is False
        assert len(result["blocked_categories"]) == 0

    def test_check_scanner_flag_with_dict_blocked(self):
        """Test _check_scanner_flag with dictionary result (blocked)."""
        # Arrange
        scanners = {"pii_scanner": {"blocked": True}}

        # Act
        result = self.formatter._check_scanner_flag(scanners, ["pii"])

        # Assert
        assert result is True

    def test_check_scanner_flag_with_dict_sanitized(self):
        """Test _check_scanner_flag with dictionary result (sanitized)."""
        # Arrange
        scanners = {"toxicity_scanner": {"sanitized": True}}

        # Act
        result = self.formatter._check_scanner_flag(scanners, ["toxicity"])

        # Assert
        assert result is True

    def test_check_scanner_flag_with_dict_detected(self):
        """Test _check_scanner_flag with dictionary result (detected)."""
        # Arrange
        scanners = {"jailbreak": {"detected": True}}

        # Act
        result = self.formatter._check_scanner_flag(scanners, ["jailbreak"])

        # Assert
        assert result is True

    def test_check_scanner_flag_with_dict_high_risk_score(self):
        """Test _check_scanner_flag with high risk score."""
        # Arrange
        scanners = {"suspicious_scanner": {"risk_score": 0.8}}

        # Act
        result = self.formatter._check_scanner_flag(scanners, ["suspicious"])

        # Assert
        assert result is True

    def test_check_scanner_flag_with_dict_low_risk_score(self):
        """Test _check_scanner_flag with low risk score."""
        # Arrange
        scanners = {"safe_scanner": {"risk_score": 0.3}}

        # Act
        result = self.formatter._check_scanner_flag(scanners, ["safe"])

        # Assert
        assert result is False

    def test_check_scanner_flag_with_boolean_true(self):
        """Test _check_scanner_flag with boolean True result."""
        # Arrange
        scanners = {"pii": True}

        # Act
        result = self.formatter._check_scanner_flag(scanners, ["pii"])

        # Assert
        assert result is True

    def test_check_scanner_flag_with_boolean_false(self):
        """Test _check_scanner_flag with boolean False result."""
        # Arrange
        scanners = {"pii": False}

        # Act
        result = self.formatter._check_scanner_flag(scanners, ["pii"])

        # Assert
        assert result is False

    def test_check_scanner_flag_no_match(self):
        """Test _check_scanner_flag when no scanners match keywords."""
        # Arrange
        scanners = {"unrelated_scanner": {"blocked": True}}

        # Act
        result = self.formatter._check_scanner_flag(scanners, ["pii", "toxicity"])

        # Assert
        assert result is False

    def test_check_scanner_flag_multiple_keywords(self):
        """Test _check_scanner_flag with multiple matching keywords."""
        # Arrange
        scanners = {
            "pii_anonymize_scanner": {"blocked": True},
            "sensitive_data_detector": {"blocked": False},
        }

        # Act
        result = self.formatter._check_scanner_flag(
            scanners, ["pii", "anonymize", "sensitive_data"]
        )

        # Assert
        assert result is True  # First scanner matches and is blocked

    def test_parse_security_flags_preserves_original_data(self):
        """Test that parsing preserves original guard details."""
        # Arrange
        guard_details = {
            "scanners": {"pii": {"blocked": True}},
            "custom_field": "custom_value",
            "risk_assessment": "high",
        }

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        assert result["custom_field"] == "custom_value"
        assert result["risk_assessment"] == "high"
        assert "scanners" in result

    def test_parse_security_flags_deduplicates_categories(self):
        """Test that blocked categories are deduplicated."""
        # Arrange
        guard_details = {
            "scanners": {
                "scanner1": {
                    "blocked": True,
                    "blocked_categories": ["pii", "sensitive"],
                },
                "scanner2": {"blocked": True, "blocked_categories": ["pii", "toxic"]},
            }
        }

        # Act
        result = self.formatter._parse_security_flags(guard_details)

        # Assert
        # "pii" should only appear once despite being in multiple scanners
        assert result["blocked_categories"].count("pii") == 1
        assert "sensitive" in result["blocked_categories"]
        assert "toxic" in result["blocked_categories"]


class TestSecurityFlagsIntegration:
    """Integration tests for security flags in full metrics consolidation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResponseFormatter()

    def test_consolidate_metrics_with_security_flags(self):
        """Test that security flags are included in consolidated metrics."""
        # Arrange
        from src.orchestrator.app.schemas.llm import LLMResponse, ModelType

        llm_response = LLMResponse(
            response="Test response",
            model_used=ModelType.QUERY,  # Use enum, not string
            tokens_used=100,
            processing_time=1.0,
            metadata={"tokens_in": 50, "tokens_out": 50},
        )

        guard_metrics = {
            "risk_score": 0.3,
            "modified": True,
            "details": {
                "scanners": {
                    "anonymize": {"passed": False, "score": 0.8},  # Actual scanner name
                    "prompt_injection": {
                        "passed": True,
                        "score": 0.1,
                    },  # Actual scanner name
                }
            },
        }

        # Act
        consolidated = self.formatter._consolidate_metrics(
            llm_response=llm_response,
            sources=[],
            retrieval_metrics=None,
            guard_metrics=guard_metrics,
        )

        # Assert
        assert consolidated.guard is not None
        assert consolidated.guard.details["pii_detected"] is True
        assert consolidated.guard.details["jailbreak_attempt"] is False
        assert "anonymize" in consolidated.guard.details["blocked_categories"]
        assert consolidated.guard.details["content_filtered"] is True
