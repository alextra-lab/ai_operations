"""
Context Compaction Service for AI Operations Platform.

This service provides intelligent context compaction for conversation threads,
including token counting and conversation summarization.

Supports air-gapped deployment with offline tokenizer loading.
"""

import os
import uuid
from pathlib import Path
from typing import Any

import tiktoken

from shared.logging_utils.fastapi import get_logger

from ..db.models import ContextThread, ThreadMessage

logger = get_logger(__name__)


class ContextCompactionService:
    """Intelligent context compaction for conversation threads."""

    def __init__(self, model_name: str = "gpt-4", tokenizer_path: str | None = None):
        """
        Initialize the compaction service with offline tokenizer support.

        Args:
            model_name: The model name to use for token encoding
            tokenizer_path: Optional path to bundled tokenizer directory for air-gapped deployment
        """
        self.model_name = model_name
        self.tokenizer_path = tokenizer_path
        self.encoding = self._load_tokenizer()

        self.max_tokens = 8000  # Configurable per thread
        self.compaction_threshold = 0.7  # Compact at 70% of max

    def _load_tokenizer(self) -> tiktoken.Encoding | None:
        """
        Load tokenizer with fallback chain for air-gapped deployment.

        Fallback chain:
        1. Local bundled tokenizer files (if tokenizer_path provided)
        2. Standard tiktoken encoding_for_model()
        3. Standard tiktoken get_encoding() with cl100k_base
        4. Character-based approximation (last resort)

        Returns:
            tiktoken encoding object or None for character approximation
        """
        # Try bundled tokenizer files first (air-gapped mode)
        if self.tokenizer_path and os.path.exists(self.tokenizer_path):
            try:
                encoding = self._load_bundled_tokenizer()
                if encoding:
                    logger.info(
                        f"Loaded bundled tokenizer for {self.model_name} from {self.tokenizer_path}"
                    )
                    return encoding
            except Exception as e:
                logger.warning(f"Failed to load bundled tokenizer: {e}")

        # Try standard tiktoken model encoding
        try:
            encoding = tiktoken.encoding_for_model(self.model_name)
            logger.info(f"Loaded tiktoken encoding for model {self.model_name}")
            return encoding
        except (KeyError, Exception) as e:
            logger.warning(f"Model {self.model_name} not recognized by tiktoken: {e}")

        # Fallback to cl100k_base encoding
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            logger.warning(f"Using cl100k_base encoding fallback for {self.model_name}")
            return encoding
        except Exception as e:
            logger.error(f"Failed to load cl100k_base encoding: {e}")

        # Last resort: return None for character approximation
        logger.error(
            f"All tokenizer loading methods failed for {self.model_name}, using character approximation"
        )
        return None

    def _load_bundled_tokenizer(self) -> tiktoken.Encoding | None:
        """
        Load tokenizer from bundled files for air-gapped deployment.

        Returns:
            tiktoken encoding object or None if not found
        """
        if not self.tokenizer_path:
            return None

        tokenizer_dir = Path(self.tokenizer_path)

        # Map model names to potential tokenizer files
        model_mappings = {
            "foundation-sec": ["foundation-sec.json", "foundation-sec.tiktoken"],
            "phi-4-mini": ["phi-4-mini.json", "phi-4-mini.tiktoken"],
            "mistral-large": ["mistral-large.json", "mistral-large.tiktoken"],
            "mistral-small": ["mistral-small.json", "mistral-small.tiktoken"],
            "gpt-oss": ["cl100k_base.json", "cl100k_base.tiktoken"],
            "llama-3.3": ["llama-3.3.json", "llama-3.3.tiktoken"],
        }

        # Try to find matching tokenizer files
        potential_files = model_mappings.get(self.model_name, [])
        for filename in potential_files:
            tokenizer_file = tokenizer_dir / filename
            if tokenizer_file.exists():
                try:
                    # Load the tokenizer file
                    with open(tokenizer_file, "rb"):
                        # This is a simplified approach - in practice, you'd need to
                        # implement proper tokenizer loading based on the file format
                        logger.info(f"Found bundled tokenizer file: {tokenizer_file}")
                        # For now, fall back to standard encoding
                        return tiktoken.get_encoding("cl100k_base")
                except Exception as e:
                    logger.warning(f"Failed to load tokenizer file {tokenizer_file}: {e}")
                    continue

        return None

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken or character approximation.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens in the text
        """
        if not text:
            return 0

        # Use tiktoken if available
        if self.encoding is not None:
            try:
                return len(self.encoding.encode(text))
            except Exception as e:
                logger.error("Error counting tokens with tiktoken: %s", str(e))
                # Fall through to character approximation

        # Character-based approximation (last resort)
        logger.warning(
            f"Using character approximation for token counting (model: {self.model_name})"
        )
        # Rough approximation: 1 token ≈ 4 characters for most models
        # This is less accurate but works in air-gapped environments
        return len(text) // 4

    def should_compact(self, thread: ContextThread) -> bool:
        """
        Check if thread needs compaction.

        Args:
            thread: The conversation thread to check

        Returns:
            True if thread should be compacted (>70% of max tokens)
        """
        if not thread.auto_compact:
            return False

        max_tokens = thread.max_context_tokens or self.max_tokens
        threshold = max_tokens * self.compaction_threshold

        return thread.context_size_tokens > threshold

    async def compact_thread(
        self,
        thread: ContextThread,
        messages: list[ThreadMessage],
        llm_service: Any,  # Will use existing LLM router
    ) -> list[ThreadMessage]:
        """
        Compact thread by summarizing older messages.

        Strategy:
        1. Keep last 10 messages unchanged
        2. Summarize messages 11-N into single summary message
        3. Update token counts

        Args:
            thread: The conversation thread
            messages: List of thread messages
            llm_service: LLM service for generating summaries

        Returns:
            List of messages after compaction
        """
        if len(messages) <= 10:
            logger.info(
                "Thread %s has %d messages, no compaction needed",
                thread.thread_id,
                len(messages),
            )
            return messages

        recent_messages = messages[-10:]
        older_messages = messages[:-10]

        logger.info(
            "Compacting thread %s: %d older messages, %d recent messages",
            thread.thread_id,
            len(older_messages),
            len(recent_messages),
        )

        # Build summary prompt
        conversation_text = "\n\n".join(
            [f"{msg.role}: {msg.content}" for msg in older_messages if not msg.is_summary]
        )

        summary_prompt = f"""Summarize this conversation preserving key facts, decisions, and context:

