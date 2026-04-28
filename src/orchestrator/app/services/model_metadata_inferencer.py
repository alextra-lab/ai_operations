"""
Model Metadata Inferencer for AI Operations Platform.

Infers model parameters from model IDs and known patterns when
the inference server doesn't provide complete metadata.

Metadata Priority:
1. YAML configuration file (config/models/model_metadata.yaml)
2. Pattern-based inference from model ID
3. Provider/model-type defaults
"""

from pathlib import Path
from typing import Any, ClassVar, cast

import yaml

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="model_metadata_inferencer")


class ModelMetadataInferencer:
    """
    Infer model parameters from model ID and known patterns.

    Since OpenAI-compatible /v1/models endpoints often only return
    basic info (id, owned_by), this class infers likely parameters.

    Loads configuration from config/models/model_metadata.yaml for
    comprehensive metadata management.
    """

    def __init__(self) -> None:
        """Initialize inferencer and load YAML configuration."""
        self.yaml_config = self._load_yaml_config()
        logger.info(
            "Model metadata inferencer initialized",
            extra={
                "yaml_models_count": len(self.yaml_config.get("models", {})),
                "provider_defaults": list(self.yaml_config.get("provider_defaults", {}).keys()),
            },
        )

    def _load_yaml_config(self) -> dict:
        """
        Load model metadata from YAML configuration file.

        Returns:
            Dictionary with models, provider_defaults, model_type_defaults
        """
        # Try multiple possible paths
        possible_paths = [
            Path("config/models/model_metadata.yaml"),
            Path("/app/config/models/model_metadata.yaml"),
            Path(__file__).parent.parent.parent.parent.parent
            / "config"
            / "models"
            / "model_metadata.yaml",
        ]

        for config_path in possible_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                        logger.info(
                            f"Loaded model metadata config from {config_path}",
                            extra={
                                "config_path": str(config_path),
                                "models_count": len(config.get("models", {})),
                            },
                        )
                        return cast("dict[Any, Any]", config)
                except Exception as e:
                    logger.warning(
                        f"Failed to load YAML config from {config_path}: {e}",
                        extra={"config_path": str(config_path), "error": str(e)},
                    )

        logger.warning("No YAML config found, using fallback patterns only")
        return {"models": {}, "provider_defaults": {}, "model_type_defaults": {}}

    # Known model configurations (fallback if YAML not available)
    KNOWN_MODELS: ClassVar[dict[str, Any]] = {
        # OpenAI models
        "gpt-4o-mini": {
            "context_window": 128000,
            "max_output_tokens": 16384,
            "provider": "openai",
            "model_type": "llm",
        },
        "gpt-4o": {
            "context_window": 128000,
            "max_output_tokens": 16384,
            "provider": "openai",
            "model_type": "llm",
            "supports_vision": True,
            "supports_tools": True,
        },
        "gpt-4-turbo": {
            "context_window": 128000,
            "max_output_tokens": 4096,
            "provider": "openai",
            "model_type": "llm",
            "supports_tools": True,
        },
        "gpt-4": {
            "context_window": 8192,
            "max_output_tokens": 4096,
            "provider": "openai",
            "model_type": "llm",
        },
        "gpt-3.5-turbo": {
            "context_window": 16384,
            "max_output_tokens": 4096,
            "provider": "openai",
            "model_type": "llm",
        },
        # Claude models
        "claude-3-opus": {
            "context_window": 200000,
            "max_output_tokens": 4096,
            "provider": "anthropic",
            "model_type": "llm",
            "supports_vision": True,
        },
        "claude-3-sonnet": {
            "context_window": 200000,
            "max_output_tokens": 4096,
            "provider": "anthropic",
            "model_type": "llm",
            "supports_vision": True,
        },
        "claude-3-haiku": {
            "context_window": 200000,
            "max_output_tokens": 4096,
            "provider": "anthropic",
            "model_type": "llm",
        },
        # Embedding models
        "text-embedding-3-small": {
            "context_window": 8191,
            "provider": "openai",
            "model_type": "embedding",
        },
        "text-embedding-3-large": {
            "context_window": 8191,
            "provider": "openai",
            "model_type": "embedding",
        },
        "all-minilm-l6-v2": {
            "context_window": 256,
            "provider": "local",
            "model_type": "embedding",
        },
    }

    # Pattern-based inference rules
    CONTEXT_WINDOW_PATTERNS: ClassVar[dict[str, int]] = {
        "gpt-4": 128000,
        "gpt-3.5": 16384,
        "claude-3": 200000,
        "llama-3.2": 128000,
        "llama-3.1": 128000,
        "llama-3": 8192,
        "mistral": 32000,
    }

    def infer_metadata(self, model_id: str, owned_by: str | None = None) -> dict[str, Any]:
        """
        Infer model metadata from model ID.

        Priority:
        1. YAML config (config/models/model_metadata.yaml)
        2. Hardcoded KNOWN_MODELS
        3. Pattern-based inference

        Args:
            model_id: Model identifier from inference server
            owned_by: Owner field from /v1/models response

        Returns:
            Dictionary of inferred metadata
        """
        # 1. Check YAML config first
        if model_id in self.yaml_config.get("models", {}):
            yaml_metadata = self.yaml_config["models"][model_id].copy()
            yaml_metadata["model_id"] = model_id
            yaml_metadata["name"] = yaml_metadata.get("name", self._generate_display_name(model_id))

            # Apply provider_type defaults if available
            provider_type = yaml_metadata.get("provider_type")
            if provider_type and provider_type in self.yaml_config.get("provider_defaults", {}):
                provider_defaults = self.yaml_config["provider_defaults"][provider_type]
                # Merge defaults (YAML values take precedence)
                for key, value in provider_defaults.items():
                    if key not in yaml_metadata or yaml_metadata[key] is None:
                        yaml_metadata[key] = value

            logger.info(
                f"Found model {model_id} in YAML config",
                extra={"model_id": model_id, "source": "yaml_config"},
            )
            return cast("dict[str, Any]", yaml_metadata)

        # 2. Check hardcoded KNOWN_MODELS (fallback)
        if model_id in self.KNOWN_MODELS:
            logger.info(
                f"Found model {model_id} in known models",
                extra={"model_id": model_id, "source": "known_models"},
            )
            return cast("dict[str, Any]", self.KNOWN_MODELS[model_id].copy())

        # 3. Pattern-based inference
        metadata = {
            "model_id": model_id,
            "name": self._generate_display_name(model_id),
            "provider_type": self._infer_provider_type(model_id, owned_by),
            "model_type": self._infer_model_type(model_id),
            "context_window": self._infer_context_window(model_id),
            "max_output_tokens": self._infer_max_output_tokens(model_id),
            "embedding_dimensions": self._infer_embedding_dimensions(model_id),
            "supports_tools": self._infer_supports_tools(model_id),
            "supports_vision": self._infer_supports_vision(model_id),
        }

        # Apply provider defaults if available
        provider_type = metadata.get("provider_type")
        if provider_type and provider_type in self.yaml_config.get("provider_defaults", {}):
            provider_defaults = self.yaml_config["provider_defaults"][provider_type]
            # Merge provider defaults (pattern inference takes precedence)
            for key, value in provider_defaults.items():
                if key not in metadata or metadata[key] is None:
                    metadata[key] = value

        logger.info(
            f"Inferred metadata for model {model_id}",
            extra={"model_id": model_id, "source": "pattern_inference"},
        )

        return metadata

    def _generate_display_name(self, model_id: str) -> str:
        """Generate human-readable name from model ID."""
        # Simple: Title case and replace hyphens/underscores
        name = model_id.replace("-", " ").replace("_", " ")
        return name.title()

    def _infer_provider_type(self, model_id: str, owned_by: str | None) -> str:
        """
        Infer model provider type (API protocol).

        Returns provider_type: "openai", "anthropic", "local", or "other"
        This indicates the API protocol, not the gateway provider name.
        """
        model_lower = model_id.lower()

        # Use owned_by if provided
        if owned_by:
            if owned_by in ["openai", "system"]:
                return "openai"
            if owned_by in ["anthropic"]:
                return "anthropic"

        # Pattern matching on model ID
        if "gpt" in model_lower or "davinci" in model_lower:
            return "openai"
        if "claude" in model_lower:
            return "anthropic"
        if any(x in model_lower for x in ["llama", "mistral", "qwen", "phi"]):
            return "openai"  # These are served via OpenAI-compatible API (LMStudio)

        return "other"

    def _infer_model_type(self, model_id: str) -> str:
        """Infer model type (llm, embedding, etc.)."""
        model_lower = model_id.lower()

        if "embedding" in model_lower or "embed" in model_lower:
            return "embedding"
        if "vision" in model_lower:
            return "vision"
        if "audio" in model_lower or "whisper" in model_lower:
            return "audio"

        return "llm"

    def _infer_context_window(self, model_id: str) -> int | None:
        """Infer context window from model ID patterns."""
        model_lower = model_id.lower()

        # Check patterns
        for pattern, context_window in self.CONTEXT_WINDOW_PATTERNS.items():
            if pattern in model_lower:
                return context_window

        # Default guesses by model type
        if "embedding" in model_lower:
            return 512
        if "llama" in model_lower or "mistral" in model_lower:
            return 32000

        return None  # Unknown, admin should set manually

    def _infer_max_output_tokens(self, model_id: str) -> int | None:
        """Infer max output tokens."""
        # Most modern models default to ~4K output
        context_window = self._infer_context_window(model_id)

        if context_window:
            # Conservative: 1/4 of context window for output
            return min(context_window // 4, 16384)

        return None

    def _infer_supports_tools(self, model_id: str) -> bool:
        """Infer if model supports tool/function calling."""
        model_lower = model_id.lower()

        # Known tool-capable models
        tool_patterns = ["gpt-4", "gpt-3.5-turbo", "claude-3"]

        return any(pattern in model_lower for pattern in tool_patterns)

    def _infer_supports_vision(self, model_id: str) -> bool:
        """Infer if model supports vision."""
        model_lower = model_id.lower()

        # Known vision-capable models
        vision_patterns = ["gpt-4o", "claude-3-opus", "claude-3-sonnet", "vision"]

        return any(pattern in model_lower for pattern in vision_patterns)

    def _infer_embedding_dimensions(self, model_id: str) -> int | None:
        """Infer embedding dimensions for embedding models."""
        model_lower = model_id.lower()

        # Known embedding dimensions
        embedding_dims = {
            "minilm": 384,
            "all-minilm": 384,
            "bge-small": 384,
            "bge-base": 768,
            "bge-large": 1024,
            "bge-m3": 1024,
            "nomic-embed": 768,
            "e5-small": 384,
            "e5-base": 768,
            "e5-large": 1024,
            "e5-mistral": 4096,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "ada-002": 1536,
        }

        for pattern, dims in embedding_dims.items():
            if pattern in model_lower:
                return dims

        # Default for unknown embedding models
        if self._infer_model_type(model_id) == "embedding":
            return 768  # Common default

        return None
