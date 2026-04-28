"""
Ephemeral Conversation Cache Service

Provides thread-safe, encrypted, model-aware caching for conversation history
to support stateless multi-turn conversations without persistent storage.

Security Features:
- AES-GCM encryption with process-ephemeral master key
- Per-conversation key derivation (HKDF)
- Encrypted at rest (even in RAM)
- Master key never persisted
- Key lost on restart = ciphertext useless

Performance Features:
- In-memory storage (ephemeral)
- Absolute TTL + idle timeout
- Thread-safe operations
- Model-aware token limits (from context_window)
- LRU eviction

Architecture:
- Client-owned session IDs
- No persistent state
- Defense in depth for sensitive SOC data
- Cache mirrors LLM context window behavior

Token Counting:
- v1: Simple heuristic (~4 chars per token)
- v1.2: Upgrade to tiktoken for exact counting

Related ADRs:
- ADR-030: Stateless architecture
- ADR-034: Conversations as QUERY pattern

This supports the stateless architecture defined in ADR-030 while providing
enterprise-grade security for sensitive operational data.
"""

import json
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)


# ============================================================================
# Token Estimation (v1 - Simple Heuristic)
# ============================================================================
# v1.2 TODO: Replace with tiktoken for accurate counting
# ============================================================================


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using simple heuristic.

    Rule of thumb: ~4 characters per token for English text.
    This is a rough approximation (±15%) good enough for cache management.

    v1.2: Replace with tiktoken.encoding_for_model().encode()

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return max(len(text) // 4, 1)


def estimate_message_tokens(message: dict[str, Any]) -> int:
    """
    Estimate tokens for a single message including role overhead.

    Format overhead:
    - Role marker: ~4 tokens (e.g., "user:", "assistant:")
    - Message structure: ~3 tokens

    v1.2: Use tiktoken with proper message formatting

    Args:
        message: Message dict with 'role' and 'content'

    Returns:
        Estimated token count
    """
    role_overhead = 7  # Role + formatting tokens
    content_tokens = estimate_tokens(message.get("content", ""))
    return role_overhead + content_tokens


def estimate_conversation_tokens(messages: list[dict[str, Any]]) -> int:
    """
    Estimate total tokens for conversation history.

    System overhead:
    - Conversation structure: ~10 tokens
    - Message array formatting: ~3 tokens per message

    v1.2: Use tiktoken with exact chat completion format

    Args:
        messages: List of message dictionaries

    Returns:
        Estimated total token count
    """
    if not messages:
        return 0

    system_overhead = 10  # Conversation structure tokens
    message_tokens = sum(estimate_message_tokens(m) for m in messages)
    return system_overhead + message_tokens


@dataclass
class CacheEntry:
    """Represents an encrypted, cached conversation session."""

    session_id: str
    ciphertext: bytes  # Encrypted conversation data
    nonce: bytes  # AES-GCM nonce (96 bits)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    expires_at: float = field(init=False)
    turn_count: int = 0
    token_count: int = 0  # Estimated tokens (v1: chars/4, v1.2: tiktoken)
    size_bytes: int = 0  # For monitoring only
    ttl_seconds: int = 86400  # 24 hours default
    idle_seconds: int = 900  # 15 minutes default

    def __post_init__(self) -> None:
        """Calculate expiration time."""
        self.expires_at = self.created_at + self.ttl_seconds

    def is_expired(self, idle_timeout: int) -> bool:
        """
        Check if this entry has expired.

        Args:
            idle_timeout: Idle timeout in seconds

        Returns:
            True if expired (absolute TTL or idle timeout)
        """
        now = time.time()
        absolute_expired = now > self.expires_at
        idle_expired = (now - self.last_accessed) > idle_timeout
        return absolute_expired or idle_expired

    def touch(self) -> None:
        """Update last accessed time (does NOT extend absolute TTL)."""
        self.last_accessed = time.time()


class ConversationCache:
    """
    Thread-safe, encrypted, TTL-based in-memory cache for conversation history.

    This cache provides ephemeral storage for multi-turn conversations with:
    - AES-GCM encryption (encrypted at rest, even in RAM)
    - Process-ephemeral master key (lost on restart)
    - Per-conversation key derivation (HKDF)
    - Absolute TTL + idle timeout
    - Size and turn limits

    Security:
        - Master key generated at init, never persisted
        - Per-conversation DEK derived via HKDF(master_key, session_id)
        - AES-GCM AEAD with session_id as AAD
        - Restart = lose key = ciphertext useless

    Thread Safety:
        All operations protected by threading.Lock

    Expiration:
        - Absolute TTL: Max lifetime from creation
        - Idle timeout: Max time since last access
        - Accessing does NOT extend absolute TTL
        - Expired entries purged on access and periodically

    Example:
        ```python
        cache = ConversationCache(
            ttl_seconds=3600,
            idle_seconds=900,
            max_bytes=131072,
            max_turns=30
        )

        # Store conversation history (encrypted automatically)
        cache.set("session_123", [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ])

        # Retrieve (decrypted automatically)
        history = cache.get("session_123")

        # Append new message
        cache.append("session_123", "user", "What is a SOC?")
        ```
    """

    def __init__(
        self,
        ttl_seconds: int = 86400,
        idle_seconds: int = 900,
        max_entries: int = 10000,
        default_max_tokens: int = 8000,  # Default if model not specified
        default_max_turns: int = 50,
    ) -> None:
        """
        Initialize the encrypted conversation cache.

        Note: max_tokens should be set based on the model's context_window.
        Use set_limits_from_model() to configure per-model limits dynamically.

        Args:
            ttl_seconds: Absolute TTL in seconds (default: 24 hours)
            idle_seconds: Idle timeout in seconds (default: 15 minutes)
            max_entries: Maximum number of sessions (LRU eviction)
            default_max_tokens: Default max tokens if model not specified (default: 8K)
            default_max_turns: Default max turns (default: 50)
        """
        self.ttl_seconds = ttl_seconds
        self.idle_seconds = idle_seconds
        self.max_entries = max_entries
        self.default_max_tokens = default_max_tokens
        self.default_max_turns = default_max_turns

        # Model-specific limits (can be updated per session)
        self._session_limits: dict[str, dict[str, int]] = {}

        # Process-ephemeral master key (AES-256)
        # NEVER persisted - lost on restart by design
        self._master_key = os.urandom(32)

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

        logger.info(
            "Encrypted ConversationCache initialized",
            extra={
                "ttl_seconds": ttl_seconds,
                "idle_seconds": idle_seconds,
                "max_entries": max_entries,
                "default_max_tokens": default_max_tokens,
                "default_max_turns": default_max_turns,
                "encryption": "AES-GCM-256",
            },
        )

    def set_session_limits(
        self,
        session_id: str,
        max_tokens: int,
        max_turns: int | None = None,
        reserved_response_tokens: int = 2000,
    ) -> None:
        """
        Set token limits for a specific session based on model's context window.

        Args:
            session_id: Client-owned session identifier
            max_tokens: Model's context_window or max_input_tokens
            max_turns: Optional max turns override
            reserved_response_tokens: Tokens to reserve for model response
        """
        with self._lock:
            # Reserve space for response
            cache_max_tokens = max(max_tokens - reserved_response_tokens, 1000)

            self._session_limits[session_id] = {
                "max_tokens": cache_max_tokens,
                "max_turns": max_turns or self.default_max_turns,
                "model_context_window": max_tokens,
                "reserved_response_tokens": reserved_response_tokens,
            }

            logger.debug(
                "Session limits configured from model",
                extra={
                    "session_id": session_id,
                    "cache_max_tokens": cache_max_tokens,
                    "model_context_window": max_tokens,
                    "reserved_response_tokens": reserved_response_tokens,
                },
            )

    def _get_session_limits(self, session_id: str) -> dict[str, int]:
        """Get limits for a session, falling back to defaults."""
        return self._session_limits.get(
            session_id,
            {
                "max_tokens": self.default_max_tokens,
                "max_turns": self.default_max_turns,
                "model_context_window": self.default_max_tokens,
                "reserved_response_tokens": 0,
            },
        )

    def _derive_key(self, session_id: str) -> bytes:
        """
        Derive a per-conversation encryption key using HKDF.

        Args:
            session_id: Client-owned session identifier

        Returns:
            32-byte AES-256 key unique to this conversation
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=f"ephemeral-cache:{session_id}".encode(),
        )
        return hkdf.derive(self._master_key)

    def _encrypt(self, session_id: str, plaintext: bytes) -> tuple[bytes, bytes]:
        """
        Encrypt conversation data with AES-GCM.

        Args:
            session_id: Used as AAD and for key derivation
            plaintext: Conversation data as JSON bytes

        Returns:
            Tuple of (ciphertext, nonce)
        """
        dek = self._derive_key(session_id)
        aes = AESGCM(dek)
        nonce = os.urandom(12)  # 96 bits for AES-GCM
        aad = session_id.encode()  # Additional authenticated data
        ciphertext = aes.encrypt(nonce, plaintext, aad)
        return ciphertext, nonce

    def _decrypt(self, session_id: str, ciphertext: bytes, nonce: bytes) -> bytes:
        """
        Decrypt conversation data with AES-GCM.

        Args:
            session_id: Used as AAD and for key derivation
            ciphertext: Encrypted conversation data
            nonce: 96-bit nonce used during encryption

        Returns:
            Decrypted plaintext as bytes

        Raises:
            cryptography.exceptions.InvalidTag: If authentication fails
        """
        dek = self._derive_key(session_id)
        aes = AESGCM(dek)
        aad = session_id.encode()
        return aes.decrypt(nonce, ciphertext, aad)

    def get(self, session_id: str) -> list[dict[str, Any]] | None:
        """
        Retrieve and decrypt conversation history for a session.

        Args:
            session_id: Client-owned session identifier

        Returns:
            List of message dictionaries, or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(session_id)

            if not entry:
                return None

            # Check if expired (both absolute and idle)
            if entry.is_expired(self.idle_seconds):
                logger.debug(
                    "Cache entry expired",
                    extra={
                        "session_id": session_id,
                        "age_seconds": time.time() - entry.created_at,
                        "idle_seconds": time.time() - entry.last_accessed,
                    },
                )
                del self._cache[session_id]
                return None

            # Decrypt conversation data
            try:
                plaintext = self._decrypt(session_id, entry.ciphertext, entry.nonce)
                messages = json.loads(plaintext.decode("utf-8"))
            except (ValueError, KeyError, UnicodeDecodeError) as e:
                logger.error(
                    "Failed to decrypt cache entry",
                    extra={"session_id": session_id, "error": str(e)},
                )
                # Remove corrupted entry
                del self._cache[session_id]
                return None

            # Touch entry (updates access time, NOT expiration)
            entry.touch()

            # Move to end (LRU)
            self._cache.move_to_end(session_id)

            return cast("list[dict[str, Any]]", messages)

    def set(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """
        Encrypt and store conversation history for a session.

        Args:
            session_id: Client-owned session identifier
            messages: List of message dictionaries with role/content

        Raises:
            ValueError: If messages exceed size or turn limits
        """
        with self._lock:
            # Get limits for this session
            limits = self._get_session_limits(session_id)

            # Validate turn limit
            if len(messages) > limits["max_turns"]:
                raise ValueError(f"Turn limit exceeded: {len(messages)} > {limits['max_turns']}")

            # Calculate token count
            token_count = estimate_conversation_tokens(messages)

            # Validate token limit
            if token_count > limits["max_tokens"]:
                raise ValueError(f"Token limit exceeded: {token_count} > {limits['max_tokens']}")

            # Serialize to JSON
            plaintext = json.dumps(messages).encode("utf-8")
            size_bytes = len(plaintext)

            # Encrypt conversation data
            ciphertext, nonce = self._encrypt(session_id, plaintext)

            # Create encrypted cache entry
            entry = CacheEntry(
                session_id=session_id,
                ciphertext=ciphertext,
                nonce=nonce,
                turn_count=len(messages),
                token_count=token_count,
                size_bytes=size_bytes,
                ttl_seconds=self.ttl_seconds,
                idle_seconds=self.idle_seconds,
            )

            self._cache[session_id] = entry
            self._cache.move_to_end(session_id)

            # Enforce max entries (LRU eviction)
            while len(self._cache) > self.max_entries:
                oldest_key = next(iter(self._cache))
                removed_entry = self._cache.pop(oldest_key)
                logger.debug(
                    "Cache eviction (max entries)",
                    extra={
                        "evicted_session": oldest_key,
                        "age_seconds": time.time() - removed_entry.created_at,
                    },
                )

            logger.debug(
                "Cache entry stored (encrypted)",
                extra={
                    "session_id": session_id,
                    "turn_count": len(messages),
                    "token_count": token_count,
                    "size_bytes": size_bytes,
                },
            )

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Append a new message to an existing conversation (decrypt, append, re-encrypt).

        Args:
            session_id: Client-owned session identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata (model, tokens, etc.)

        Returns:
            True if appended successfully, False if session not found/expired

        Raises:
            ValueError: If appending would exceed size or turn limits
        """
        with self._lock:
            entry = self._cache.get(session_id)

            if not entry:
                logger.debug(
                    "Cannot append to non-existent session",
                    extra={"session_id": session_id},
                )
                return False

            if entry.is_expired(self.idle_seconds):
                logger.debug("Cannot append to expired session", extra={"session_id": session_id})
                del self._cache[session_id]
                return False

            # Decrypt existing messages
            try:
                plaintext = self._decrypt(session_id, entry.ciphertext, entry.nonce)
                messages = json.loads(plaintext.decode("utf-8"))
            except (ValueError, KeyError, UnicodeDecodeError) as e:
                logger.error(
                    "Failed to decrypt for append",
                    extra={"session_id": session_id, "error": str(e)},
                )
                return False

            # Get limits for validation
            limits = self._get_session_limits(session_id)

            # Build new message
            new_message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            # Calculate new token count
            new_message_tokens = estimate_message_tokens(new_message)
            new_total_tokens = entry.token_count + new_message_tokens
            new_turn_count = entry.turn_count + 1

            # Validate limits
            if new_turn_count > limits["max_turns"]:
                raise ValueError(
                    f"Turn limit would be exceeded: {new_turn_count} > {limits['max_turns']}"
                )

            if new_total_tokens > limits["max_tokens"]:
                raise ValueError(
                    f"Token limit would be exceeded: {new_total_tokens} > {limits['max_tokens']}"
                )

            # Append message
            messages.append(new_message)

            # Re-encrypt updated conversation
            updated_plaintext = json.dumps(messages).encode("utf-8")
            updated_ciphertext, updated_nonce = self._encrypt(session_id, updated_plaintext)

            # Update entry
            entry.ciphertext = updated_ciphertext
            entry.nonce = updated_nonce
            entry.turn_count = new_turn_count
            entry.token_count = new_total_tokens
            entry.size_bytes = len(updated_plaintext)
            entry.touch()

            self._cache.move_to_end(session_id)

            logger.debug(
                "Message appended (re-encrypted)",
                extra={
                    "session_id": session_id,
                    "role": role,
                    "new_tokens": new_message_tokens,
                    "total_tokens": new_total_tokens,
                    "turn_count": new_turn_count,
                },
            )

            return True

    def delete(self, session_id: str) -> bool:
        """
        Delete a session from the cache.

        Args:
            session_id: Client-owned session identifier

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]
                logger.debug("Cache entry deleted", extra={"session_id": session_id})
                return True
            return False

    def clear_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                session_id
                for session_id, entry in self._cache.items()
                if entry.is_expired(self.idle_seconds)
            ]

            for session_id in expired_keys:
                del self._cache[session_id]

            if expired_keys:
                logger.info("Expired cache entries cleared", extra={"count": len(expired_keys)})

            return len(expired_keys)

    def get_session_stats(self, session_id: str) -> dict[str, Any] | None:
        """
        Get utilization statistics for a specific session (model-aware).

        Args:
            session_id: Client-owned session identifier

        Returns:
            Dictionary with session stats including token utilization, or None if not found
        """
        with self._lock:
            entry = self._cache.get(session_id)

            if not entry:
                return None

            # Check if expired
            if entry.is_expired(self.idle_seconds):
                return None

            # Get model-specific limits for this session
            limits = self._get_session_limits(session_id)
            max_tokens = limits["max_tokens"]
            max_turns = limits["max_turns"]

            # Calculate utilization percentages (token-based, like LLM context window)
            token_percentage = int((entry.token_count / max_tokens) * 100) if max_tokens > 0 else 0
            turn_percentage = int((entry.turn_count / max_turns) * 100) if max_turns > 0 else 0

            # Use token percentage as primary indicator
            primary_percentage = max(token_percentage, turn_percentage)

            # Determine if compression will occur soon (>80% threshold)
            compression_threshold_pct = 80
            will_compress = primary_percentage >= compression_threshold_pct

            return {
                "session_id": session_id,
                # Token-based metrics (primary)
                "tokens_used": entry.token_count,
                "max_tokens": max_tokens,
                "token_percentage": token_percentage,
                # Turn-based metrics (secondary)
                "turn_count": entry.turn_count,
                "max_turns": max_turns,
                "turn_percentage": turn_percentage,
                # Utilization (shown in UI)
                "utilization_percentage": primary_percentage,
                "will_compress": will_compress,
                "compression_threshold": compression_threshold_pct,
                # Model info
                "model_context_window": limits["model_context_window"],
                "reserved_response_tokens": limits["reserved_response_tokens"],
                # Expiration info
                "ttl_remaining_seconds": int(entry.expires_at - time.time()),
                "idle_remaining_seconds": int(
                    self.idle_seconds - (time.time() - entry.last_accessed)
                ),
                # Timestamps
                "created_at": datetime.fromtimestamp(entry.created_at).isoformat(),
                "last_accessed": datetime.fromtimestamp(entry.last_accessed).isoformat(),
                # Metadata (for debugging)
                "size_bytes": entry.size_bytes,
                "estimation_method": "heuristic_v1",  # v1.2: "tiktoken"
            }

    def get_stats(self) -> dict[str, Any]:
        """
        Get global cache statistics.

        Returns:
            Dictionary with global cache stats including token usage
        """
        with self._lock:
            expired_count = sum(
                1 for entry in self._cache.values() if entry.is_expired(self.idle_seconds)
            )
            total_turns = sum(entry.turn_count for entry in self._cache.values())
            total_tokens = sum(entry.token_count for entry in self._cache.values())
            total_bytes = sum(entry.size_bytes for entry in self._cache.values())

            return {
                "total_sessions": len(self._cache),
                "total_turns": total_turns,
                "total_tokens": total_tokens,
                "total_bytes": total_bytes,
                "expired_sessions": expired_count,
                "max_entries": self.max_entries,
                "default_max_tokens": self.default_max_tokens,
                "default_max_turns": self.default_max_turns,
                "ttl_seconds": self.ttl_seconds,
                "idle_seconds": self.idle_seconds,
                "encryption": "AES-GCM-256",
                "token_estimation": "heuristic_v1",  # v1.2: "tiktoken"
            }


# Global cache instance (singleton pattern)
_global_cache: ConversationCache | None = None


def get_conversation_cache(
    ttl_seconds: int = 86400,
    idle_seconds: int = 900,
    max_entries: int = 10000,
    default_max_tokens: int = 8000,
    default_max_turns: int = 50,
) -> ConversationCache:
    """
    Get or create the global conversation cache instance.

    Args:
        ttl_seconds: Absolute TTL in seconds (default: 24 hours)
        idle_seconds: Idle timeout in seconds (default: 15 minutes)
        max_entries: Maximum number of sessions to store
        default_max_tokens: Default max tokens if model not specified (default: 8K)
        default_max_turns: Default max turns if not specified (default: 50)

    Returns:
        Global ConversationCache instance (encrypted, model-aware)
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = ConversationCache(
            ttl_seconds=ttl_seconds,
            idle_seconds=idle_seconds,
            max_entries=max_entries,
            default_max_tokens=default_max_tokens,
            default_max_turns=default_max_turns,
        )

    return _global_cache
