"""
Policy Engine for orchestrator policy checks and guardrails.

Extracted from OrchestratorController for better separation of concerns.
Part of Layer 3 orchestrator refactoring (P4-F10).
ADR-034: Use Case Validation & Test Harness
"""

from typing import Any

from shared.logging_utils.fastapi import get_logger

from ..schemas.use_case_config import UseCaseConfig

logger = get_logger(__name__)


class PolicyEngine:
    """
    Policy checks and guardrails for use case execution.

    Handles:
    - Streaming policy resolution (explicit, template default, intent-based)
    - Tool allowlist validation
    - Policy-based configuration overrides
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize policy engine.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

    def resolve_streaming_policy(
        self,
        explicit_stream: bool | None,
        use_case_config: UseCaseConfig,
        intent_type: str | None = None,
    ) -> bool:
        """
        Resolve streaming preference with three-tier fallback.

        Priority order:
        1. Explicit user override (`stream` parameter) - highest priority
        2. Template default (config.policy.streaming_default) - medium priority
        3. Intent-based default (streaming enabled for known streaming intents) - lowest priority

        Args:
            explicit_stream: Explicit streaming preference from request
            use_case_config: Use case configuration containing policy settings
            intent_type: Detected intent type (e.g., "chat", "retrieval")

        Returns:
            Final streaming decision (True/False)
        """
        # Priority 1: Explicit user override
        if explicit_stream is not None:
            logger.debug(f"Streaming: explicit override = {explicit_stream}")
            return explicit_stream

        # Priority 2: Template default from use case policy
        if (
            hasattr(use_case_config, "policy")
            and hasattr(use_case_config.policy, "streaming_default")
            and use_case_config.policy.model_fields_set
            and "streaming_default" in use_case_config.policy.model_fields_set
        ):
            template_default = use_case_config.policy.streaming_default
            logger.debug(f"Streaming: template default = {template_default}")
            return template_default

        # Priority 3: Intent-based default
        streaming_intents = {"chat", "conversational", "interactive"}
        intent_based_default = intent_type in streaming_intents if intent_type else False

        logger.debug(
            f"Streaming: intent-based default = {intent_based_default} (intent={intent_type})"
        )
        return intent_based_default

    def validate_tool_allowlist(self, use_case_config: UseCaseConfig) -> None:
        """
        Validate tool configuration against allowlist.

        Raises ValueError if tools are configured but not allowed.

        Args:
            use_case_config: Use case configuration to validate

        Raises:
            ValueError: If tools configured but max_tool_steps=0
        """
        # Check if tools are configured
        has_tools = (
            hasattr(use_case_config, "tools_allowlist")
            and use_case_config.tools_allowlist
            and len(use_case_config.tools_allowlist) > 0
        )

        # Check if tools are allowed
        allows_tools = (
            hasattr(use_case_config, "generation_params")
            and use_case_config.generation_params
            and getattr(use_case_config.generation_params, "max_tool_steps", 0) > 0
        )

        if has_tools and not allows_tools:
            raise ValueError(
                "Use case has tool_config.available_tools configured, "
                "but generation_params.max_tool_steps is 0. "
                "Set max_tool_steps > 0 to enable tool use."
            )

        logger.debug(
            f"Tool allowlist validation: has_tools={has_tools}, allows_tools={allows_tools}"
        )

    def check_policy_violations(
        self,
        use_case_config: UseCaseConfig,
        context: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """
        Check for policy violations in use case configuration.

        Returns a report of any policy violations found.

        Args:
            use_case_config: Use case configuration to check
            context: Optional execution context

        Returns:
            Dictionary with violation details:
            {
                "has_violations": bool,
                "violations": List[Dict[str, str]],
                "warnings": List[Dict[str, str]]
            }
        """
        violations = []
        warnings = []

        # Check for tool configuration violations
        try:
            self.validate_tool_allowlist(use_case_config)
        except ValueError as e:
            violations.append(
                {
                    "type": "tool_configuration",
                    "severity": "error",
                    "message": str(e),
                }
            )

        # Check for missing required policy fields
        if hasattr(use_case_config, "generation_params"):
            gen_params = use_case_config.generation_params

            # Check if max_tokens is reasonable
            if hasattr(gen_params, "max_tokens"):
                max_tokens = gen_params.max_tokens
                if max_tokens and max_tokens > 16000:
                    warnings.append(
                        {
                            "type": "policy_configuration",
                            "severity": "warning",
                            "message": f"max_output_tokens ({max_tokens}) is very high. Consider lowering for cost efficiency.",
                        }
                    )

        # Check generation parameters
        if hasattr(use_case_config, "generation_params"):
            gen_params = use_case_config.generation_params

            # Check for high-entropy configuration
            if hasattr(gen_params, "temperature") and hasattr(gen_params, "top_p"):
                temp = gen_params.temperature
                top_p = gen_params.top_p

                if temp and top_p and temp > 0.9 and top_p > 0.97:
                    warnings.append(
                        {
                            "type": "generation_params",
                            "severity": "warning",
                            "message": f"High-entropy configuration detected (temp={temp}, top_p={top_p}). This may produce unstable results.",
                        }
                    )

        return {
            "has_violations": len(violations) > 0,
            "violations": violations,
            "warnings": warnings,
        }

    def apply_policy_overrides(
        self,
        use_case_config: UseCaseConfig,
        policy_overrides: dict[str, Any] | None = None,
    ) -> UseCaseConfig:
        """
        Apply policy-based configuration overrides.

        Allows runtime policy enforcement to override use case configuration.

        Args:
            use_case_config: Original use case configuration
            policy_overrides: Dictionary of policy-based overrides

        Returns:
            Modified use case configuration (new instance)
        """
        if not policy_overrides:
            return use_case_config

        # Create a copy to avoid mutating original
        config_dict = use_case_config.model_dump()

        # Apply overrides
        for key, value in policy_overrides.items():
            if "." in key:
                # Handle nested keys (e.g., "generation_params.temperature")
                parts = key.split(".")
                current = config_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
                logger.info(f"Applied policy override: {key} = {value}")
            else:
                # Handle top-level keys
                config_dict[key] = value
                logger.info(f"Applied policy override: {key} = {value}")

        # Reconstruct use case config from modified dict
        return UseCaseConfig.model_validate(config_dict)

    def get_policy_summary(self, use_case_config: UseCaseConfig) -> dict[str, Any]:
        """
        Get a summary of policy settings for a use case.

        Args:
            use_case_config: Use case configuration

        Returns:
            Dictionary with policy summary
        """
        summary = {
            "has_policy": hasattr(use_case_config, "policy"),
            "streaming_default": None,
            "max_output_tokens": None,
            "timeout_seconds": None,
            "allows_tools": False,
            "max_tool_steps": 0,
        }

        if hasattr(use_case_config, "policy") and use_case_config.policy:
            policy = use_case_config.policy
            summary["streaming_default"] = getattr(policy, "streaming_default", None)
            summary["max_output_tokens"] = getattr(policy, "max_output_tokens", None)
            summary["timeout_seconds"] = getattr(policy, "timeout_seconds", None)

        if hasattr(use_case_config, "generation_params") and use_case_config.generation_params:
            gen_params = use_case_config.generation_params
            max_tool_steps = getattr(gen_params, "max_tool_steps", 0)
            summary["max_tool_steps"] = max_tool_steps if max_tool_steps is not None else 0
            summary["allows_tools"] = (max_tool_steps or 0) > 0

        return summary
