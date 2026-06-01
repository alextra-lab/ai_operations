"""
LLM-Guard validation logic for protecting against prompt injection and harmful content.

This module defines the main LLMGuard class that uses multiple scanners
to detect various types of malicious or harmful input patterns.
The scanners include anonymization, prompt injection, secrets detection, gibberish detection, and regex checks.
It also incorporates best practices like fail-fast scanning and caching.
"""

import logging
import os
import time  # For TTLCache timer
from threading import RLock  # Correct import for RLock
from typing import TYPE_CHECKING, Any

from cachetools import LRUCache, TTLCache

if TYPE_CHECKING:
    from shared.config.schemas import LLMGuardConfig

_logger = logging.getLogger(__name__)
from llm_guard.input_scanners import (
    Anonymize,
    Gibberish,
    Language,
    PromptInjection,
    Regex,
    Secrets,
)
from llm_guard.input_scanners.anonymize_helpers import DISTILBERT_AI4PRIVACY_v2_CONF
from llm_guard.input_scanners.gibberish import DEFAULT_MODEL as GIB_MODEL
from llm_guard.input_scanners.gibberish import MatchType as GMatchType
from llm_guard.input_scanners.language import DEFAULT_MODEL as LANG_MODEL
from llm_guard.input_scanners.language import MatchType as LMatchType
from llm_guard.input_scanners.prompt_injection import V2_SMALL_MODEL as PI_MODEL
from llm_guard.input_scanners.prompt_injection import MatchType as PIMatchType
from llm_guard.input_scanners.regex import MatchType as RMatchType
from llm_guard.vault import Vault

_MODELS_OVERRIDE_PATH: str | None = None

# Scanner model paths are configured at runtime in configure_models() from
# LLMGuardConfig directory names (ADR-073 D5).


def get_models_base_path() -> str:
    """
    Get the base path for models, environment-aware like import statements.

    Priority order:
    1. LLM_GUARD_MODELS_PATH environment variable (explicit override)
    2. /app/models (container environment)
    3. ./models (local development)
    4. ../models (testing from subdirectory)
    5. /workspace/data/llm-guard-models (workspace development)

    Returns:
        str: The base path where models are stored
    """
    # 0. Explicit override provided via configuration
    if _MODELS_OVERRIDE_PATH and os.path.exists(_MODELS_OVERRIDE_PATH):
        return _MODELS_OVERRIDE_PATH

    # 1. Shared config override
    from shared.config.loader import load_llm_guard_config

    env_path = load_llm_guard_config().models_path
    if env_path and os.path.exists(env_path):
        return env_path

    # 2. Container environment
    container_path = "/app/models"
    if os.path.exists(container_path):
        return container_path

    # 3. Workspace-relative path (for development) - MOVED UP IN PRIORITY
    workspace_path = "/workspace/data/llm-guard-models"
    if os.path.exists(workspace_path):
        return workspace_path

    # 4. Local development (relative to current working directory)
    local_path = "./models"
    if os.path.exists(local_path):
        return os.path.abspath(local_path)

    # 5. Testing from subdirectory (go up one level)
    parent_path = "../models"
    if os.path.exists(parent_path):
        return os.path.abspath(parent_path)

    # 6. Fallback to container path (will fail gracefully if models not found)
    return container_path


def get_model_path(model_name: str) -> str:
    """
    Get the full path for a specific model.

    Args:
        model_name: Name of the model directory

    Returns:
        str: Full path to the model
    """
    base_path = get_models_base_path()
    return os.path.join(base_path, model_name)


def verify_model_path(path: str, _model_name: str) -> bool:
    """
    Verify that a model path exists and contains required files.

    Args:
        path: Path to check
        model_name: Human-readable model name for logging

    Returns:
        bool: True if model is available, False otherwise
    """
    if not os.path.exists(path):
        return False

    # Check for common model files
    required_files = ["config.json"]
    for file in required_files:
        if os.path.exists(os.path.join(path, file)):
            return True

    # If no config.json, check if it's a directory with model files
    if os.path.isdir(path):
        files = os.listdir(path)
        # Look for any model-related files
        model_extensions = [".bin", ".safetensors", ".onnx", ".json"]
        if any(any(f.endswith(ext) for ext in model_extensions) for f in files):
            return True

    return False


