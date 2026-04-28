"""
Fallback Strategy for AI Operations Platform LLM Router.

This module provides the FallbackStrategy class which handles:
- Determining when to try a different model based on failure type
- Model-specific fallback mechanisms for different intents
- Tracking attempted models to prevent fallback loops
"""

import os

from shared.logging_utils.fastapi import configure_logging

from ..schemas.intent import RequestType
from ..schemas.llm import ModelType
from .llm_client import BadRequestError

logger = configure_logging(service_name="fallback_strategy", log_level="INFO", log_format="json")


class FallbackStrategy:
    """
    Manages fallback logic when model calls fail.
    Determines appropriate fallback models and prevents infinite retry loops.
    """

    def __init__(self, max_retries: int = 3):
        """
        Initialize the FallbackStrategy with fallback mappings from environment variables.

        Args:
            max_retries: Maximum number of retry attempts
        """
        self.max_retries = max_retries
        self._load_fallback_mappings()
        logger.info("FallbackStrategy initialized with model-specific fallback mappings")

    def _load_fallback_mappings(self) -> None:
        """Load model-specific fallback mappings from environment variables."""
        # Create general fallback mappings - each model type falls back to a different model type
        self.FALLBACK_MAPPING = {
            ModelType.QUERY: ModelType.SUMMARIZATION,  # Query falls back to Summarization (more general capabilities)
            ModelType.RULE_GENERATION: ModelType.ENRICHMENT,  # Rule generation falls back to Enrichment (similar structured output)
            ModelType.SUMMARIZATION: ModelType.QUERY,  # Summarization falls back to Query
            ModelType.ENRICHMENT: ModelType.RULE_GENERATION,  # Enrichment falls back to Rule Generation
        }

        # Create model-specific fallback mappings from environment variables
        self.MODEL_FALLBACK_MAPPING = {
            ModelType.QUERY: self._get_model_type_from_env(
                "INTENT_FALLBACK_QUERY", ModelType.SUMMARIZATION
            ),
            ModelType.RULE_GENERATION: self._get_model_type_from_env(
                "INTENT_FALLBACK_RULE_GENERATION", ModelType.ENRICHMENT
            ),
            ModelType.SUMMARIZATION: self._get_model_type_from_env(
                "INTENT_FALLBACK_SUMMARIZATION", ModelType.QUERY
            ),
            ModelType.ENRICHMENT: self._get_model_type_from_env(
                "INTENT_FALLBACK_ENRICHMENT", ModelType.RULE_GENERATION
            ),
        }

        # Log the loaded fallback mappings
        for model_type, fallback in self.MODEL_FALLBACK_MAPPING.items():
            logger.info(f"Model type {model_type} fallback: {fallback}")

    def _get_model_type_from_env(self, env_var: str, default: ModelType) -> ModelType:
        """
        Get a ModelType from an environment variable.

        Args:
            env_var: The environment variable name to check
            default: The default ModelType to use if not found

        Returns:
            The corresponding ModelType
        """
        if env_var not in os.environ:
            return default

        model_name = os.environ[env_var].upper()

        try:
            # Try to directly convert the environment variable to a ModelType
            return ModelType(model_name)
        except ValueError:
            # If direct conversion fails, log a warning and return the default
            logger.warning(f"Unknown model type in {env_var}: {model_name}, using {default}")
            return default

    def get_fallback_model(
        self,
        original_model: ModelType,
        error: Exception,
        intent_type: RequestType | None = None,
        fallback_chain: list[ModelType] | None = None,
    ) -> ModelType | None:
        """
        Determine fallback model based on model type and error.

        Args:
            original_model: The model that failed
            error: The exception that occurred
            intent_type: The intent type (used for logging purposes)
            fallback_chain: List of previously attempted fallback models

        Returns:
            The fallback model to use, or None if no fallback is appropriate
        """
        # Initialize fallback chain if not provided
        if fallback_chain is None:
            fallback_chain = []

        # Skip fallback for certain error types
        if isinstance(error, BadRequestError):
            # Input issues won't be resolved by switching models
            logger.warning(f"Not attempting fallback for BadRequestError: {error!s}")
            return None

        # Use model-based fallback
        fallback_model = self.MODEL_FALLBACK_MAPPING.get(original_model)
        if fallback_model is None:
            logger.warning(f"No fallback mapping for model {original_model}")
            return None

        if fallback_model == original_model:
            logger.warning(f"Avoiding fallback loop for model {original_model}")
            return None

        # Check if fallback model has already been attempted
        if fallback_model in fallback_chain:
            logger.warning(
                f"Fallback model {fallback_model} already tried in chain {fallback_chain}"
            )
            return None

        # Include intent_type in log if available
        if intent_type:
            logger.info(
                f"Using model-based fallback from {original_model} to {fallback_model} for intent {intent_type}"
            )
        else:
            logger.info(f"Using model-based fallback from {original_model} to {fallback_model}")

        return fallback_model

    def should_attempt_fallback(self, attempt: int, error: Exception) -> bool:
        """
        Determine if we should attempt a fallback based on retry count and error type.

        Args:
            attempt: The current attempt number
            error: The exception that occurred

        Returns:
            Boolean indicating whether to attempt fallback
        """
        # Check retry count
        if attempt > self.max_retries:
            logger.warning(
                f"Maximum retry attempts reached ({self.max_retries}), not attempting fallback"
            )
            return False

        # Skip fallback for certain error types
        if isinstance(error, BadRequestError):
            logger.warning(f"Not attempting fallback for BadRequestError: {error!s}")
            return False

        return True
