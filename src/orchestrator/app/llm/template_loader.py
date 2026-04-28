"""
Template Loader Service for AI Operations Platform.

This module provides functionality to load prompt templates using a hybrid approach:
1. First checks the database for user-customized templates
2. Falls back to file-based templates if no database override is found

The service includes caching to minimize database queries and file operations.
"""

import json
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import PromptTemplate as DBPromptTemplate
from ..schemas.prompt import PromptTemplate

# Path to file-based templates relative to the application root
DEFAULT_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "templates")

# Use a descriptive service name for clarity in logs
logger = configure_logging(service_name="template_loader")


class TemplateLoader:
    """
    Service for loading prompt templates using a hybrid approach.

    Supports both database-stored templates (for user customization) and
    file-based templates (for defaults/fallbacks).

    Implements caching to minimize database queries and file system operations.
    """

    def __init__(self, db: AsyncSession, templates_dir: str = DEFAULT_TEMPLATES_DIR):
        """
        Initialize the template loader.

        Args:
            db: Async database session for accessing templates stored in the database
            templates_dir: Directory containing file-based templates (defaults if not in DB)
        """
        self.db = db
        self.templates_dir = templates_dir
        self._cache: dict[str, PromptTemplate] = {}

    async def get_template(self, template_id: str) -> PromptTemplate | None:
        """
        Get a template by its ID using the hybrid approach.

        First checks the cache, then the database for a customized version,
        and finally falls back to file-based templates.

        Args:
            template_id: The unique identifier for the template

        Returns:
            The template if found, None otherwise
        """
        # Check cache first
        if template_id in self._cache:
            logger.debug(f"Template cache hit for {template_id}")
            return self._cache[template_id]

        # Check database for customized template
        db_template = await self._get_db_template(template_id)
        if db_template:
            # Convert to schema model and cache
            # Ensure we convert SQLAlchemy Column values to Python types
            template = PromptTemplate(
                template_id=str(db_template.template_id),
                template=str(db_template.template_content),
                variables=(
                    list(db_template.variables) if isinstance(db_template.variables, list) else []
                ),
            )
            self._cache[template_id] = template
            logger.debug(f"Loaded template {template_id} from database")
            return template

        # Fall back to file-based template
        file_template = self._get_file_template(template_id)
        if file_template:
            self._cache[template_id] = file_template
            logger.debug(f"Loaded template {template_id} from file")
            return file_template

        # Template not found
        logger.warning(f"Template {template_id} not found in database or files")
        return None

    async def list_templates(self) -> list[PromptTemplate]:
        """
        List all available templates, combining database and file-based templates.

        Database templates override file templates with the same ID.

        Returns:
            List of available templates
        """
        templates = {}

        # Get file-based templates first
        for template in self._list_file_templates():
            templates[template.template_id] = template

        # Override with database templates
        for template in await self._list_db_templates():
            templates[template.template_id] = template

        return list(templates.values())

    def reset_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()
        logger.debug("Template cache cleared")

    async def _get_db_template(self, template_id: str) -> DBPromptTemplate | None:
        """Get a template from the database."""
        stmt = (
            select(DBPromptTemplate)
            .where(DBPromptTemplate.template_id == template_id)
            .where(DBPromptTemplate.is_active_version)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _list_db_templates(self) -> list[PromptTemplate]:
        """List all templates from the database."""
        stmt = select(DBPromptTemplate).where(DBPromptTemplate.is_active_version)
        result = await self.db.execute(stmt)
        db_templates = result.scalars().all()

        templates_list: list[PromptTemplate] = []
        for t in db_templates:
            # Ensure proper type conversion for all fields
            template_id = str(t.template_id)
            template_text = str(t.template_content)

            # Handle variables specially since it's a JSON column (runtime may differ)
            if isinstance(t.variables, list):
                variables = list(t.variables)
            else:
                # If for some reason variables is not iterable, use empty list
                variables = []  # type: ignore[unreachable]
                logger.warning(
                    f"Template {template_id} has invalid variables format, using empty list"
                )

            try:
                templates_list.append(
                    PromptTemplate(
                        template_id=template_id,
                        template=template_text,
                        variables=variables,
                    )
                )
            except Exception as e:
                logger.error(f"Error converting template {template_id}: {e!s}")

        return templates_list

    def _get_file_template(self, template_id: str) -> PromptTemplate | None:
        """Get a template from the file system."""
        try:
            # Check common template filenames
            potential_filenames = [
                f"{template_id}.json",
                f"{template_id}_template.json",
            ]

            for filename in potential_filenames:
                file_path = os.path.join(self.templates_dir, filename)
                if os.path.exists(file_path):
                    with open(file_path) as file:
                        data = json.load(file)
                        return PromptTemplate(**data)

            # Also try searching all JSON files for matching template_id
            for filename in os.listdir(self.templates_dir):
                if not filename.endswith(".json"):
                    continue

                file_path = os.path.join(self.templates_dir, filename)
                with open(file_path) as file:
                    data = json.load(file)
                    if data.get("template_id") == template_id:
                        return PromptTemplate(**data)

            return None
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Error loading file template {template_id}: {e!s}")
            return None

    def _list_file_templates(self) -> list[PromptTemplate]:
        """List all templates from the file system."""
        templates = []

        try:
            for filename in os.listdir(self.templates_dir):
                if not filename.endswith(".json"):
                    continue

                file_path = os.path.join(self.templates_dir, filename)
                try:
                    with open(file_path) as file:
                        data = json.load(file)
                        templates.append(PromptTemplate(**data))
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.error(f"Error loading template from {filename}: {e!s}")
        except FileNotFoundError:
            logger.warning(f"Templates directory not found: {self.templates_dir}")

        return templates
