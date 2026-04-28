"""
Unit tests for Ephemeral Conversation Cache Service.

Tests encryption, TTL, idle timeout, token limits, and thread safety.
"""

import time

import pytest

from src.orchestrator.app.services.conversation_cache import (
    CacheEntry,
    ConversationCache,
    estimate_conversation_tokens,
    estimate_message_tokens,
    estimate_tokens,
    get_conversation_cache,
)


class TestTokenEstimation:
    """Test token estimation heuristics (v1)."""

    def test_estimate_tokens_basic(self):
        """Test basic token estimation (~4 chars per token)."""
        assert estimate_tokens("") == 0
        assert estimate_tokens("test") == 1  # 4 chars = 1 token
        assert estimate_tokens("testing message") >= 3  # 15 chars = ~4 tokens
        assert estimate_tokens("a" * 100) == 25  # 100 chars = 25 tokens

    def test_estimate_message_tokens(self):
        """Test message token estimation with role overhead."""
        msg = {"role": "user", "content": "test"}
        tokens = estimate_message_tokens(msg)
        assert tokens > 1  # Content + role overhead
        assert tokens == 7 + 1  # 7 overhead + 1 for "test"

    def test_estimate_conversation_tokens(self):
        """Test full conversation token estimation."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        tokens = estimate_conversation_tokens(messages)
        assert tokens > 10  # System overhead + messages
        assert tokens == 10 + 7 + 1 + 7 + 2  # overhead + 2 messages


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test CacheEntry initialization."""
        entry = CacheEntry(
            session_id="test_123",
            ciphertext=b"encrypted_data",
            nonce=b"random_nonce",
            turn_count=5,
            token_count=123,
            size_bytes=456,
        )
        assert entry.session_id == "test_123"
        assert entry.turn_count == 5
        assert entry.token_count == 123
        assert entry.expires_at > time.time()

    def test_cache_entry_expiration_absolute(self):
        """Test absolute TTL expiration."""
        entry = CacheEntry(
            session_id="test",
            ciphertext=b"data",
            nonce=b"nonce",
            ttl_seconds=1,  # 1 second TTL
        )
        assert not entry.is_expired(idle_timeout=900)
        time.sleep(1.1)
        assert entry.is_expired(idle_timeout=900)

    def test_cache_entry_expiration_idle(self):
        """Test idle timeout expiration."""
        entry = CacheEntry(
            session_id="test",
            ciphertext=b"data",
            nonce=b"nonce",
            ttl_seconds=3600,
        )
        # Touch to update access time
        entry.touch()
        assert not entry.is_expired(idle_timeout=1)

        time.sleep(1.1)
        assert entry.is_expired(idle_timeout=1)  # Idle timeout

    def test_cache_entry_touch(self):
        """Test touch updates last_accessed but not expiration."""
        entry = CacheEntry(
            session_id="test",
            ciphertext=b"data",
            nonce=b"nonce",
        )
        original_expires = entry.expires_at
        original_accessed = entry.last_accessed

        time.sleep(0.1)
        entry.touch()

        assert entry.last_accessed > original_accessed
        assert entry.expires_at == original_expires  # Unchanged