def configure_models(config: "LLMGuardConfig | None" = None) -> None:
    """
    Configure all models with environment-aware paths.
    Works both inside and outside containers.

    Model directory names are sourced from ``LLMGuardConfig`` (ADR-073 D5), so
    they can be overridden via environment variables without code changes.
    """
    if config is None:
        from shared.config.loader import load_llm_guard_config

        config = load_llm_guard_config()

    _logger.info("Configuring LLM-Guard models")

    # PII Detection Model Configuration
    pii_model_path = get_model_path(config.pii_model_dir)
    if verify_model_path(pii_model_path, "PII Detection"):
        DISTILBERT_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].path = pii_model_path
        DISTILBERT_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].onnx_path = pii_model_path
        DISTILBERT_AI4PRIVACY_v2_CONF["DEFAULT_MODEL"].kwargs.update(
            {"local_files_only": True, "trust_remote_code": False}
        )
        _logger.info("PII Detection model configured")
    else:
        _logger.warning("PII Detection model not found")

    # Gibberish Detection Model Configuration
    gibberish_model_path = get_model_path(config.gibberish_model_dir)
    if verify_model_path(gibberish_model_path, "Gibberish Detection"):
        GIB_MODEL.path = gibberish_model_path
        GIB_MODEL.onnx_path = os.path.join(gibberish_model_path, "onnx")
        GIB_MODEL.onnx_subfolder = ""
        GIB_MODEL.kwargs.update({"local_files_only": True, "trust_remote_code": False})
        _logger.info("Gibberish Detection model configured")
    else:
        _logger.warning("Gibberish Detection model not found")

    # Language Detection Model Configuration
    language_model_path = get_model_path(config.language_model_dir)
    if verify_model_path(language_model_path, "Language Detection"):
        LANG_MODEL.path = language_model_path
        LANG_MODEL.onnx_path = language_model_path
        LANG_MODEL.onnx_subfolder = ""
        LANG_MODEL.onnx_filename = "model_quantized.onnx"
        LANG_MODEL.kwargs.update(
            {
                "local_files_only": True,
                "trust_remote_code": False,
            }
        )
        _logger.info("Language Detection model configured")
    else:
        _logger.warning("Language Detection model not found")

    # Prompt Injection Detection Model Configuration
    prompt_injection_model_path = get_model_path(config.prompt_injection_model_dir)
    if verify_model_path(prompt_injection_model_path, "Prompt Injection Detection"):
        PI_MODEL.path = prompt_injection_model_path
        PI_MODEL.onnx_path = os.path.join(prompt_injection_model_path, "onnx")
        PI_MODEL.onnx_subfolder = ""
        PI_MODEL.kwargs.update({"local_files_only": True, "trust_remote_code": False})
        _logger.info("Prompt Injection Detection model configured")
    else:
        _logger.warning("Prompt Injection Detection model not found")


def initialize_models(models_base_path: str | None = None) -> None:
    """
    Initialize model configuration using optional override path.
    """
    global _MODELS_OVERRIDE_PATH
    if models_base_path:
        _MODELS_OVERRIDE_PATH = models_base_path
    from shared.config.loader import load_llm_guard_config

    configure_models(config=load_llm_guard_config())


