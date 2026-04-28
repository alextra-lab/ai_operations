"""
Export service for client-side conversation data (ADR-031).

Generates exports from client-provided conversation data without
storing content server-side.
"""

import hashlib
import json
from datetime import datetime
from typing import Any

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="export_service")


class ExportService:
    """
    Service for generating exports from client-provided conversation data.

    This service implements ADR-031 (Client-Owned Exports) by generating
    exports on-demand from client data without server-side storage.
    """

    def generate_json_export(
        self,
        conversation_id: str,
        export_timestamp: datetime,
        use_case: dict[str, Any],
        messages: list[dict[str, Any]],
        session_metadata: dict[str, Any],
    ) -> str:
        """
        Generate JSON export from conversation data.

        Args:
            conversation_id: Client-side conversation identifier
            export_timestamp: When export was requested
            use_case: Use case context
            messages: Conversation messages
            session_metadata: Session metadata

        Returns:
            JSON string of exported conversation
        """
        export_data = {
            "conversation_id": conversation_id,
            "export_timestamp": export_timestamp.isoformat(),
            "export_version": "1.0",
            "use_case": use_case,
            "messages": messages,
            "session_metadata": session_metadata,
        }

        logger.info(
            "Generated JSON export",
            extra={
                "conversation_id": conversation_id,
                "message_count": len(messages),
                "use_case_id": use_case.get("id"),
            },
        )

        return json.dumps(export_data, indent=2)

    def generate_markdown_export(
        self,
        conversation_id: str,
        export_timestamp: datetime,
        use_case: dict[str, Any],
        messages: list[dict[str, Any]],
        session_metadata: dict[str, Any],
    ) -> str:
        """
        Generate Markdown export from conversation data.

        Args:
            conversation_id: Client-side conversation identifier
            export_timestamp: When export was requested
            use_case: Use case context
            messages: Conversation messages
            session_metadata: Session_metadata

        Returns:
            Markdown string of exported conversation
        """
        lines = []

        # Header
        lines.append(f"# Conversation Export: {use_case.get('name', 'Unknown')}")
        lines.append("")
        lines.append(f"**Conversation ID:** `{conversation_id}`")
        lines.append(f"**Exported:** {export_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"**Use Case:** {use_case.get('name', 'Unknown')}")
        lines.append(f"**Use Case ID:** `{use_case.get('id', 'Unknown')}`")

        if use_case.get("version"):
            lines.append(f"**Version:** {use_case['version']}")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Session metadata
        if session_metadata:
            lines.append("## Session Metadata")
            lines.append("")
            for key, value in session_metadata.items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Messages
        lines.append("## Conversation")
        lines.append("")

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            # Role header
            role_emoji = {
                "user": "👤",
                "assistant": "🤖",
                "system": "⚙️",
            }.get(role, "💬")

            lines.append(f"### {role_emoji} {role.title()} (Message {i})")
            lines.append("")

            if timestamp:
                lines.append(f"*{timestamp}*")
                lines.append("")

            # Content
            lines.append(content)
            lines.append("")

            # Metadata
            if msg.get("metadata"):
                meta = msg["metadata"]
                details = []
                if meta.get("model"):
                    details.append(f"Model: `{meta['model']}`")
                if meta.get("tokens"):
                    details.append(f"Tokens: {meta['tokens']}")
                if meta.get("latency_ms"):
                    details.append(f"Latency: {meta['latency_ms']}ms")

                if details:
                    lines.append("*" + " | ".join(details) + "*")
                    lines.append("")

            lines.append("---")
            lines.append("")

        # Footer
        lines.append("## Export Information")
        lines.append("")
        lines.append("This conversation was exported from AI Operations Platform.")
        lines.append(
            f"Export format: Markdown | Export version: 1.0 | Total messages: {len(messages)}"
        )
        lines.append("")

        markdown_content = "\n".join(lines)

        logger.info(
            "Generated Markdown export",
            extra={
                "conversation_id": conversation_id,
                "message_count": len(messages),
                "use_case_id": use_case.get("id"),
            },
        )

        return markdown_content

    def generate_export_id(self, conversation_id: str, timestamp: datetime) -> str:
        """
        Generate unique export ID.

        Args:
            conversation_id: Conversation identifier
            timestamp: Export timestamp

        Returns:
            Unique export ID
        """
        data = f"{conversation_id}:{timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
