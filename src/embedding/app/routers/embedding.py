"""
Router for embedding API endpoints.
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from shared.logging_utils.fastapi import configure_logging

from ..providers import provider_factory
from ..providers.protocol import ModelNotFoundError, ProviderNotAvailableError
from ..schemas.embedding import (
    EmbeddingRequest,
    EmbeddingResponse,
    OpenAIEmbeddingData,
    OpenAIEmbeddingRequest,
    OpenAIEmbeddingResponse,
    OpenAIUsage,
)
from ..utils.auth import get_current_user

# Configure centralized logger for this router
logger = configure_logging(service_name="embedding_router")

router = APIRouter(
    prefix="/embed",
    tags=["embedding"],
)


@router.post("", response_model=EmbeddingResponse)
async def create_embeddings(
    request: EmbeddingRequest,
    current_user: Any = Depends(get_current_user),
) -> EmbeddingResponse:
    """
    Generate embeddings for the provided texts.

    Args:
        request: Embedding request with texts to embed

    Returns:
        EmbeddingResponse: Response containing embedding vectors
    """
    logger.info(f"Embedding request received for {len(request.texts)} texts")
    start_time = time.time()

    try:
        provider = await provider_factory.get_provider(None)  # Use default provider
        response = await provider.embed_texts(request)

        logger.info(
            f"Embedding generation completed in {time.time() - start_time:.2f}s for "
            f"{len(request.texts)} texts using provider {provider.name}"
        )
        return response
    except ModelNotFoundError as e:
        logger.error(f"Model not found: {e!s}")
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderNotAvailableError as e:
        logger.error(f"Provider not available: {e!s}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating embeddings: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {e!s}")


@router.post("/provider/{provider_name}", response_model=EmbeddingResponse)
async def create_embeddings_with_provider(
    provider_name: str,
    request: EmbeddingRequest,
    current_user: Any = Depends(get_current_user),
) -> EmbeddingResponse:
    """
    Generate embeddings using a specific provider.

    Args:
        provider_name: Name of the provider to use
        request: Embedding request with texts to embed

    Returns:
        EmbeddingResponse: Response containing embedding vectors
    """
    logger.info(f"Embedding request received for provider {provider_name}")
    start_time = time.time()

    try:
        provider = await provider_factory.get_provider(provider_name)
        response = await provider.embed_texts(request)

        logger.info(
            f"Embedding generation completed in {time.time() - start_time:.2f}s for "
            f"{len(request.texts)} texts using provider {provider_name}"
        )
        return response
    except ModelNotFoundError as e:
        logger.error(f"Model not found: {e!s}")
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderNotAvailableError as e:
        logger.error(f"Provider not available: {e!s}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating embeddings: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error generating embeddings: {e!s}")


@router.post("/openai", response_model=OpenAIEmbeddingResponse)
async def create_openai_embeddings(
    request: OpenAIEmbeddingRequest,
    current_user: Any = Depends(get_current_user),
) -> OpenAIEmbeddingResponse:
    """
    Generate embeddings in OpenAI-compatible format.

    This endpoint provides an OpenAI-compatible interface for the embedding service.

    Args:
        request: OpenAI-compatible embedding request

    Returns:
        OpenAIEmbeddingResponse: Response in OpenAI-compatible format
    """
    logger.info(
        f"OpenAI-compatible embedding request received: model={request.model}, input_type={type(request.input).__name__}"
    )
    start_time = time.time()

    # Convert OpenAI request to internal format
    input_texts = request.input if isinstance(request.input, list) else [request.input]

    # Determine which provider and model to use
    actual_model = None  # Default: use provider's default model
    provider = None

    if request.model:
        model_str = str(request.model)
        if model_str == "openai":
            # Provider identifier - use OpenAI provider with default model
            provider = await provider_factory.get_provider("openai")
            actual_model = None
        elif model_str == "local":
            # Provider identifier - use local provider with default model
            provider = await provider_factory.get_provider("local")
            actual_model = None
        else:
            # Specific model name - find which provider has this model
            provider = await provider_factory.find_provider_for_model(model_str)
            if provider:
                actual_model = model_str
            else:
                # Model not found in any provider - use default provider
                logger.warning(
                    f"Model {model_str} not found in any provider, using default provider"
                )
                provider = await provider_factory.get_provider(None)
                actual_model = None

    if not provider:
        # No model specified - use default provider
        provider = await provider_factory.get_provider(None)

    internal_request = EmbeddingRequest(
        texts=input_texts,
        model=actual_model,  # Pass None to use provider's default model
        user=request.user,
    )

    try:
        response = await provider.embed_texts(internal_request)

        # Convert internal response to OpenAI format
        data = [
            OpenAIEmbeddingData(
                embedding=vector,
                index=i,
            )
            for i, vector in enumerate(response.vectors)
        ]

        usage = OpenAIUsage(
            prompt_tokens=(response.usage.get("prompt_tokens", 0) if response.usage else 0),
            total_tokens=response.usage.get("total_tokens", 0) if response.usage else 0,
        )

        openai_response = OpenAIEmbeddingResponse(
            data=data,
            model=response.model,
            usage=usage,
        )

        logger.info(
            f"OpenAI-compatible embedding generation completed in {time.time() - start_time:.2f}s for "
            f"{len(input_texts)} texts"
        )

        return openai_response
    except ModelNotFoundError as e:
        logger.error(f"Model not found: {e!s}")
        raise HTTPException(
            status_code=404,
            detail={"error": {"message": str(e), "type": "model_not_found"}},
        )
    except ProviderNotAvailableError as e:
        logger.error(f"Provider not available: {e!s}")
        raise HTTPException(
            status_code=503,
            detail={"error": {"message": str(e), "type": "service_unavailable"}},
        )
    except Exception as e:
        logger.exception(f"Error generating embeddings: {e!s}")
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": str(e), "type": "server_error"}},
        )


@router.get("/models", response_model=dict[str, dict[str, dict]])
async def list_models(
    current_user: Any = Depends(get_current_user),
) -> dict[str, dict[str, dict]]:
    """
    List available embedding models across all providers.

    Returns:
        dict: Mapping of provider names to model information
    """
    try:
        return await provider_factory.get_available_models()
    except Exception as e:
        logger.exception(f"Error listing models: {e!s}")
        raise HTTPException(status_code=500, detail=f"Error listing models: {e!s}")
