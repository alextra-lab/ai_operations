"""
HTTP client for interacting with the Embedding Service.
"""

import asyncio
from logging import DEBUG
from types import TracebackType
from typing import Any, Self, cast

import aiohttp
import backoff
from pydantic import BaseModel

from shared.logging_utils.fastapi import configure_logging

logging = configure_logging(service_name="embedding_client")


# Custom Exceptions
class EmbeddingServiceError(Exception):
    """Base exception for Embedding Service client errors."""


class EmbeddingAuthenticationError(EmbeddingServiceError):
    """Raised when authentication with the Embedding Service fails."""


class EmbeddingTimeoutError(EmbeddingServiceError):
    """Raised when a request to the Embedding Service times out."""


class EmbeddingClientConfigurationError(EmbeddingServiceError):
    """Raised for configuration issues with the client."""


# OpenAI-compatible request schema that matches the embedding service /v1/embeddings endpoint
class OpenAIEmbeddingRequest(BaseModel):
    input: list[str]  # List of input strings to embed
    model: str  # Model name (required for OpenAI compatibility)
    encoding_format: str | None = "float"  # Format for embeddings
    user: str | None = None  # User identifier


class EmbeddingUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingObject(BaseModel):
    object: str = "embedding"
    embedding: list[float]
    index: int


class OpenAIEmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingObject]
    model: str
    usage: EmbeddingUsage