class TestConversationCache:
    """Test ConversationCache main functionality."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache for each test."""
        return ConversationCache(
            ttl_seconds=3600,
            idle_seconds=900,
            max_entries=100,
            default_max_tokens=1000,
            default_max_turns=10,
        )

    def test_cache_initialization(self, cache):
        """Test cache initializes with ephemeral master key."""
        assert cache._master_key is not None
        assert len(cache._master_key) == 32  # AES-256
        assert cache.ttl_seconds == 3600
        assert cache.idle_seconds == 900

    def test_cache_set_and_get(self, cache):
        """Test basic set and get operations with encryption."""
        session_id = "test_session_1"
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        # Set
        cache.set(session_id, messages)

        # Get
        retrieved = cache.get(session_id)
        assert retrieved is not None
        assert len(retrieved) == 2
        assert retrieved[0]["role"] == "user"
        assert retrieved[0]["content"] == "Hello"

    def test_cache_encryption_round_trip(self, cache):
        """Test encryption and decryption work correctly."""
        session_id = "test_crypto"
        messages = [{"role": "user", "content": "Sensitive data"}]

        cache.set(session_id, messages)

        # Verify stored as ciphertext
        entry = cache._cache[session_id]
        assert isinstance(entry.ciphertext, bytes)
        assert b"Sensitive data" not in entry.ciphertext  # Encrypted!

        # Verify decryption
        retrieved = cache.get(session_id)
        assert retrieved[0]["content"] == "Sensitive data"

    def test_cache_append(self, cache):
        """Test appending messages to existing conversation."""
        session_id = "test_append"

        # Create initial session
        cache.set(session_id, [{"role": "user", "content": "First"}])

        # Append
        result = cache.append(session_id, "assistant", "Response")
        assert result is True

        # Verify
        messages = cache.get(session_id)
        assert len(messages) == 2
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Response"

    def test_cache_append_nonexistent(self, cache):
        """Test append to non-existent session returns False."""
        result = cache.append("nonexistent", "user", "Test")
        assert result is False

    def test_cache_delete(self, cache):
        """Test session deletion."""
        session_id = "test_delete"
        cache.set(session_id, [{"role": "user", "content": "Test"}])

        assert cache.delete(session_id) is True
        assert cache.get(session_id) is None
        assert cache.delete(session_id) is False  # Already deleted

    def test_cache_expiration_absolute(self, cache):
        """Test absolute TTL expiration."""
        cache_short = ConversationCache(ttl_seconds=1, idle_seconds=900)
        session_id = "test_expire"

        cache_short.set(session_id, [{"role": "user", "content": "Test"}])
        assert cache_short.get(session_id) is not None

        time.sleep(1.1)
        assert cache_short.get(session_id) is None  # Expired

    def test_cache_expiration_idle(self, cache):
        """Test idle timeout expiration."""
        cache_short = ConversationCache(ttl_seconds=3600, idle_seconds=1)
        session_id = "test_idle"

        cache_short.set(session_id, [{"role": "user", "content": "Test"}])
        time.sleep(1.1)

        assert cache_short.get(session_id) is None  # Idle timeout

    def test_cache_lru_eviction(self, cache):
        """Test LRU eviction when max_entries exceeded."""
        small_cache = ConversationCache(max_entries=3, default_max_tokens=1000)

        # Fill cache
        small_cache.set("session_1", [{"role": "user", "content": "1"}])
        small_cache.set("session_2", [{"role": "user", "content": "2"}])
        small_cache.set("session_3", [{"role": "user", "content": "3"}])

        # Add 4th (should evict session_1)
        small_cache.set("session_4", [{"role": "user", "content": "4"}])

        assert small_cache.get("session_1") is None  # Evicted
        assert small_cache.get("session_4") is not None

    def test_cache_token_limit_validation(self, cache):
        """Test token limit enforcement."""
        session_id = "test_limit"
        cache.set_session_limits(session_id, max_tokens=50, max_turns=10)

        # Create messages that exceed token limit
        large_messages = [{"role": "user", "content": "a" * 500}]  # ~125 tokens

        with pytest.raises(ValueError, match="Token limit exceeded"):
            cache.set(session_id, large_messages)

    def test_cache_turn_limit_validation(self, cache):
        """Test turn limit enforcement."""
        session_id = "test_turns"
        cache.set_session_limits(session_id, max_tokens=10000, max_turns=2)

        # Create more turns than allowed
        many_messages = [{"role": "user", "content": f"Turn {i}"} for i in range(5)]

        with pytest.raises(ValueError, match="Turn limit exceeded"):
            cache.set(session_id, many_messages)

    def test_cache_session_limits(self, cache):
        """Test per-session limit configuration."""
        session_id = "test_limits"

        cache.set_session_limits(
            session_id, max_tokens=16000, max_turns=20, reserved_response_tokens=2000
        )

        limits = cache._get_session_limits(session_id)
        assert limits["max_tokens"] == 14000  # 16000 - 2000 reserved
        assert limits["max_turns"] == 20
        assert limits["model_context_window"] == 16000

    def test_cache_get_session_stats(self, cache):
        """Test session statistics retrieval."""
        session_id = "test_stats"
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

        cache.set(session_id, messages)
        stats = cache.get_session_stats(session_id)

        assert stats is not None
        assert stats["session_id"] == session_id
        assert stats["turn_count"] == 2
        assert stats["tokens_used"] > 0
        assert "token_percentage" in stats
        assert "will_compress" in stats
        assert stats["estimation_method"] == "heuristic_v1"

    def test_cache_get_global_stats(self, cache):
        """Test global cache statistics."""
        cache.set("session_1", [{"role": "user", "content": "Test 1"}])
        cache.set("session_2", [{"role": "user", "content": "Test 2"}])

        stats = cache.get_stats()

        assert stats["total_sessions"] == 2
        assert stats["total_turns"] == 2
        assert stats["total_tokens"] > 0
        assert stats["encryption"] == "AES-GCM-256"
        assert stats["token_estimation"] == "heuristic_v1"

    def test_cache_clear_expired(self, cache):
        """Test garbage collection of expired entries."""
        short_cache = ConversationCache(ttl_seconds=1, idle_seconds=900)

        short_cache.set("session_1", [{"role": "user", "content": "Test"}])
        short_cache.set("session_2", [{"role": "user", "content": "Test"}])

        time.sleep(1.1)

        cleared = short_cache.clear_expired()
        assert cleared == 2

    def test_cache_key_derivation_unique(self, cache):
        """Test per-session key derivation produces unique keys."""
        key1 = cache._derive_key("session_1")
        key2 = cache._derive_key("session_2")

        assert len(key1) == 32  # AES-256
        assert len(key2) == 32
        assert key1 != key2  # Different sessions = different keys

    def test_cache_encryption_aad(self, cache):
        """Test Additional Authenticated Data prevents tampering."""
        session_id = "test_aad"
        messages = [{"role": "user", "content": "Test"}]

        cache.set(session_id, messages)
        entry = cache._cache[session_id]

        # Try to decrypt with wrong session_id (different AAD)
        with pytest.raises(Exception):  # cryptography.exceptions.InvalidTag
            cache._decrypt("wrong_session", entry.ciphertext, entry.nonce)

    def test_cache_thread_safety_basic(self, cache):
        """Test basic thread safety of cache operations."""
        import threading

        session_id = "test_threading"
        cache.set(session_id, [{"role": "user", "content": "Initial"}])

        def append_message(i):
            cache.append(session_id, "user", f"Message {i}")

        threads = [threading.Thread(target=append_message, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        messages = cache.get(session_id)
        assert len(messages) == 6  # Initial + 5 appends

    def test_cache_get_nonexistent(self, cache):
        """Test get on non-existent session returns None."""
        assert cache.get("nonexistent_session") is None

    def test_cache_append_with_metadata(self, cache):
        """Test append includes metadata."""
        session_id = "test_metadata"
        cache.set(session_id, [{"role": "user", "content": "Test"}])

        metadata = {"request_id": "req_123", "model": "gpt-4"}
        cache.append(session_id, "assistant", "Response", metadata)

        messages = cache.get(session_id)
        assert messages[1]["metadata"] == metadata

    def test_global_cache_singleton(self):
        """Test get_conversation_cache returns singleton."""
        cache1 = get_conversation_cache()
        cache2 = get_conversation_cache()

        assert cache1 is cache2  # Same instance

    def test_cache_stats_compression_warning(self, cache):
        """Test compression warning at 80% threshold."""
        session_id = "test_compress"
        cache.set_session_limits(session_id, max_tokens=100, max_turns=10)

        # Create conversation approaching limit
        messages = [{"role": "user", "content": "a" * 320}]  # ~80 tokens
        cache.set(session_id, messages)

        stats = cache.get_session_stats(session_id)
        assert stats["will_compress"] is True  # > 80%

    def test_cache_handles_empty_messages(self, cache):
        """Test cache handles empty message list."""
        session_id = "test_empty"
        cache.set(session_id, [])

        retrieved = cache.get(session_id)
        assert retrieved == []

    def test_cache_decryption_failure_handling(self, cache):
        """Test cache handles decryption failures gracefully."""
        session_id = "test_corrupt"
        messages = [{"role": "user", "content": "Test"}]

        cache.set(session_id, messages)

        # Corrupt the ciphertext
        entry = cache._cache[session_id]
        entry.ciphertext = b"corrupted_data"

        # Should return None and remove corrupted entry
        retrieved = cache.get(session_id)
        assert retrieved is None
        assert session_id not in cache._cache


class TestCacheIntegration:
    """Integration tests for cache workflow."""

    def test_multi_turn_conversation_flow(self):
        """Test complete multi-turn conversation with cache."""
        cache = ConversationCache(default_max_tokens=1000)
        session_id = "integration_test"

        # Turn 1: Create session
        cache.set(session_id, [{"role": "user", "content": "What is a SOC?"}])
        history = cache.get(session_id)
        assert len(history) == 1

        # Simulate assistant response
        cache.append(session_id, "assistant", "A SOC is a Security Operations Center")
        history = cache.get(session_id)
        assert len(history) == 2

        # Turn 2: Add user follow-up
        cache.append(session_id, "user", "What are its main functions?")
        history = cache.get(session_id)
        assert len(history) == 3

        # Verify conversation structure
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"
        assert "SOC" in history[1]["content"]

    def test_cache_stats_track_growth(self):
        """Test stats track conversation growth."""
        cache = ConversationCache(default_max_tokens=1000)
        session_id = "growth_test"

        # Initial
        cache.set(session_id, [{"role": "user", "content": "Hi"}])
        stats1 = cache.get_session_stats(session_id)

        # Add more
        cache.append(session_id, "assistant", "Hello")
        cache.append(session_id, "user", "How are you?")
        stats2 = cache.get_session_stats(session_id)

        assert stats2["turn_count"] > stats1["turn_count"]
        assert stats2["tokens_used"] > stats1["tokens_used"]
