"""
Parameter Manager for AI Operations Platform LLM Router.

This module provides the ParameterManager class which handles:
- Model-based temperature and token management
- Using ModelType metadata for default values
"""

from shared.logging_utils.fastapi import configure_logging

from ..schemas.intent import RequestType
from ..schemas.llm import ModelType

logger = configure_logging(service_name="parameter_manager", log_level="INFO", log_format="json")


class ParameterManager:
    """
    Manages model parameters like temperature and max tokens based on model type.
    Uses the ModelType metadata for code-level defaults.
    """

    def __init__(self) -> None:
        """
        Initialize the ParameterManager with model metadata defaults.
        """
        self._load_parameter_mappings()
        logger.info("ParameterManager initialized with model-specific parameter mappings")

    def _load_parameter_mappings(self) -> None:
        """Load model-specific parameter mappings from model metadata defaults."""
        # Temperature mappings
        self.MODEL_TEMP_MAPPING = {
            ModelType.QUERY: float(ModelType.QUERY.metadata["default_temperature"]),
            ModelType.RULE_GENERATION: float(
                ModelType.RULE_GENERATION.metadata["default_temperature"]
            ),
            ModelType.SUMMARIZATION: float(ModelType.SUMMARIZATION.metadata["default_temperature"]),
            ModelType.ENRICHMENT: float(ModelType.ENRICHMENT.metadata["default_temperature"]),
        }

        # Max tokens mappings
        self.MODEL_TOKENS_MAPPING = {
            ModelType.QUERY: int(ModelType.QUERY.metadata["max_tokens"]),
            ModelType.RULE_GENERATION: int(ModelType.RULE_GENERATION.metadata["max_tokens"]),
            ModelType.SUMMARIZATION: int(ModelType.SUMMARIZATION.metadata["max_tokens"]),
            ModelType.ENRICHMENT: int(ModelType.ENRICHMENT.metadata["max_tokens"]),
        }

        # Log the loaded parameter mappings
        for model_type, temp in self.MODEL_TEMP_MAPPING.items():
            tokens = self.MODEL_TOKENS_MAPPING.get(model_type, 0)
            logger.info(
                f"Model type {model_type} parameters: temperature={temp}, max_tokens={tokens}"
            )

    def get_model_temperature(self, model_type: ModelType) -> float:
        """
        Get the appropriate temperature setting for a model type.

        Args:
            model_type: The type of model

        Returns:
            The temperature value to use
        """
        temp = self.MODEL_TEMP_MAPPING.get(model_type)
        if temp is None:
            return float(model_type.metadata["default_temperature"])
        return float(temp)

    def get_model_max_tokens(self, model_type: ModelType) -> int:
        """
        Get the appropriate max tokens setting for a model type.

        Args:
            model_type: The type of model

        Returns:
            The max tokens value to use
        """
        tokens = self.MODEL_TOKENS_MAPPING.get(model_type)
        if tokens is None:
            return int(model_type.metadata["max_tokens"])
        return int(tokens)

    def get_model_parameters(self, model_type: ModelType) -> dict[str, float | int]:
        """
        Get all parameters for a specific model type.

        Args:
            model_type: The type of model

        Returns:
            Dictionary with temperature and max_tokens for the model
        """
        return {
            "temperature": self.get_model_temperature(model_type),
            "max_tokens": self.get_model_max_tokens(model_type),
        }

    # Legacy compatibility methods
    def get_intent_temperature(self, intent_type: RequestType, default: float = 0.7) -> float:
        """
        Get the appropriate temperature setting for an intent type.
        Maps intent to model type and returns the corresponding temperature.

        Args:
            intent_type: The type of request
            default: Default temperature if mapping fails

        Returns:
            The temperature value to use
        """
        try:
            model_type = ModelType(intent_type.value)
            return self.get_model_temperature(model_type)
        except (ValueError, KeyError):
            logger.warning(
                f"No model type mapping for intent {intent_type}, using default temperature: {default}"
            )
            return default

    def get_intent_max_tokens(self, intent_type: RequestType, default: int = 2048) -> int:
        """
        Get the appropriate max tokens setting for an intent type.
        Maps intent to model type and returns the corresponding max tokens.

        Args:
            intent_type: The type of request
            default: Default max tokens if mapping fails

        Returns:
            The max tokens value to use
        """
        try:
            model_type = ModelType(intent_type.value)
            return self.get_model_max_tokens(model_type)
        except (ValueError, KeyError):
            logger.warning(
                f"No model type mapping for intent {intent_type}, using default max_tokens: {default}"
            )
            return default

    def get_intent_parameters(self, intent_type: RequestType) -> dict:
        """
        Get all parameters for a specific intent type.
        Maps intent to model type and returns all parameters.

        Args:
            intent_type: The type of request

        Returns:
            Dictionary with temperature and max_tokens for the intent
        """
        try:
            model_type = ModelType(intent_type.value)
            return self.get_model_parameters(model_type)
        except (ValueError, KeyError):
            logger.warning(
                f"No model type mapping for intent {intent_type}, using default parameters"
            )
            return {"temperature": 0.7, "max_tokens": 2048}
