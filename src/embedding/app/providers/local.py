"""
Local embedding provider implementation using SentenceTransformers.
"""

import time
from pathlib import Path

from shared.logging_utils.fastapi import configure_logging

from ..config.models import ModelConfig
from ..schemas.embedding import EmbeddingRequest, EmbeddingResponse
from ..types import ProviderType
from .protocol import EmbeddingError, EmbeddingProvider, ModelNotFoundError

# Configure centralized logger for this provider
logger = configure_logging(service_name="local_provider")

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "SentenceTransformers library not found. LocalProvider will not be available. "
        "Install with: pip install sentence-transformers"
    )


class LocalProvider(EmbeddingProvider):
    """
    Implementation of EmbeddingProvider for local SentenceTransformer models.
    """

    def __init__(self, name: str, models: list[ModelConfig], priority: int = 20):
        """
        Initialize the Local provider.

        Args:
            name: Provider name.
            models: List of models available through this provider.
            priority: Provider priority (lower is higher priority).
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "SentenceTransformers library is not installed. "
                "LocalProvider cannot be initialized."
            )

        self.name = name
        self.provider_type = ProviderType.LOCAL_MODEL
        self.priority = priority

        self.loaded_models: dict[str, SentenceTransformer] = {}
        self.model_configs: dict[str, ModelConfig] = {}
        self.default_model_name: str | None = None

        if not models:
            logger.error(f"No models configured for LocalProvider '{name}'.")
            raise ValueError(f"At least one model must be configured for LocalProvider '{name}'.")

        for model_config in models:
            self.model_configs[model_config.name] = model_config
            if model_config.path:
                try:
                    model_path = Path(model_config.path)
                    if not model_path.exists():
                        logger.error(
                            f"Model path {model_path} does not exist for model "
                            f"'{model_config.name}' in LocalProvider '{name}'. "
                            "Ensure models are downloaded and mounted correctly."
                        )
                        # Continue to allow other models to load, health check will fail
                        continue

                    logger.info(f"Loading local model '{model_config.name}'.")
                    self.loaded_models[model_config.name] = SentenceTransformer(str(model_path))
                    logger.info(f"Successfully loaded model '{model_config.name}'.")
                    if model_config.default and not self.default_model_name:
                        self.default_model_name = model_config.name
                except Exception as e:
                    logger.error(
                        f"Failed to load model '{model_config.name}' from path "
                        f"'{model_config.path}' for LocalProvider '{name}': {e}"
                    )
            else:
                logger.warning(
                    f"No path configured for model '{model_config.name}' in "
                    f"LocalProvider '{name}'. This model will not be available."
                )

        if not self.default_model_name and self.loaded_models:
            self.default_model_name = next(iter(self.loaded_models.keys()))
            logger.info(
                f"No default model explicitly set, using first loaded model: {self.default_model_name}"
            )

        if not self.loaded_models:
            logger.error(f"No models successfully loaded for LocalProvider '{name}'.")
            # This provider will be unhealthy.

        logger.info(
            f"Initialized LocalProvider '{name}' with {len(self.loaded_models)} loaded models."
        )

    async def health_check(self) -> dict[str, bool]:
        """
        Check the health of this provider.
        Checks if at least one model is loaded.
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return {
                "available": False,
                "sentence_transformers_installed": False,
                "models_loaded": False,
            }

        models_loaded_check = bool(self.loaded_models)
        return {
            "available": models_loaded_check,
            "sentence_transformers_installed": True,
            "models_loaded": models_loaded_check,
            "default_model_set": bool(
                self.default_model_name and self.default_model_name in self.loaded_models
            ),
        }

    async def get_model_info(self) -> dict[str, dict]:
        """
        Get information about available models.
        """
        info = {}
        for name, model_config in self.model_configs.items():
            is_loaded = name in self.loaded_models
            info[name] = {
                "dimensions": model_config.dimensions,
                "path": model_config.path,
                "default": model_config.default,
                "batch_size": model_config.batch_size,
                "loaded": is_loaded,
                "metadata": model_config.metadata or {},
            }
        return info

    async def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for the provided texts using a local SentenceTransformer model.
        """
        start_time = time.time()

        model_name_to_use = request.model or self.default_model_name
        if not model_name_to_use:
            raise ModelNotFoundError(
                f"No default model available for provider {self.name} and no model specified in request."
            )

        if model_name_to_use not in self.loaded_models:
            raise ModelNotFoundError(
                f"Model '{model_name_to_use}' not loaded or available in provider '{self.name}'. "
                f"Available loaded models: {list(self.loaded_models.keys())}"
            )

        model_config = self.model_configs[model_name_to_use]
        transformer_model = self.loaded_models[model_name_to_use]

        try:
            # SentenceTransformer handles batching internally if given a list of sentences.
            # However, we respect the configured batch_size for consistency or potential future needs.
            batch_size = model_config.batch_size or 32  # Default batch size if not set
            all_vectors_list = []  # To store lists of floats

            for i in range(0, len(request.texts), batch_size):
                batch_texts = request.texts[i : i + batch_size]
                # The encode method returns a list of ndarray or a single ndarray.
                # Convert to list of lists of floats.
                embeddings_np = transformer_model.encode(batch_texts, batch_size=len(batch_texts))
                all_vectors_list.extend([emb.tolist() for emb in embeddings_np])

            # Note: SentenceTransformer doesn't directly provide token counts.
            # We'll set total_tokens to 0 or an estimated value if needed.
            # For simplicity, we'll use a placeholder for now.
            num_texts = len(request.texts)
            total_tokens = num_texts * 10  # A very rough estimate, not accurate.

        except Exception as e:
            logger.error(f"Error generating embeddings with model '{model_name_to_use}': {e}")
            raise EmbeddingError(
                f"Failed to generate embeddings with model '{model_name_to_use}': {e}"
            )

        processing_time = time.time() - start_time

        dimensions = (
            model_config.dimensions
            if model_config.dimensions is not None
            else (len(all_vectors_list[0]) if all_vectors_list else 0)
        )

        return EmbeddingResponse(
            vectors=all_vectors_list,
            model=model_name_to_use,
            dimensions=dimensions,
            processing_time=processing_time,
            usage={
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens,
            },  # Placeholder usage
        )
