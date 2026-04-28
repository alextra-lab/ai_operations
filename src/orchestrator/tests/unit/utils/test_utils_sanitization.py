from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.utils.sanitization import sanitize_input


@pytest.mark.asyncio
async def test_sanitize_input_success_modified():
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "sanitized_text": "cleaned",
                    "risk_score": 0.8,
                    "modified": True,
                }
            ),
        )
    )
    with (
        patch("httpx.AsyncClient", return_value=mock_instance),
        patch("app.utils.sanitization.logger") as mock_logger,
    ):
        result = await sanitize_input("dirty", user_id="u", request_id="r")
        assert result == ("cleaned", 0.8, True)
        assert mock_logger.warning.called


@pytest.mark.asyncio
async def test_sanitize_input_success_not_modified():
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "sanitized_text": "original",
                    "risk_score": 0.1,
                    "modified": False,
                }
            ),
        )
    )
    with (
        patch("httpx.AsyncClient", return_value=mock_instance),
        patch("app.utils.sanitization.logger") as mock_logger,
    ):
        result = await sanitize_input("original")
        assert result == ("original", 0.1, False)
        assert mock_logger.info.called


@pytest.mark.asyncio
async def test_sanitize_input_non_200():
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(
        return_value=MagicMock(status_code=400, text="fail")
    )
    with (
        patch("httpx.AsyncClient", return_value=mock_instance),
        patch("app.utils.sanitization.logger") as mock_logger,
    ):
        result = await sanitize_input("input")
        assert result == ("input", 0.0, False)
        assert mock_logger.error.called


@pytest.mark.asyncio
async def test_sanitize_input_exception():
    mock_instance = MagicMock()
    mock_instance.__aenter__.return_value.post = AsyncMock(side_effect=Exception("fail"))
    with (
        patch("httpx.AsyncClient", return_value=mock_instance),
        patch("app.utils.sanitization.logger") as mock_logger,
    ):
        result = await sanitize_input("input")
        assert result == ("input", 0.0, False)
        assert mock_logger.exception.called
