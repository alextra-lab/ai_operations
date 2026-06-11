"""
Model Registry Service for AI Operations Platform.

Manages model metadata, discovery, and recommendations.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import httpx
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import Model
from ..schemas.model import (
    ModelCapabilities,
    ModelDetailedResponse,
    ModelListResponse,
    ModelPerformance,
    ModelPricing,
    ModelRecommendation,
    ModelResponse,
    ModelSelectionRequest,
)
from .model_metadata_inferencer import ModelMetadataInferencer

logger = configure_logging(service_name="model_registry_service")


class ModelRegistryService:
    """Service for managing model registry and metadata."""

    def __init__(
        self,
        session: AsyncSession,
        inference_endpoint: str | None = None,
        api_key: str | None = None,
        gateway_url: str | None = None,
        gateway_auth_token: str | None = None,
    ):
        """
        Initialize model registry service.

        Args:
            session: Database session
            inference_endpoint: OpenAI-compatible inference endpoint (fallback)
            api_key: API key for inference server
            gateway_url: Inference Gateway URL for unified model discovery
            gateway_auth_token: Authorization header value (e.g. "Bearer <jwt>") to
                forward to the Gateway, which requires a JWT rather than the LLMaaS key
        """
        self.session = session
        self.inference_endpoint = inference_endpoint
        self.api_key = api_key
        self.gateway_url = gateway_url
        self.gateway_auth_token = gateway_auth_token
        self.cache_ttl_seconds = 3600  # 1 hour cache
        self.inferencer = ModelMetadataInferencer()

    async def list_models(
        self,
        provider: str | None = None,
        model_type: str | None = None,
        available_only: bool = True,
        include_deprecated: bool = False,
        include_hidden: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> ModelListResponse:
        """
        List available models with filtering and pagination.

        Args:
            provider: Filter by provider
            model_type: Filter by model type
            available_only: Only return available models
            include_deprecated: Include deprecated models
            include_hidden: Include hidden models
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Paginated list of models
        """
        # Build query
        stmt = select(Model)

        filters = []
        if provider:
            filters.append(Model.provider == provider)
        if model_type:
            filters.append(Model.model_type == model_type)
        if available_only:
            filters.append(Model.is_available == True)  # noqa: E712
        if not include_deprecated:
            filters.append(Model.deprecated == False)  # noqa: E712
        if not include_hidden:
            filters.append(Model.is_hidden == False)  # noqa: E712

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count total - build count query with same filters
        count_stmt = select(func.count(Model.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination - order_by must come before offset/limit
        offset = (page - 1) * size
        stmt = stmt.order_by(Model.name).offset(offset).limit(size)

        # Execute
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return ModelListResponse(
            models=[ModelResponse.model_validate(m) for m in models],
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size if total > 0 else 0,
        )

    async def get_model(self, model_id: str) -> ModelDetailedResponse | None:
        """
        Get detailed model information.

        Args:
            model_id: Model identifier

        Returns:
            Detailed model information or None
        """
        stmt = select(Model).where(Model.model_id == model_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        # Build detailed response
        capabilities = ModelCapabilities(
            supports_tools=model.supports_tools,
            supports_vision=model.supports_vision,
            supports_audio=model.supports_audio,
        )

        pricing = (
            ModelPricing(
                input_price_per_million=Decimal(str(model.input_price_per_million)),
                output_price_per_million=Decimal(str(model.output_price_per_million)),
                currency="USD",
            )
            if model.input_price_per_million
            else None
        )

        performance = ModelPerformance(
            typical_latency_ms=model.typical_latency_ms,
            tokens_per_second=model.tokens_per_second,
            context_window=model.context_window,
            max_input_tokens=model.max_input_tokens,
            max_output_tokens=model.max_output_tokens,
        )

        # Calculate estimated cost per 1K tokens
        estimated_cost = None
        if model.input_price_per_million and model.output_price_per_million:
            # Assume 70/30 split input/output for estimation
            estimated_cost = (
                Decimal(str(model.input_price_per_million)) * Decimal("0.7")
                + Decimal(str(model.output_price_per_million)) * Decimal("0.3")
            ) / Decimal(
                "1000"
            )  # Convert to per 1K

        return ModelDetailedResponse(
            **ModelResponse.model_validate(model).model_dump(),
            capabilities=capabilities,
            pricing=pricing,
            performance=performance,
            estimated_cost_per_1k_tokens=estimated_cost,
        )

    async def discover_models_from_inference_server(self) -> list[dict[str, Any]]:
        """
        Query inference server for available models.

        Prefers Gateway endpoint (aggregates all providers) over direct inference server.

        Uses OpenAI-compatible /models endpoint.

        Returns:
            List of model metadata from inference server
        """
        # Prefer Gateway if available (aggregates all providers)
        if self.gateway_url:
            try:
                return await self._discover_from_gateway()
            except Exception as e:
                logger.warning(
                    "Failed to discover models from Gateway, falling back to direct endpoint: %s",
                    str(e),
                    extra={"gateway_url": self.gateway_url, "error": str(e)},
                )
                # Fall through to direct endpoint

        # Fallback to direct inference server
        if not self.inference_endpoint:
            logger.warning("No inference endpoint configured for model discovery")
            return []

        try:
            async with httpx.AsyncClient() as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                # Handle endpoint URL - may already include /v1
                endpoint = self.inference_endpoint.rstrip("/")
                if endpoint.endswith("/v1"):
                    models_url = f"{endpoint}/models"
                else:
                    models_url = f"{endpoint}/v1/models"

                logger.info(
                    "Querying models from: %s",
                    models_url,
                    extra={"endpoint": models_url},
                )

                response = await client.get(models_url, headers=headers, timeout=10.0)
                response.raise_for_status()

                data = response.json()
                models = data.get("data", [])

                # Determine provider from endpoint URL
                provider_from_endpoint = await self._determine_provider_from_url(
                    self.inference_endpoint
                )
                if provider_from_endpoint:
                    for model in models:
                        if "provider" not in model or not model.get("provider"):
                            model["provider"] = provider_from_endpoint
                            logger.debug(
                                "Assigned provider from endpoint URL",
                                extra={
                                    "model_id": model.get("id"),
                                    "provider": provider_from_endpoint,
                                    "endpoint": self.inference_endpoint,
                                },
                            )

                logger.info(
                    "Discovered %d models from inference server",
                    len(models),
                    extra={"models_count": len(models), "endpoint": models_url},
                )
                return cast("list[dict[str, Any]]", models)

        except Exception as e:
            logger.error(
                "Failed to discover models from inference server: %s",
                str(e),
                extra={"endpoint": self.inference_endpoint, "error": str(e)},
            )
            return []

    async def _discover_from_gateway(self) -> list[dict[str, Any]]:
        """
        Discover models from Inference Gateway (aggregates all providers).

        Returns:
            List of model metadata dictionaries from all Gateway providers
        """
        try:
            async with httpx.AsyncClient() as client:
                # The Gateway authenticates with a JWT (admin tokens bypass scope
                # checks); self.api_key is the LLMaaS key, which the Gateway rejects with
                # 401. Forward the caller's JWT when provided, falling back to api_key.
                headers = {}
                if self.gateway_auth_token:
                    headers["Authorization"] = self.gateway_auth_token
                elif self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                # gateway_url may already include /v1 (INFERENCE_GATEWAY_URL default does),
                # so guard against producing /v1/v1/models — same handling as the direct
                # inference-server and model-detail paths below.
                gateway_endpoint = (self.gateway_url or "").rstrip("/")
                if gateway_endpoint.endswith("/v1"):
                    models_url = f"{gateway_endpoint}/models"
                else:
                    models_url = f"{gateway_endpoint}/v1/models"

                logger.info(
                    "Querying models from Gateway (all providers): %s",
                    models_url,
                    extra={"gateway_url": models_url},
                )

                response = await client.get(models_url, headers=headers, timeout=10.0)
                response.raise_for_status()

                data = response.json()
                models = data.get("data", [])

                # If Gateway doesn't provide provider info for some models, determine from context
                # Check if we have a default provider we can assign
                default_provider = await self._get_default_gateway_provider()
                if default_provider:
                    for model in models:
                        if "provider" not in model or not model.get("provider"):
                            model["provider"] = default_provider
                            logger.debug(
                                "Assigned default provider from Gateway context",
                                extra={"model_id": model.get("id"), "provider": default_provider},
                            )

                logger.info(
                    "Discovered %d models from Gateway (all providers)",
                    len(models),
                    extra={"models_count": len(models), "gateway_url": models_url},
                )
                return cast("list[dict[str, Any]]", models)

        except Exception as e:
            logger.error(
                "Failed to discover models from Gateway: %s",
                str(e),
                extra={"gateway_url": self.gateway_url, "error": str(e)},
            )
            raise

    async def get_extended_model_metadata(self, model_id: str) -> dict[str, Any] | None:
        """
        Query extended metadata for a specific model.

        Some inference servers support /v1/models/{model_id} for detailed info.
        This may include context_window, max_tokens, capabilities, etc.

        Args:
            model_id: Model identifier

        Returns:
            Extended metadata dict or None if not available
        """
        if not self.inference_endpoint:
            return None

        try:
            async with httpx.AsyncClient() as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                # Build model detail URL
                endpoint = self.inference_endpoint.rstrip("/")
                if endpoint.endswith("/v1"):
                    model_url = f"{endpoint}/models/{model_id}"
                else:
                    model_url = f"{endpoint}/v1/models/{model_id}"

                response = await client.get(model_url, headers=headers, timeout=5.0)

                # If endpoint doesn't exist (404), return None gracefully
                if response.status_code == 404:
                    logger.debug(
                        "Extended metadata endpoint not available for %s",
                        model_id,
                        extra={"model_id": model_id, "status_code": 404},
                    )
                    return None

                response.raise_for_status()
                data = response.json()

                logger.info(
                    "Retrieved extended metadata for %s",
                    model_id,
                    extra={"model_id": model_id, "has_metadata": bool(data)},
                )

                return cast("dict[str, Any] | None", data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Endpoint doesn't support this, not an error
                return None
            logger.warning(
                "Failed to get extended metadata for %s: %s",
                model_id,
                str(e),
                extra={"model_id": model_id, "status_code": e.response.status_code},
            )
            return None
        except Exception as e:
            logger.debug(
                "Extended metadata not available for %s: %s",
                model_id,
                str(e),
                extra={"model_id": model_id, "error": str(e)},
            )
            return None

    async def sync_with_inference_server(self) -> dict[str, Any]:
        """
        Synchronize model registry with inference server.

        Workflow:
        1. Query Gateway /v1/models endpoint (Gateway aggregates all providers)
        2. Gateway provides provider metadata for each model
        3. Create new models automatically
        4. Update existing models
        5. Mark missing models as unavailable

        Returns:
            Detailed sync report with created/updated/unavailable counts
        """
        # Discover models via Gateway (prefers Gateway, falls back to direct endpoint)
        discovered_models = await self.discover_models_from_inference_server()

        sync_report: dict[str, Any] = {
            "status": "success",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "summary": {
                "total_discovered": len(discovered_models),
                "newly_created": 0,
                "updated_existing": 0,
                "marked_unavailable": 0,
            },
            "created_models": [],
            "updated_models": [],
            "unavailable_models": [],
            "warnings": [],
        }

        if not discovered_models:
            sync_report["warnings"].append(
                "No models discovered from any provider - check Gateway provider configuration"
            )
            logger.warning("No models discovered from any provider")
            # Continue to mark existing models as unavailable even if discovery is empty
            discovered_ids = set()
        else:
            discovered_ids = {m.get("id") for m in discovered_models if m.get("id")}

        # Get existing models
        stmt = select(Model)
        result = await self.session.execute(stmt)
        existing_models = result.scalars().all()
        existing_model_map = {m.model_id: m for m in existing_models}

        # Process discovered models - create or update
        for model_data in discovered_models:
            model_id = model_data.get("id")
            if not model_id:
                continue

            owned_by = model_data.get("owned_by")
            provider_name = model_data.get("provider")  # From Gateway (if enhanced) or None
            provider_type = model_data.get("provider_type")  # From Gateway (if enhanced) or None

            # Check if model exists
            if model_id in existing_model_map:
                # Update existing model
                existing = existing_model_map[model_id]
                updated = await self._update_existing_model(existing, model_data)
                if updated:
                    sync_report["summary"]["updated_existing"] += 1
                    sync_report["updated_models"].append(model_id)
            else:
                # Create new model (provider/provider_type from Gateway or inferred)
                created = await self._create_new_model(
                    model_id, owned_by, provider_name, provider_type
                )
                if created:
                    sync_report["summary"]["newly_created"] += 1
                    sync_report["created_models"].append(
                        {
                            "model_id": model_id,
                            "name": created.name,
                            "provider_type": created.provider_type,
                            "provider": created.provider,
                        }
                    )

        # Mark models not found as unavailable
        # Skip local models (provider=NULL) - they're not served by inference servers
        for model_id, model in existing_model_map.items():
            if model_id not in discovered_ids and model.is_available:
                # Skip local models - they're not queried from inference servers
                if model.provider is None:
                    continue

                model.is_available = False
                model.health_status = "unavailable"
                last_checked = datetime.now(tz=UTC)
                model.last_checked_at = last_checked
                sync_report["summary"]["marked_unavailable"] += 1
                sync_report["unavailable_models"].append(
                    {
                        "model_id": model_id,
                        "last_seen": last_checked.isoformat(),
                    }
                )

        await self.session.commit()

        logger.info(
            "Sync completed",
            extra={
                "discovered_count": sync_report["summary"]["total_discovered"],
                "newly_created_count": sync_report["summary"]["newly_created"],
                "updated_count": sync_report["summary"]["updated_existing"],
                "unavailable_count": sync_report["summary"]["marked_unavailable"],
            },
        )

        return sync_report

    async def _create_new_model(
        self,
        model_id: str,
        owned_by: str | None,
        provider_name: str | None = None,
        provider_type_from_discovery: str | None = None,
    ) -> Model | None:
        """
        Create a new model from discovered metadata.

        Workflow:
        1. Try to get extended metadata from /v1/models/{model_id}
        2. Infer metadata from model ID patterns
        3. Merge extended + inferred (extended takes precedence)
        4. Use provider info from discovery (provider_name, provider_type)
        5. Create model with combined metadata

        Args:
            model_id: Model identifier
            owned_by: Owner from inference server
            provider_name: Provider name (e.g., "LMStudio") - from provider discovery
            provider_type_from_discovery: Provider type (e.g., "openai") - from provider discovery

        Returns:
            Created model or None if failed
        """
        try:
            # 1. Try to get extended metadata from inference server
            extended_metadata = await self.get_extended_model_metadata(model_id)

            # 2. Infer metadata from model ID
            inferred_metadata = self.inferencer.infer_metadata(model_id, owned_by)

            # 3. Merge metadata (extended takes precedence)
            metadata = self._merge_metadata(inferred_metadata, extended_metadata)

            # 4. Use provider info from discovery (guaranteed when using _discover_models_from_all_providers)
            # Fallback to auto-assign if not provided (backward compatibility)
            if provider_name:
                assigned_provider = provider_name
                logger.debug(
                    "Using provider from discovery",
                    extra={"model_id": model_id, "provider": assigned_provider},
                )
            else:
                default_provider = await self._get_default_gateway_provider()
                if default_provider:
                    assigned_provider = default_provider
                    logger.debug(
                        "Auto-assigned provider (fallback)",
                        extra={"model_id": model_id, "provider": assigned_provider},
                    )

            # 4.5. Determine provider_type
            # Priority: Discovery > Metadata inference > Gateway default
            if provider_type_from_discovery:
                # Use provider_type from Gateway discovery (preferred)
                metadata["provider_type"] = provider_type_from_discovery
                logger.debug(
                    "Using provider_type from discovery",
                    extra={
                        "model_id": model_id,
                        "provider_type": provider_type_from_discovery,
                    },
                )
            elif metadata.get("provider_type") and metadata.get("provider_type") != "other":
                # Use inferred provider_type from YAML/patterns (if valid)
                logger.debug(
                    "Using provider_type from metadata inference",
                    extra={"model_id": model_id, "provider_type": metadata["provider_type"]},
                )
            elif assigned_provider:
                # Default to "openai" for Gateway providers (all OpenAI-compatible currently)
                metadata["provider_type"] = "openai"
                logger.debug(
                    "Defaulted provider_type to 'openai' for Gateway provider",
                    extra={"model_id": model_id, "provider": assigned_provider},
                )
            else:
                # Last resort: keep inferred value (even if "other")
                logger.debug(
                    "Using inferred provider_type (no better option)",
                    extra={
                        "model_id": model_id,
                        "provider_type": metadata.get("provider_type", "other"),
                    },
                )

            # 5. Create model with combined metadata
            # SQLAlchemy ORM model - using **kwargs to work around type checker limitations
            model_kwargs = {
                "model_id": model_id,
                "name": metadata.get("name", model_id),
                "provider_type": metadata.get("provider_type", "openai"),
                "provider": assigned_provider,  # From Gateway or auto-assigned
                "model_type": metadata.get("model_type", "llm"),
                "context_window": metadata.get("context_window"),
                "max_input_tokens": metadata.get("max_input_tokens"),
                "max_output_tokens": metadata.get("max_output_tokens"),
                "embedding_dimensions": metadata.get("embedding_dimensions"),
                "supports_tools": metadata.get("supports_tools", False),
                "supports_vision": metadata.get("supports_vision", False),
                "supports_audio": metadata.get("supports_audio", False),
                "is_reasoning_model": metadata.get("is_reasoning_model", False),
                "description": metadata.get("description"),
                "specialization": metadata.get("specialization"),
                "recommended_use_cases": metadata.get("recommended_use_cases", []),
                "is_available": True,
                "health_status": "healthy",
                "last_checked_at": datetime.now(tz=UTC),
                # Pricing is NULL - uses environment defaults
                "input_price_per_million": None,
                "output_price_per_million": None,
                "metadata_json": {
                    "auto_discovered": True,
                    "discovery_source": "inference_server",
                    "discovered_at": datetime.now(tz=UTC).isoformat(),
                    "owned_by": owned_by,
                    "has_extended_metadata": extended_metadata is not None,
                    "has_yaml_config": model_id in self.inferencer.yaml_config.get("models", {}),
                },
            }
            model = Model(**model_kwargs)  # type: ignore

            self.session.add(model)
            await self.session.flush()  # Get ID without committing

            logger.info(
                "Created new model: %s",
                model_id,
                extra={
                    "model_id": model_id,
                    "provider_type": model.provider_type,
                    "provider": model.provider,
                },
            )

            return model

        except Exception as e:
            logger.error(
                "Failed to create model %s: %s",
                model_id,
                str(e),
                extra={"model_id": model_id, "error": str(e)},
                exc_info=True,
            )
            return None

    async def _determine_provider_from_url(self, endpoint_url: str) -> str | None:
        """
        Determine provider name from endpoint URL by matching against gateway_providers.

        Matches endpoint URL (or base URL) against gateway_providers.base_url.

        Args:
            endpoint_url: The inference endpoint URL (e.g., http://lmstudio:1234/v1)

        Returns:
            Provider name if URL matches a configured provider, else None
        """
        if not endpoint_url:
            return None

        # Normalize URL for matching (remove /v1, trailing slashes, etc.)
        normalized = endpoint_url.rstrip("/").lower()
        if normalized.endswith("/v1"):
            normalized = normalized[:-3]

        try:
            from sqlalchemy import text

            # Query all enabled providers (using text() since GatewayProvider model doesn't exist)
            stmt = text("SELECT name, base_url FROM gateway_providers WHERE is_enabled = true")
            result = await self.session.execute(stmt)
            providers = result.all()

            # Match endpoint against provider base URLs
            for provider_name, base_url in providers:
                if not base_url:
                    continue
                provider_normalized = base_url.rstrip("/").lower()
                if provider_normalized.endswith("/v1"):
                    provider_normalized = provider_normalized[:-3]

                # Check if endpoint matches provider URL
                if normalized in provider_normalized or provider_normalized in normalized:
                    logger.debug(
                        "Matched endpoint URL to provider",
                        extra={
                            "endpoint": endpoint_url,
                            "provider": provider_name,
                            "base_url": base_url,
                        },
                    )
                    return cast("str", provider_name)

        except Exception as e:
            logger.debug(
                f"Could not determine provider from URL: {e}",
                extra={"endpoint": endpoint_url, "error": str(e)},
            )

        return None

    async def _get_default_gateway_provider(self) -> str | None:
        """
        Get default gateway provider if only one is enabled.

        This allows auto-assignment of provider during model sync.
        If multiple providers are enabled, returns None (requires manual assignment).

        Returns:
            Provider name if only one enabled, else None
        """
        try:
            from sqlalchemy import text

            stmt = text("SELECT name FROM gateway_providers WHERE is_enabled = true")
            result = await self.session.execute(stmt)
            enabled_providers = [str(row[0]) for row in result.all()]

            if len(enabled_providers) == 1:
                provider_name = enabled_providers[0]
                logger.debug(
                    f"Auto-assigning provider: {provider_name} (only enabled provider)",
                    extra={"provider": provider_name},
                )
                return provider_name

            if len(enabled_providers) > 1:
                logger.debug(
                    f"Multiple providers enabled ({len(enabled_providers)}), "
                    "skipping auto-assignment",
                    extra={"providers": enabled_providers},
                )

            return None

        except Exception as e:
            logger.warning(
                f"Failed to get default gateway provider: {e}",
                extra={"error": str(e)},
            )
            return None

    def _merge_metadata(
        self, inferred: dict[str, Any], extended: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        Merge inferred and extended metadata.

        Extended metadata takes precedence when both provide a value.

        Args:
            inferred: Metadata from pattern-based inference
            extended: Metadata from /v1/models/{model_id} endpoint

        Returns:
            Merged metadata dictionary
        """
        # Start with inferred metadata
        merged = inferred.copy()

        if not extended:
            return merged

        # Extended metadata fields to check and merge
        extended_fields = {
            "context_window": lambda v: v if isinstance(v, int) and v > 0 else None,
            "max_tokens": "max_output_tokens",  # Map to our field name
            "max_output_tokens": lambda v: v if isinstance(v, int) and v > 0 else None,
            "max_input_tokens": lambda v: v if isinstance(v, int) and v > 0 else None,
            "embedding_dimensions": lambda v: (v if isinstance(v, int) and v > 0 else None),
            "supports_tools": lambda v: bool(v) if v is not None else None,
            "supports_vision": lambda v: bool(v) if v is not None else None,
            "supports_audio": lambda v: bool(v) if v is not None else None,
            "capabilities": self._parse_capabilities,
        }

        # Merge extended metadata
        for ext_field, target in extended_fields.items():
            if ext_field not in extended:
                continue

            value = extended[ext_field]

            # Handle field mapping
            if isinstance(target, str):
                # Map to different field name
                if value is not None:
                    merged[target] = value
            elif callable(target):
                # Transform/validate value
                transformed = target(value)
                if transformed is not None:
                    merged[ext_field] = transformed
            else:
                # Direct copy
                if value is not None:
                    merged[ext_field] = value

        return merged

    def _parse_capabilities(self, capabilities: dict | list) -> dict:
        """
        Parse capabilities from extended metadata.

        Some servers return capabilities as dict or list.

        Returns:
            Dictionary of capability flags
        """
        if isinstance(capabilities, dict):
            return capabilities
        if isinstance(capabilities, list):
            # Convert list to dict
            return dict.fromkeys(capabilities, True)
        return {}

    async def _update_existing_model(self, model: Model, model_data: dict) -> bool:
        """
        Update existing model from discovery.

        Tries to fetch extended metadata to update context_window
        and other capabilities if they were previously unknown.

        Args:
            model: Existing model record
            model_data: Data from inference server

        Returns:
            True if updated, False if no changes
        """
        updated = False

        # Update availability
        if not model.is_available:
            model.is_available = True
            model.health_status = "healthy"
            updated = True

        # Update last checked timestamp
        model.last_checked_at = datetime.now(tz=UTC)

        # Try to get extended metadata to fill in missing fields
        if not model.context_window or not model.max_output_tokens:
            extended = await self.get_extended_model_metadata(model.model_id)
            if extended:
                # Update missing fields from extended metadata
                if not model.context_window and "context_window" in extended:
                    context_win = extended["context_window"]
                    if isinstance(context_win, int) and context_win > 0:
                        model.context_window = context_win
                        updated = True

                if not model.max_output_tokens:
                    max_out = extended.get("max_tokens") or extended.get("max_output_tokens")
                    if isinstance(max_out, int) and max_out > 0:
                        model.max_output_tokens = max_out
                        updated = True

        # Update owned_by if changed
        owned_by = model_data.get("owned_by")
        if owned_by and model.metadata_json.get("owned_by") != owned_by:
            if not isinstance(model.metadata_json, dict):
                model.metadata_json = {}
            model.metadata_json["owned_by"] = owned_by
            updated = True

        # Update provider if provided by Gateway (ADR-052 enhancement)
        provider_from_gateway = model_data.get("provider")
        if provider_from_gateway and model.provider != provider_from_gateway:
            model.provider = provider_from_gateway
            updated = True
            logger.debug(
                f"Updated provider for {model.model_id}: {model.provider} → {provider_from_gateway}",
                extra={"model_id": model.model_id, "new_provider": provider_from_gateway},
            )

        if updated:
            logger.info(
                "Updated model: %s",
                model.model_id,
                extra={"model_id": model.model_id},
            )

        return updated

    async def recommend_model(self, request: ModelSelectionRequest) -> list[ModelRecommendation]:
        """
        Recommend models based on use case requirements.

        Args:
            request: Model selection request with requirements

        Returns:
            List of model recommendations sorted by confidence
        """
        # Get available models
        models_response = await self.list_models(
            model_type="llm", available_only=True, include_deprecated=False, size=100
        )

        recommendations = []

        for model in models_response.models:
            confidence, reasoning = self._calculate_model_match(model, request)

            if confidence > 0.3:  # Only recommend if confidence > 30%
                # Get detailed info for cost/latency
                detailed = await self.get_model(model.model_id)

                recommendations.append(
                    ModelRecommendation(
                        model_id=model.model_id,
                        name=model.name,
                        confidence=confidence,
                        reasoning=reasoning,
                        estimated_cost=(
                            detailed.estimated_cost_per_1k_tokens if detailed else None
                        ),
                        estimated_latency_ms=(detailed.typical_latency_ms if detailed else None),
                        capabilities_match=confidence,
                    )
                )

        # Sort by confidence descending
        recommendations.sort(key=lambda x: x.confidence, reverse=True)

        return recommendations[:5]  # Return top 5

    def _calculate_model_match(
        self, model: ModelResponse, request: ModelSelectionRequest
    ) -> tuple[float, str]:
        """
        Calculate how well a model matches requirements.

        Returns:
            Tuple of (confidence_score, reasoning)
        """
        score = 0.5  # Base score
        reasons = []

        # Check specialization match
        if (
            model.specialization
            and request.use_case_type
            and request.use_case_type.lower() in model.specialization.lower()
        ):
            score += 0.2
            reasons.append(f"Specialized for {request.use_case_type}")

        # Check recommended use cases
        if (
            model.recommended_use_cases
            and request.use_case_type
            and request.use_case_type.lower() in [uc.lower() for uc in model.recommended_use_cases]
        ):
            score += 0.2
            reasons.append("Listed in recommended use cases")

        # Check capability requirements
        if request.prefer_capabilities:
            matches = 0
            for cap in request.prefer_capabilities:
                if (
                    (cap == "tools" and model.supports_tools)
                    or (cap == "vision" and model.supports_vision)
                    or (cap == "reasoning" and model.is_reasoning_model)
                ):
                    matches += 1

            if matches > 0:
                score += 0.1 * matches
                reasons.append(f"{matches} capability requirements met")

        # Check constraints
        if request.constraints:
            max_cost = request.constraints.get("max_cost_per_1k")
            if max_cost and model.input_price_per_million:
                estimated_cost = float(model.input_price_per_million) / 1000
                if estimated_cost > max_cost:
                    score -= 0.3
                    reasons.append("Exceeds cost budget")

        # Cap score at 1.0
        score = min(score, 1.0)

        reasoning = "; ".join(reasons) if reasons else "General purpose model"
        return score, reasoning