class EmbeddingServiceClient:
    """
    Asynchronous client for the Embedding Service.
    """

    DEFAULT_MAX_RETRIES_FOR_DECORATOR = 3

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,  # Instance specific, could be used for manual retry logic if needed
        batch_size: int = 32,  # Default batch size
        model_name: str | None = None,  # Default model to request
    ):
        if not base_url:
            raise EmbeddingClientConfigurationError("Embedding Service base_url is required.")

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries  # Instance copy, decorator uses class var
        self.batch_size = batch_size
        self.model_name = model_name

        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        """Initializes session for async context manager."""
        await self._get_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Closes session for async context manager."""
        await self.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Initializes and returns the aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            connector = aiohttp.TCPConnector(limit_per_host=100)  # Sensible default limit
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                connector=connector,
            )
        return self._session

    @staticmethod
    def _should_retry(e: Exception) -> bool:
        """Determines if an exception warrants a retry."""
        if isinstance(
            e,
            aiohttp.ClientConnectionError | aiohttp.ClientPayloadError | asyncio.TimeoutError,
        ):
            return True
        if isinstance(e, aiohttp.ClientResponseError):
            # Retry on server errors (5xx) and rate limiting (429)
            return e.status >= 500 or e.status == 429
        return False

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=DEFAULT_MAX_RETRIES_FOR_DECORATOR + 1,
        giveup=lambda e: not EmbeddingServiceClient._should_retry(e),  # Call static method
        on_backoff=lambda details: logging.warning(
            f"Backing off {details.get('wait', 0.0):.1f}s after {details['tries']} tries "  # Safe access to 'wait'
            f"calling {details['target'].__name__} with args {details['args']} and kwargs {details['kwargs']}"
        ),
        on_giveup=lambda details: logging.error(
            f"Gave up calling {details['target'].__name__} after {details['tries']} tries."
        ),
    )
    async def embed_texts(
        self,
        texts: list[str],
        model: str | None = None,
        provider: str | None = None,
        auth_token: str | None = None,
    ) -> list[EmbeddingObject]:
        """
        Generates embeddings for a list of texts.

        Args:
            texts: A list of strings to embed.
            model: Optional model name to override the client's default.
            provider: Optional provider name. If specified, uses provider-specific endpoint.
            auth_token: Optional auth token for this request.

        Returns:
            A list of EmbeddingObject containing the embeddings.

        Raises:
            EmbeddingServiceError: If the request fails after retries or for other reasons.
            EmbeddingAuthenticationError: If authentication fails (401/403).
            EmbeddingTimeoutError: If the request times out.
        """
        if not texts:
            return []

        # Use per-request auth token if provided, otherwise use default session
        if auth_token:
            # Create temporary session with the provided token
            headers = {"Authorization": f"Bearer {auth_token}"}
            connector = aiohttp.TCPConnector(limit_per_host=100)
            session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                connector=connector,
            )
            should_close_session = True
        else:
            session = await self._get_session()
            should_close_session = False

        results: list[EmbeddingObject] = []
        request_model = model or self.model_name or "local"

        # Use provider-specific endpoint if provider is specified, otherwise use OpenAI-compatible endpoint
        if provider:
            # Use provider-specific endpoint for explicit provider routing
            embeddings_url = f"{self.base_url}/embed/provider/{provider}"
            # Construct EmbeddingRequest payload manually (can't import from embedding service)
            # Format: {"texts": [...], "model": "...", "user": null}

            try:
                for i in range(0, len(texts), self.batch_size):
                    batch = texts[i : i + self.batch_size]
                    # Construct payload matching EmbeddingRequest schema
                    payload: dict[str, Any] = {"texts": batch}
                    if request_model:
                        payload["model"] = request_model

                    logging.debug(
                        f"Sending batch of {len(batch)} texts to embedding service via provider {provider}."
                    )

                    try:
                        response = await session.post(embeddings_url, json=payload)

                        # Handle auth errors specifically first
                        if response.status == 401 or response.status == 403:
                            error_text = await response.text()
                            raise EmbeddingAuthenticationError(
                                f"Authentication failed: {error_text}"
                            )

                        response.raise_for_status()
                        response_data = await response.json()
                        # Parse EmbeddingResponse format: {"vectors": [[...], ...], "usage": {...}}
                        vectors = response_data.get("vectors", [])
                        for vector in vectors:
                            results.append(
                                EmbeddingObject(
                                    embedding=vector,
                                    index=len(results),
                                )
                            )
                    except aiohttp.ClientResponseError as e:
                        if e.status == 401 or e.status == 403:
                            raise EmbeddingAuthenticationError(
                                f"Authentication failed: {e.message}"
                            )
                        raise EmbeddingServiceError(
                            f"HTTP error from embedding service: {e.status} - {e.message}"
                        )
            finally:
                if should_close_session and session:
                    await session.close()
            return results
        # Use OpenAI-compatible /v1/embeddings endpoint for auto-detection
        # The embedding service will route to the correct provider based on the model name
        # LMStudio and other providers expose /v1/embeddings, so this is the standard interface
        embeddings_url = f"{self.base_url}/v1/embeddings"

        try:
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i : i + self.batch_size]
                payload = OpenAIEmbeddingRequest(input=batch, model=request_model).model_dump(
                    exclude_none=True
                )

                logging.debug(f"Sending batch of {len(batch)} texts to embedding service.")

                try:
                    response = await session.post(embeddings_url, json=payload)

                    # Handle auth errors specifically first, as they are not typically retried by _should_retry
                    if response.status == 401 or response.status == 403:
                        response_data_auth_err = await response.json()  # Try to get error details
                        logging.error(
                            f"Authentication error ({response.status}) with Embedding Service: {response_data_auth_err}"
                        )
                        raise EmbeddingAuthenticationError(
                            f"Authentication failed ({response.status}): {response_data_auth_err.get('detail', 'Unauthorized')}"
                        )

                    response.raise_for_status()  # Raises ClientResponseError for other 4xx/5xx

                    # If no error was raised by raise_for_status(), and response is ok, proceed to parse.
                    if response.ok:
                        response_data_success = await response.json()
                        parsed_response = OpenAIEmbeddingResponse.model_validate(
                            response_data_success
                        )
                        results.extend(parsed_response.data)
                        logging.debug(f"Received {len(parsed_response.data)} embeddings for batch.")
                    else:
                        # This block should ideally not be reached if raise_for_status() worked as expected for all errors.
                        # It acts as a safeguard if raise_for_status() did not raise for a non-OK status.
                        logging.warning(
                            f"Response status {response.status} was not 'ok' but raise_for_status() did not raise prior to this check. Attempting to raise error."
                        )
                        # Try to raise again or construct a generic error.
                        # This ensures that we don't proceed to parse non-OK responses as success.
                        response.raise_for_status()  # This should raise if it hasn't already.
                        # If it still hasn't raised (e.g. faulty mock or unusual response object), raise a generic error.
                        error_text = await response.text()  # Get raw text for error message
                        raise EmbeddingServiceError(
                            f"Request failed with status {response.status} but did not raise via raise_for_status: {error_text}"
                        )

                except aiohttp.ClientResponseError as e:
                    if EmbeddingServiceClient._should_retry(e):
                        # Re-raise the original ClientResponseError for backoff to handle the retry
                        raise
                    # For non-retryable ClientResponseErrors (e.g., 400, 404 not covered by auth)
                    logging.error(
                        f"Non-retryable HTTP error calling Embedding Service: {e.status} {e.message} - {e.history}"
                    )
                    raise EmbeddingServiceError(
                        f"Embedding Service request failed with status {e.status}: {e.message}"
                    ) from e
                except (aiohttp.ClientConnectionError, aiohttp.ClientPayloadError) as e:
                    logging.error(f"Connection/Payload error calling Embedding Service: {e}")
                    raise EmbeddingServiceError(
                        f"Embedding Service connection/payload error: {e}"
                    ) from e
                except TimeoutError as e:  # Raised by aiohttp.ClientTimeout
                    logging.error(f"Timeout calling Embedding Service: {embeddings_url}")
                    raise EmbeddingTimeoutError(
                        f"Request to Embedding Service timed out: {embeddings_url}"
                    ) from e
                except Exception as e:  # Catch-all for unexpected errors like JSON parsing
                    logging.exception(f"Unexpected error interacting with Embedding Service: {e}")
                    raise EmbeddingServiceError(f"An unexpected error occurred: {e}") from e

        finally:
            # Close temporary session if we created one
            if should_close_session and session and not session.closed:
                await session.close()

        # Sort results by original index to maintain order
        results.sort(key=lambda eo: eo.index)
        return results

    async def get_service_health(self) -> dict[str, Any]:
        """
        Checks the health of the Embedding Service.
        Assumes a /health endpoint exists on the Embedding Service.
        """
        session = await self._get_session()
        health_url = f"{self.base_url}/health"  # Common health check endpoint

        try:
            async with session.get(health_url) as response:
                response.raise_for_status()
                health_data = await response.json()
                logging.info(f"Embedding Service health check successful: {health_data}")
                return cast("dict[str, Any]", health_data)
        except aiohttp.ClientResponseError as e:
            logging.error(
                f"Embedding Service health check failed with status {e.status}: {e.message}"
            )
            raise EmbeddingServiceError(f"Health check failed ({e.status}): {e.message}") from e
        except (TimeoutError, aiohttp.ClientConnectionError) as e:
            logging.error(f"Embedding Service health check connection/timeout error: {e}")
            raise EmbeddingServiceError(f"Health check connection/timeout error: {e}") from e
        except Exception as e:
            logging.exception(f"Unexpected error during Embedding Service health check: {e}")
            raise EmbeddingServiceError(
                f"An unexpected error occurred during health check: {e}"
            ) from e

    async def close(self) -> None:
        """Closes the aiohttp ClientSession."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logging.info("EmbeddingServiceClient session closed.")


