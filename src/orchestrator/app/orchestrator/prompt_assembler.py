"""
Prompt Assembler Component for AI Operations Platform.

This module provides functionality to select appropriate templates and assemble
prompts for the LLM based on the intent type and context from the retrieval engine.

The Prompt Assembler is a key component in the orchestrator workflow:
Intent Parser → Retrieval Engine → Prompt Assembler → Tool & Model Router → LLM Router → Response Formatter
"""

import os
from typing import ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging, get_logger

from ..llm.template_loader import TemplateLoader
from ..schemas.intent import RequestType
from ..schemas.prompt import PromptRequest, PromptResponse, PromptTemplate

logger = configure_logging(service_name="prompt_assembler", log_level="INFO", log_format="json")


class PromptAssembler:
    """
    Assembles prompts based on intent and context.

    This class is responsible for:
    1. Selecting the appropriate template based on the intent type
    2. Filling the template with variables from the request
    3. Recommending the appropriate model for the prompt

    It uses the TemplateLoader to fetch templates from either the database
    or file system, with proper fallback mechanisms.
    """

    # Mapping from intent types to template IDs
    INTENT_TO_TEMPLATE_MAP: ClassVar[dict[RequestType, str]] = {
        RequestType.QUERY: "general_query",
        RequestType.RULE_GENERATION: "rule_generation",
        RequestType.SUMMARIZATION: "content_summarization",
        RequestType.ENRICHMENT: "security_enrichment",
    }

    # Mapping from intent types to recommended models
    # More complex intents (rule generation, enrichment) use larger models
    INTENT_TO_MODEL_MAP: ClassVar[dict[RequestType, str]] = {
        RequestType.QUERY: "mistral-small",
        RequestType.RULE_GENERATION: "mistral-large",
        RequestType.SUMMARIZATION: "mistral-small",
        RequestType.ENRICHMENT: "mistral-large",
    }

    def __init__(self, db: AsyncSession):
        """
        Initialize the prompt assembler.

        Args:
            db: Database session for template loading
        """
        if os.environ.get("PYTEST_CURRENT_TEST"):
            get_logger(__name__).info("PromptAssembler.__init__ START")
        self.template_loader = TemplateLoader(db)
        logger.info("PromptAssembler initialized with TemplateLoader")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            get_logger(__name__).info("PromptAssembler.__init__ END")

    async def select_template(self, intent_type: RequestType) -> PromptTemplate | None:
        """
        Select the appropriate template based on the intent type.

        Args:
            intent_type: The type of request (query, rule generation, etc.)

        Returns:
            The selected template if found, None otherwise
        """
        template_id = self.INTENT_TO_TEMPLATE_MAP.get(intent_type)
        if not template_id:
            logger.error(f"No template mapping found for intent type: {intent_type}")
            return None

        logger.info(f"Selecting template '{template_id}' for intent type: {intent_type}")
        template = await self.template_loader.get_template(template_id)

        if not template:
            logger.error(f"Template '{template_id}' not found for intent type: {intent_type}")
            return None

        logger.debug(f"Selected template: {template.template_id}")
        return template

    def assemble_prompt(self, template: PromptTemplate, variables: dict) -> str:
        """
        Fill the template with the provided variables.

        Args:
            template: The template to fill
            variables: Dictionary of variable names and values

        Returns:
            The assembled prompt string
        """
        logger.info(f"Assembling prompt using template: {template.template_id}")

        # Validate that all required variables are provided
        missing_vars = [var for var in template.variables if var not in variables]
        if missing_vars:
            logger.error(
                f"Missing required variables for template {template.template_id}: {missing_vars}"
            )
            # Provide empty strings for missing variables to avoid template errors
            for var in missing_vars:
                variables[var] = ""

        # Log variables being used (excluding potentially sensitive content)
        safe_vars = dict.fromkeys(variables, "...")
        logger.debug(f"Using variables: {safe_vars}")

        try:
            # Use string.format_map to handle missing keys gracefully
            prompt = template.template.format_map(variables)
            logger.info(f"Successfully assembled prompt with template {template.template_id}")
            return prompt
        except KeyError as e:
            logger.error(f"Error during template formatting: {e!s}")
            return f"ERROR: Failed to format template {template.template_id}. Missing key: {e!s}"
        except ValueError as e:
            logger.error(f"Error during template formatting: {e!s}")
            return f"ERROR: Invalid format in template {template.template_id}: {e!s}"

    async def get_prompt(self, request: PromptRequest) -> PromptResponse:
        """
        Process a prompt request and return an assembled prompt.

        Args:
            request: The prompt request containing intent and context

        Returns:
            A prompt response with the assembled prompt and metadata
        """
        logger.info(f"Processing prompt request for intent type: {request.intent.detected_type}")

        # Select the appropriate template
        template = await self.select_template(request.intent.detected_type)
        if not template:
            error_msg = f"No template found for intent type: {request.intent.detected_type}"
            logger.error(error_msg)
            return PromptResponse(
                prompt=f"ERROR: {error_msg}",
                template_id="error",
                model=self.INTENT_TO_MODEL_MAP.get(request.intent.detected_type, "mistral-small"),
                metadata={"error": error_msg},
            )

        # Prepare variables for the template
        variables = {
            "query": request.intent.query,
            "context": self._format_context_for_prompt(request.context),
        }

        # Assemble the prompt
        prompt = self.assemble_prompt(template, variables)

        # Determine the recommended model
        model = self.INTENT_TO_MODEL_MAP.get(request.intent.detected_type, "mistral-small")

        # Build metadata
        metadata = {
            "intent_type": request.intent.detected_type.value,
            "confidence": request.intent.confidence,
            "template_used": template.template_id,
            "context_size": len(str(request.context)) if request.context else 0,
        }

        logger.info(f"Successfully created prompt response using template {template.template_id}")
        return PromptResponse(
            prompt=prompt,
            template_id=template.template_id,
            model=model,
            metadata=metadata,
        )

    def _format_context_for_prompt(self, context: dict | None) -> str:
        """
        Format the context dictionary into a readable string with proper source citations.

        Args:
            context: The context dictionary from the retrieval service

        Returns:
            A formatted string ready for use in prompts
        """
        if not context or not context.get("sources"):
            return "No relevant context found in the knowledge base."

        sources = context.get("sources", [])
        if not sources:
            return "No relevant context found in the knowledge base."

        formatted_context = "Based on the following sources:\n\n"

        for i, source in enumerate(sources, 1):
            title = source.get("title", "Unknown Document")
            doc_id = source.get("document_id", "unknown")
            content = source.get("content", "")
            relevance = source.get("relevance_score", 0.0)

            formatted_context += f"[{i}] {title} ({doc_id})\n"
            formatted_context += f"Relevance: {relevance:.3f}\n"
            formatted_context += f"Content: {content}\n\n"

        formatted_context += "IMPORTANT: When citing information, use the format [1], [2], etc. to reference the numbered sources above.\n"

        logger.info(f"Formatted context with {len(sources)} sources for prompt")
        return formatted_context
