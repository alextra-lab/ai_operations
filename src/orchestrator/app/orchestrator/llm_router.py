"""
Intent-Based LLM Router implementation for AI Operations Platform.

This module provides the LLMRouter class which handles:
- Model selection (deterministic: use case pin or intent default)
- Parameter management
- Request processing and response formatting
- Handling both synchronous and streaming responses

The LLMRouter is a key component in the orchestrator workflow:
Intent Parser → Retrieval Engine → Prompt Assembler → LLM Router → Response Formatter

ADR-069: Deterministic model selection. No hardcoded models. No fallback chains.
"""

import os
import time
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from openai import APITimeoutError
from openai.types.chat import ChatCompletionMessageParam

from shared.logging_utils.fastapi import configure_logging

from ..schemas.intent import RequestType
from ..schemas.llm import LLMRequest, LLMResponse, LLMStreamResponse, ModelType
from ..schemas.use_case_config import UseCaseConfig
from .llm_client import LLMClient
from .model_selection import ModelSelector
from .parameter_manager import ParameterManager
from .streaming_response import StreamingResponseGenerator

logger = configure_logging(service_name="llm_router", log_level="INFO", log_format="json")


class LLMRouter:
    """
    Router for LLM requests that orchestrates model selection, parameter management,
    and fallback strategy components to process requests and handle responses.
    """

    def __init__(
        self,
        gateway_url: str | None = None,
        connect_timeout: int = 10,
        read_timeout: int = 300,
        write_timeout: int = 10,
        pool_timeout: int = 5,
        max_retries: int = 3,
        base_delay: int = 1,
        user_jwt_token: str | None = None,
        request_timeout_seconds: int | None = None,
        model_selector: ModelSelector | None = None,
    ):
        """
        Initialize the Intent-Based LLM Router.

        Args:
            gateway_url: Inference Gateway URL
            connect_timeout: Timeout for establishing connection (seconds)
            read_timeout: Timeout for reading response (seconds)
            write_timeout: Timeout for writing request (seconds)
            pool_timeout: Timeout for connection pool (seconds)
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries (seconds)
            user_jwt_token: User's JWT token for Gateway authentication
            request_timeout_seconds: Optional timeout override for requests
            model_selector: Optional ModelSelector with preloaded intent defaults.
                When None, creates empty ModelSelector (use case must pin model).
        """
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info("LLMRouter.__init__ START")

        if not user_jwt_token:
            raise ValueError("LLMRouter requires user_jwt_token for Gateway authentication")

        base_url = gateway_url or "http://inference-gateway:8002"
        logger.info("LLMRouter: Using Inference Gateway")

        self.client = LLMClient(
            api_key=user_jwt_token,
            base_url=base_url,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
            pool_timeout=pool_timeout,
            max_retries=max_retries,
            base_delay=base_delay,
        )

        self.model_selector = model_selector or ModelSelector()
        self.parameter_manager = ParameterManager()
        self.max_retries = max_retries

        if request_timeout_seconds is not None:
            try:
                self.client.client.read_timeout = int(request_timeout_seconds)  # type: ignore[attr-defined]
                logger.info(
                    "Updated read timeout to %ss from configuration",
                    self.client.client.read_timeout,  # type: ignore[attr-defined]
                )
            except (ValueError, TypeError):
                logger.warning("Invalid request_timeout_seconds value provided")

        logger.info("LLMRouter initialized with database-driven model selection (ADR-069)")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.info(
                "LLMRouter.__init__ END. LLMRouter.__init__ completed successfully during test."
            )

    def _apply_intent_parameters(
        self, request: LLMRequest, intent_type: RequestType | None
    ) -> None:
        """
        Apply intent-specific temperature and max_tokens to the request if needed.

        Temperature priority: intent_model_defaults DB override > ParameterManager.
        """
        if intent_type:
            if abs(request.temperature - 0.7) < 0.01:
                # Check DB intent default first (ADR-069 extension)
                db_temp = self.model_selector.get_intent_temperature(intent_type)
                if db_temp is not None:
                    request.temperature = db_temp
                    logger.info(
                        "Using intent default temperature %.2f for %s",
                        request.temperature,
                        intent_type,
                    )
                else:
                    request.temperature = self.parameter_manager.get_intent_temperature(intent_type)
                    logger.info(
                        "Using intent-specific temperature %.2f for %s",
                        request.temperature,
                        intent_type,
                    )
            if request.max_tokens == 1024:
                request.max_tokens = self.parameter_manager.get_intent_max_tokens(intent_type)
                logger.info(
                    f"Using intent-specific max_tokens {request.max_tokens} for {intent_type}"
                )

    def _apply_config_overrides(
        self, request: LLMRequest, use_case_config: UseCaseConfig | None
    ) -> None:
        """
        Apply use case config to the request.

        ADR-069: No hardcoded model mappings. If config.models.llm is set, use it.
        Otherwise model selection uses intent default from ModelSelector.
        """
        if not use_case_config:
            return

        # Model pin: use case author explicitly chose a model
        if use_case_config.models and use_case_config.models.llm:
            request.model_name_override = use_case_config.models.llm
            logger.info(
                "Using use case model pin: %s (from config.models.llm)",
                use_case_config.models.llm,
            )

        # Generation parameters
        if use_case_config.generation_params:
            if use_case_config.generation_params.temperature is not None:
                request.temperature = use_case_config.generation_params.temperature
            if use_case_config.generation_params.max_tokens is not None:
                request.max_tokens = use_case_config.generation_params.max_tokens

    async def process(
        self,
        request: LLMRequest,
        stream: bool = False,
        intent_type: RequestType | None = None,
        use_case_config: UseCaseConfig | None = None,
    ) -> LLMResponse | AsyncGenerator[LLMStreamResponse, None]:
        """
        Process an LLMRequest and return a response.

        Args:
            request: The LLM request to process
            stream: Whether to stream the response
            intent_type: Optional RequestType for intent-specific parameters

        Returns:
            For non-streaming: LLMResponse with complete response
            For streaming: AsyncGenerator yielding LLMStreamResponse objects
        """
        # Apply config overrides first (highest priority)
        self._apply_config_overrides(request, use_case_config)

        if stream:
            return self.process_streaming(request, intent_type)
        return await self.process_sync(request, intent_type)

    async def process_sync(
        self,
        request: LLMRequest,
        intent_type: RequestType | None = None,
    ) -> LLMResponse:
        """
        Process a non-streaming LLMRequest and return a complete response.
        """
        self._apply_intent_parameters(request, intent_type)

        start_time = time.time()
        effective_intent = intent_type if intent_type is not None else RequestType.QUERY
        # Use-case override wins; otherwise select from intent/admin defaults (requires DB)
        try:
            if request.model_name_override:
                openai_model = request.model_name_override
                logger.info(
                    "Using model from use case config: %s",
                    openai_model,
                )
            else:
                openai_model = self.model_selector.get_model_for_intent(effective_intent)
        except ValueError as ve:
            processing_time = time.time() - start_time
            logger.error(f"Model selection error: {ve!s}")
            error_metadata = {
                "success": False,
                "error": str(ve),
                "error_type": "ValueError",
                "processing_time": processing_time,
            }
            if intent_type:
                error_metadata["intent_type"] = str(intent_type)
            return LLMResponse(
                response=f"Model selection error: {ve!s}",
                model_used=ModelType(effective_intent.value),
                tokens_used=1,
                processing_time=processing_time,
                metadata=error_metadata,
                tool_calls=None,
            )

        try:
            # Use messages array if provided (for multi-turn conversations)
            # Otherwise build simple message from prompt
            messages: list[ChatCompletionMessageParam]
            if request.messages:
                messages = request.messages  # type: ignore
                logger.info(
                    "Using %d messages from request for multi-turn conversation",
                    len(messages),
                )
            else:
                messages = [{"role": "user", "content": request.prompt}]

            # ModelType for fallback/metadata (aligns with intent)
            model_type = ModelType(effective_intent.value)
            response_text, metadata, tool_calls = await self._get_response(
                openai_model=openai_model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                model_type=model_type,
                intent_type=intent_type,
                tools=request.tools,
                tool_choice=request.tool_choice,
                response_format=request.response_format,
            )
            processing_time = time.time() - start_time
            response_metadata = metadata.copy()
            if intent_type:
                response_metadata["intent_type"] = str(intent_type)

            # Ensure response is not None (LLMResponse requires min_length=1)
            # But for tool calls it can be None/Empty.
            # We updated schema to allow None for response if tool calls exist, but simpler to use ""
            final_response_text = response_text or ""

            return LLMResponse(
                response=final_response_text,
                model_used=metadata.get("original_model", model_type),
                tokens_used=metadata.get("total_tokens", 0),
                processing_time=processing_time,
                metadata=response_metadata,
                tool_calls=tool_calls,
            )
        except APITimeoutError as te:
            processing_time = time.time() - start_time
            logger.error(
                f"LLM request timed out for intent {intent_type} after {processing_time:.2f}s: {te!s}"
            )
            error_metadata = {
                "success": False,
                "error": f"LLM request timed out: {te!s}",
                "error_type": te.__class__.__name__,
                "processing_time": processing_time,
            }
            if intent_type:
                error_metadata["intent_type"] = str(intent_type)
            return LLMResponse(
                response="The request to the language model timed out. Please try again later or simplify your request.",
                model_used=openai_model,
                tokens_used=0,
                processing_time=processing_time,
                metadata=error_metadata,
                tool_calls=None,
            )
        except Exception as e:
            processing_time = time.time() - start_time
            error_type_str = e.__class__.__name__
            error_str = str(e)
            logger.error(
                f"Failed to process request for intent {intent_type} after {processing_time:.2f}s: {error_type_str} - {error_str}"
            )
            error_metadata = {
                "success": False,
                "error": error_str,
                "error_type": error_type_str,
                "processing_time": processing_time,
            }
            if intent_type:
                error_metadata["intent_type"] = str(intent_type)
            return LLMResponse(
                response=f"INTERNAL ROUTER ERROR ({error_type_str}): {error_str}",
                model_used=openai_model,
                tokens_used=1,
                processing_time=processing_time,
                metadata=error_metadata,
                tool_calls=None,
            )

    def process_streaming(
        self,
        request: LLMRequest,
        intent_type: RequestType | None = None,
    ) -> AsyncGenerator[LLMStreamResponse, None]:
        """
        Process a streaming LLM request and yield LLMStreamResponse objects.
        """
        return self._process_stream(request, intent_type)

    async def _process_stream(
        self, request: LLMRequest, intent_type: RequestType | None = None
    ) -> AsyncGenerator[LLMStreamResponse, None]:
        """
        Internal: Process a streaming LLM request.
        """
        start_time = time.time()
        if request.model_name_override:
            openai_model = request.model_name_override
            logger.info(
                "Streaming: using model from use case config: %s",
                openai_model,
            )
        else:
            effective_intent = intent_type if intent_type is not None else RequestType.QUERY
            openai_model = self.model_selector.get_model_for_intent(effective_intent)
        full_response = ""
        chunk_count = 0

        try:
            # Build messages array for streaming
            if request.messages:
                messages_for_stream = request.messages
                logger.info(
                    "Using %d messages from request for streaming",
                    len(messages_for_stream),
                )
            else:
                messages_for_stream = [{"role": "user", "content": request.prompt}]

            streaming_generator = self._get_streaming_generator(
                messages=messages_for_stream,
                openai_model=openai_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                intent_type=intent_type,
                tools=request.tools,
                tool_choice=request.tool_choice,
                response_format=request.response_format,
            )

            async for stream_response in streaming_generator:
                chunk_count += 1
                response_text = stream_response.response
                chunk_len = len(response_text) if response_text else 0
                logger.debug(
                    f"Received chunk #{chunk_count}: length={chunk_len}, content={repr(response_text)[:50]}{'...' if len(repr(response_text)) > 50 else ''}"
                )
                full_response += response_text
                logger.debug(f"Accumulated response length: {len(full_response)}")
                yield stream_response

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Streaming error after {processing_time:.2f}s: {e!s}")
            error_metadata = {
                "success": False,
                "error": str(e),
                "error_type": e.__class__.__name__,
                "processing_time": processing_time,
                "is_complete": True,
            }
            if intent_type:
                error_metadata["intent_type"] = str(intent_type)
            response = LLMStreamResponse(
                response=full_response
                or "Error processing streaming request. Please try again later.",
                model_used=openai_model,
                tokens_used=1,
                processing_time=processing_time,
                chunk_number=chunk_count,
                is_final=True,
                metadata=error_metadata,
                tool_calls=None,
            )
            yield response

    def _get_streaming_generator(
        self,
        messages: list[dict[str, str]],
        openai_model: str,
        temperature: float,
        max_tokens: int,
        intent_type: RequestType | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> StreamingResponseGenerator:
        """
        Create a StreamingResponseGenerator for streaming LLM responses.

        Args:
            messages: OpenAI-style messages array
            openai_model: Model ID to use (from use-case override or intent default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            intent_type: Optional intent type for metadata
            tools: Optional tools list
            tool_choice: Optional tool choice strategy
            response_format: Optional response format constraint
        """
        messages_typed: list[ChatCompletionMessageParam] = messages  # type: ignore
        initial_metadata = {}
        if intent_type:
            initial_metadata["intent_type"] = intent_type.value
        return StreamingResponseGenerator(
            client=self.client,
            model=openai_model,
            messages=messages_typed,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=initial_metadata,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
        )

    async def _get_response(
        self,
        openai_model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float,
        max_tokens: int,
        model_type: ModelType,
        intent_type: RequestType | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> tuple[str | None, dict[str, Any], list[dict[str, Any]] | None]:
        """
        Get a non-streaming response from the model, with fallback logic.

        Returns:
            Tuple of (response_text, metadata, tool_calls)
        """
        start_time = time.time()
        metadata = {
            "attempt": 1,
            "original_model": model_type,
            "request_time": datetime.utcnow().isoformat(),
        }
        if intent_type:
            metadata["intent_type"] = str(intent_type)

        try:
            logger.info(f"Sending request to {openai_model} (internal: {model_type})")
            response = await self.client.make_async_completion_request(
                model=openai_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
            )

            message = response.choices[0].message
            response_text = message.content
            tool_calls_data = None

            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls_data = [tool_call.model_dump() for tool_call in message.tool_calls]
                logger.info(f"Received {len(tool_calls_data)} tool calls from {openai_model}")

            processing_time = time.time() - start_time

            if hasattr(response, "usage") and response.usage is not None:
                metadata.update(
                    {
                        "success": True,
                        "processing_time": processing_time,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "model_id": openai_model,  # Store actual model ID for cost estimation
                    }
                )
                logger.info(
                    f"Received response from {openai_model} in {processing_time:.2f}s "
                    f"(tokens: {response.usage.total_tokens})"
                )
            else:
                metadata.update(
                    {
                        "success": True,
                        "processing_time": processing_time,
                        "prompt_tokens": 1,
                        "completion_tokens": 1,
                        "total_tokens": 1,
                        "model_id": openai_model,  # Store actual model ID for cost estimation
                    }
                )
                logger.info(
                    f"Received response from {openai_model} in {processing_time:.2f}s (tokens: unknown)"
                )
            return response_text, metadata, tool_calls_data

        except APITimeoutError as te:
            processing_time = time.time() - start_time
            logger.error(
                "Timeout error with %s after %.2fs: %s",
                openai_model,
                processing_time,
                te,
            )
            raise te

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Error with %s after %.2fs: %s",
                openai_model,
                processing_time,
                e,
            )
            raise RuntimeError(f"Failed to get response from model {openai_model}: {e!s}") from e