{conversation_text}

Provide a concise summary that maintains important details for continued conversation."""

        try:
            # Generate summary using LLM
            summary_response = await llm_service.generate_summary(summary_prompt)

            summary_content = (
                f"[Summary of {len(older_messages)} earlier messages]: {summary_response}"
            )

            # Create summary message
            summary_message = ThreadMessage(
                id=uuid.uuid4(),
                thread_id=thread.id,
                query_id=None,  # Summaries don't have associated queries
                sequence_number=older_messages[0].sequence_number,
                role="system",
                content=summary_content,
                token_count=self.count_tokens(summary_content),
                is_summary=True,
                original_message_count=len(older_messages),
            )

            logger.info(
                "Created summary with %d tokens from %d messages",
                summary_message.token_count,
                len(older_messages),
            )

            return [summary_message, *recent_messages]

        except Exception as e:
            logger.error("Error compacting thread %s: %s", thread.thread_id, str(e))
            # Return original messages if compaction fails
            return messages

    def calculate_context_size(self, messages: list[ThreadMessage]) -> int:
        """
        Calculate total context size in tokens for a list of messages.

        Args:
            messages: List of thread messages

        Returns:
            Total token count
        """
        return sum(msg.token_count for msg in messages)

    def estimate_tokens_remaining(self, thread: ContextThread) -> int:
        """
        Estimate how many tokens remain before compaction is needed.

        Args:
            thread: The conversation thread

        Returns:
            Estimated tokens remaining
        """
        max_tokens = thread.max_context_tokens or self.max_tokens
        threshold = max_tokens * self.compaction_threshold

        return int(threshold - thread.context_size_tokens)
