"""Native port of llm-guard's Regex input scanner (MIT).

Verbatim from llm_guard.input_scanners.regex (llm-guard==0.3.16), with only the
dependency swaps needed to drop the llm_guard import:
  * llm_guard.util.get_logger      -> stdlib logging
  * the structural `Scanner` Protocol base is dropped (not needed at runtime)
Match type, redaction, and the signed score convention are unchanged.
"""

from __future__ import annotations

import logging
import re
from enum import Enum

from presidio_anonymizer.core.text_replace_builder import TextReplaceBuilder

LOGGER = logging.getLogger(__name__)

# The two production patterns, verbatim from app/guard.py (single source of truth;
# guard.py imports this for the llm-guard branch too).
CREDENTIAL_PATTERNS: list[str] = [
    r"(password|api_key|secret|token)[\s]*[=:][\s]*[\w\d]{8,}",
    r"ssh-rsa[\s]+[A-Za-z0-9+/]+={0,2}",
]


class MatchType(Enum):
    SEARCH = "search"
    FULL_MATCH = "fullmatch"
    ALL = "all"

    def match(self, pattern: re.Pattern[str], text: str) -> list[re.Match[str]]:
        if self.value == "all":
            return list(pattern.finditer(text))[::-1]  # reverse to keep indices valid
        m = None
        if self.value == "search":
            m = pattern.search(text)
        if self.value == "fullmatch":
            m = pattern.fullmatch(text)
        if m is None:
            return []
        return [m]


class RegexScanner:
    """Detects configured patterns; redacts matches to ``[REDACTED]``."""

    def __init__(
        self,
        patterns: list[str] | None = None,
        *,
        is_blocked: bool = True,
        match_type: MatchType = MatchType.SEARCH,
        redact: bool = True,
    ) -> None:
        self._patterns = [re.compile(p) for p in (patterns or CREDENTIAL_PATTERNS)]
        self._match_type = match_type
        self._is_blocked = is_blocked
        self._redact = redact

    def scan(self, prompt: str) -> tuple[str, bool, float]:
        builder = TextReplaceBuilder(original_text=prompt)
        for pattern in self._patterns:
            matches = self._match_type.match(pattern, prompt)
            if not matches:
                continue
            if self._is_blocked:
                if self._redact:
                    for match in matches:
                        builder.replace_text_get_insertion_index(
                            "[REDACTED]", match.start(), match.end()
                        )
                return builder.output_text, False, 1.0
            return builder.output_text, True, -1.0
        if self._is_blocked:
            return builder.output_text, True, -1.0
        return builder.output_text, False, 1.0