class LLMGuard:
    """
    Main class for LLM input validation and sanitization.

    This class initializes and manages multiple scanners for processing input text.
    It returns a sanitized version of the input along with a risk score and details from each scanner.
    Implements fail-fast and caching mechanisms.
    """

    def __init__(
        self,
        logger: Any,
        fail_fast: bool = False,
        cache_enabled: bool = False,  # General toggle for caching
        cache_max_size: int = 1000,
        cache_ttl_seconds: int = 3600,
        regex_engine: str = "llm_guard",
        secrets_engine: str = "llm_guard",
    ):
        """
        Initialize the LLMGuard with required scanners and configurations.

        Args:
            logger: Logger instance for recording validation and audit events.
            fail_fast: If True, stop scanning on the first detected issue. Defaults to False.
            cache_enabled: If True, enables caching of scan results. Defaults to False.
            cache_max_size: Maximum number of items in the cache. Defaults to 1000.
            cache_ttl_seconds: Time-to-live for cache entries in seconds. Defaults to 3600 (1 hour).
        """
        self.logger = logger
        self.fail_fast = fail_fast
        self.cache_enabled = cache_enabled
        self._cache_rlock = RLock()

        if self.cache_enabled:
            if cache_ttl_seconds > 0 and cache_max_size > 0:
                self.cache: TTLCache | LRUCache | None = TTLCache(
                    maxsize=cache_max_size, ttl=cache_ttl_seconds, timer=time.monotonic
                )  # Removed lock argument
                self.logger.info(
                    f"LLMGuard initialized with TTLCache (max_size={cache_max_size}, ttl={cache_ttl_seconds}s)."
                )
            elif cache_max_size > 0:
                self.cache = LRUCache(maxsize=cache_max_size)  # Removed lock argument
                self.logger.info(
                    f"LLMGuard initialized with LRUCache (max_size={cache_max_size}). TTL not configured."
                )
            else:
                self.cache = None  # Should not happen if cache_enabled is true and params are validated upstream
                self.logger.warning(
                    "LLMGuard cache_enabled is True, but cache_max_size or cache_ttl_seconds is invalid. Caching disabled."
                )
        else:
            self.cache = None
            self.logger.info("LLMGuard initialized with caching disabled.")

        # Initialize the vault for anonymization
        vault = Vault()

        # Per-scanner engine selection (LLG-04). Native ports drop the llm_guard
        # dependency; the default keeps the original llm-guard scanners so
        # behaviour is unchanged until a flag is flipped.
        from .scanners.regex_scanner import CREDENTIAL_PATTERNS, RegexScanner
        from .scanners.secrets_scanner import SecretsScanner

        regex_scanner: Any = (
            RegexScanner()
            if regex_engine == "native"
            else Regex(patterns=CREDENTIAL_PATTERNS, match_type=RMatchType.SEARCH)
        )
        secrets_scanner: Any = SecretsScanner() if secrets_engine == "native" else Secrets()

        # Set up the scanners with appropriate configurations.
        self.scanners = {
            "anonymize": Anonymize(
                vault, recognizer_conf=DISTILBERT_AI4PRIVACY_v2_CONF, use_onnx=True
            ),
            "prompt_injection": PromptInjection(
                threshold=0.92,
                match_type=PIMatchType.TRUNCATE_HEAD_TAIL,
                model=PI_MODEL,  # Path already updated
                use_onnx=True,
            ),
            "secrets": secrets_scanner,
            "gibberish": Gibberish(
                threshold=0.97,
                match_type=GMatchType.FULL,
                model=GIB_MODEL,
                use_onnx=True,  # Use ONNX for the madhurjindal Gibberish model
            ),
            "language": Language(  # Added Language scanner
                model=LANG_MODEL,  # Path already updated
                valid_languages=[
                    "en",
                    "fr",
                ],
                match_type=LMatchType.FULL,
                use_onnx=True,
            ),
            "regex": regex_scanner,
            # Note: The Language scanner and Code scanner remain commented out; uncomment or configure as needed.
        }

    def validate_input(
        self,
        input_text: str,
        user_id: str | None = None,
        request_id: str | None = None,
        _context: dict[str, str] | None = None,
        logger: Any | None = None,
    ) -> tuple[str, float, bool, dict[str, bool | float]]:
        """
        Validate and sanitize input text.

        This method runs all configured scanners on the input. It supports fail-fast scanning
        and caching of results.

        Args:
            input_text (str): The raw input text to be validated.
            user_id (Optional[str]): Optional user ID for audit.
            request_id (Optional[str]): Optional request ID for tracing.
            context (Optional[Dict[str, str]]): Optional context to aid in validation.

        Returns:
            Tuple[str, float, bool, Dict[str, Union[bool, float]]]:
                - Sanitized text (or original if no changes).
                - Overall risk score (0 to 1, higher indicates higher risk).
                - Boolean flag indicating if modifications were made.
                - Dictionary of detailed results from each scanner.
        """
        log = logger if logger is not None else self.logger
        if self.cache is not None:
            with self._cache_rlock:  # Ensure thread-safe access to cache
                cached_result = self.cache.get(input_text)
            if cached_result:
                log.debug(
                    "Cache hit for validation request",
                    extra={
                        "request_id2": request_id,
                        "user_id": user_id,
                        "input_length": len(input_text),
                    },
                )
                result: tuple[str, float, bool, dict[str, bool | float]] = cached_result
                return result

        sanitized_text = input_text
        original_input_text = input_text  # Keep a copy for cache key if text is modified
        modified = False
        scanner_results: dict[str, Any] = {}
        final_risk_score = 0.0

        for scanner_name, scanner in self.scanners.items():
            try:
                scan_result = scanner.scan(sanitized_text)
                current_scanner_failed = False

                if isinstance(scan_result, tuple):
                    if len(scan_result) == 3:  # (sanitized_text, is_valid, risk_score)
                        sanitized_text, is_valid, risk_score_from_scanner = scan_result
                        scanner_results[scanner_name] = {
                            "passed": is_valid,
                            "score": risk_score_from_scanner,
                        }
                        if not is_valid:
                            modified = True
                            current_scanner_failed = True
                    elif len(scan_result) == 2:  # (sanitized_text, scanner_result_val)
                        sanitized_text, scanner_result_val = scan_result
                        if isinstance(scanner_result_val, bool):
                            scanner_results[scanner_name] = {"passed": scanner_result_val}
                            if not scanner_result_val:
                                modified = True
                                current_scanner_failed = True
                        elif isinstance(
                            scanner_result_val, float
                        ):  # Assuming this float is a risk score
                            scanner_results[scanner_name] = {"score": scanner_result_val}
                            # Consider a threshold for "failed" if only score is returned
                            # For now, only `not is_valid` or `not passed` triggers fail_fast directly
                        else:
                            log.warning(
                                "Scanner %s returned unexpected 2-tuple content type",
                                scanner_name,
                                extra={
                                    "scanner": scanner_name,
                                    "request_id2": request_id,
                                },
                            )
                            scanner_results[scanner_name] = {
                                "error": f"Unexpected 2-tuple content type: {type(scanner_result_val).__name__}"
                            }
                    else:
                        log.warning(
                            "Scanner %s returned unexpected tuple format",
                            scanner_name,
                            extra={"scanner": scanner_name, "request_id2": request_id},
                        )
                        scanner_results[scanner_name] = {"error": "Unexpected tuple format"}
                else:
                    log.warning(
                        "Scanner %s returned non-tuple result",
                        scanner_name,
                        extra={"scanner": scanner_name, "request_id2": request_id},
                    )
                    scanner_results[scanner_name] = {
                        "error": f"Unexpected return type: {type(scan_result).__name__}"
                    }

                if (
                    sanitized_text != original_input_text and not modified
                ):  # Check if this scanner modified text
                    modified = True  # Text was modified by this scanner

                if self.fail_fast and current_scanner_failed:
                    log.info(
                        "Fail-fast triggered by scanner: %s",
                        scanner_name,
                        extra={
                            "scanner": scanner_name,
                            "request_id2": request_id,
                            "user_id": user_id,
                            "input_length": len(input_text),
                        },
                    )
                    # For fail-fast, we might want to assign a definitive high risk score.
                    # The _calculate_risk_score will still run on potentially partial results,
                    # or we can set final_risk_score directly here.
                    # Let's ensure the failing scanner's score contributes significantly or sets overall high risk.
                    # For simplicity, _calculate_risk_score will handle the current scanner_results.
                    # If a scanner explicitly provides a score, that's used. If it's a boolean fail, it's 1.0.
                    # The weights in _calculate_risk_score will determine final impact.
                    # If we want fail_fast to always be 1.0 risk:
                    final_risk_score = 1.0  # Override calculated score for fail-fast
                    break  # Exit the loop

            except Exception as e:
                log.error(
                    "Scanner %s failed: %s",
                    scanner_name,
                    type(e).__name__,
                    extra={
                        "scanner": scanner_name,
                        "request_id2": request_id,
                        "user_id": user_id,
                    },
                    exc_info=True,
                )
                scanner_results[scanner_name] = {
                    "error": "Scanner failed",
                    "passed": False,
                    "score": 1.0,
                }
                if self.fail_fast:
                    log.info(
                        "Fail-fast triggered by EXCEPTION in scanner: %s",
                        scanner_name,
                        extra={
                            "scanner": scanner_name,
                            "request_id2": request_id,
                            "user_id": user_id,
                            "input_length": len(input_text),
                        },
                    )
                    modified = True  # Assume modification or unsafe state
                    final_risk_score = 1.0  # Override for exception in fail_fast
                    break

        if not (
            self.fail_fast and final_risk_score == 1.0
        ):  # If not already set by fail_fast override
            final_risk_score = self._calculate_risk_score(scanner_results)

        # Log validation event (no user content per ADR-048)
        log.info(
            "Validation event",
            extra={
                "request_id2": request_id,
                "user_id": user_id,
                "input_length": len(original_input_text),
                "risk_score": final_risk_score,
                "modified": modified,
            },
        )

        result_tuple = (sanitized_text, final_risk_score, modified, scanner_results)
        if self.cache is not None:
            with self._cache_rlock:
                self.cache[original_input_text] = result_tuple
            log.debug(
                "Result cached for validation request",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "input_length": len(original_input_text),
                },
            )

        return result_tuple

    def _calculate_risk_score(self, scanner_results: dict[str, Any]) -> float:
        """
        Calculate an overall risk score from individual scanner results.

        Weight factors for each scanner are applied to generate the overall risk score.
        Certain scanners return binary results (pass/fail) while others return a numeric score.

        Args:
            scanner_results (Dict): The dictionary containing results from each scanner.

        Returns:
            float: Normalized risk score between 0 and 1.
        """
        weights = {
            "prompt_injection": 0.3,
            "toxicity": 0.2,
            "secrets": 0.2,
            "code": 0.1,
            "ban_substrings": 0.1,
            "ban_topics": 0.1,
            "language": 0.0,
            "gibberish": 0.0,
            "ban_competitors": 0.0,
            "regex": 0.0,
        }

        score = 0.0
        total_weight = 0.0

        for scanner_name, result in scanner_results.items():
            weight = weights.get(scanner_name, 0.0)
            if "error" in result or weight == 0.0:
                continue

            # This scanner contributes to the total_weight if it's active and has a weight
            total_weight += weight

            current_scanner_score = 0.0  # Default score if passed and no specific score given
            if "score" in result:
                current_scanner_score = result["score"]
            elif "passed" in result and not result["passed"]:  # If it failed
                current_scanner_score = 1.0
            # If "passed" is True and "score" is not present, current_scanner_score remains 0.0

            score += current_scanner_score * weight

        if total_weight > 0:
            score = score / total_weight

        # Clamp score between 0 and 1.
        return min(max(score, 0.0), 1.0)