# Example Usage (for testing purposes, typically this client is used within another service)
async def main_example() -> None:
    # This example assumes an embedding service is running at http://localhost:8001
    # and requires a token if authentication is enabled on the service.
    # Replace with actual URL and token if needed.

    # Configure logging to see output
    logging.setLevel(DEBUG)

    client = EmbeddingServiceClient(
        base_url="http://localhost:8001",  # Replace with your embedding service URL
        # token="your-service-token", # Uncomment and replace if your service needs a token
        model_name="all-minilm-l6-v2",  # Example model
    )

    try:
        # Test health check
        # health = await client.get_service_health()
        # print(f"Service Health: {health}")

        # Test embeddings
        texts_to_embed = [
            "Hello world",
            "This is a test sentence.",
            "Another example for embedding.",
        ]
        embeddings = await client.embed_texts(texts_to_embed)

        print(f"\nSuccessfully retrieved {len(embeddings)} embeddings.")
        for emb_obj in embeddings:
            print(f"Index: {emb_obj.index}, Embedding (first 3 dims): {emb_obj.embedding[:3]}...")
            # print(f"Full embedding: {emb_obj.embedding}")

    except EmbeddingServiceError as e:
        print(f"An error occurred: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    # To run this example:
    # 1. Ensure you have an OpenAI-compatible embedding service running.
    #    The `src/embedding` service in this project can be used.
    # 2. Update `base_url` and `token` in `main_example` if necessary.
    # 3. Run this file directly: `python src/retrieval/app/clients/embedding_client.py`
    #    You might need to adjust PYTHONPATH or run from the project root.
    #    Example from project root: `python -m src.retrieval.app.clients.embedding_client`

    # Note: The backoff decorator's max_tries needs access to the instance's max_retries.
    # This is a bit tricky with how Python resolves names at definition time for decorators.
    # A common workaround is to define max_tries directly or use a helper that can access it.
    # For simplicity here, I've used a placeholder in the decorator and it might need adjustment
    # if `max_retries` is dynamically changed after instantiation in a real scenario.
    # The current `_get_session.__func__.__closure__[0].cell_contents.max_retries +1` is a hacky way
    # to try and access it, assuming `max_retries` is the first free variable in `_get_session`'s closure.
    # A cleaner way would be to pass `max_retries` to the decorator if `backoff` supports it,
    # or define a static max_retries for the decorator if that's acceptable.
    # For now, I'll adjust the backoff decorator to use a fixed value or a class variable.

    # Re-defining the backoff decorator for the example to work standalone without complex closure inspection.
    # This is a simplified approach for the example.
    # In a real application, you'd ensure `max_retries` is correctly passed or accessed.

    # Let's assume a fixed max_retries for the example's direct execution.
    # The class implementation itself is fine, this is just for the __main__ block.
    # A better way for the class would be to make max_retries a class variable if it's static,
    # or pass it to the decorator if the library allows dynamic configuration per call/instance.

    # The current implementation of backoff in the class uses a trick to access instance's max_retries.
    # Let's refine the backoff decorator in the class for robustness.
    # The issue is that `max_tries` in `@backoff.on_exception` is evaluated at class definition time.
    # A common pattern is to make the decorated method a wrapper that then calls an inner method
    # where `max_tries` can be dynamically set, or to use a library feature if available.
    # For now, the provided class code will be used, acknowledging this nuance.

    asyncio.run(main_example())
