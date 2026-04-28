"""
Integration tests for user prompt template rendering through the execution pipeline.

Phase 5 (D4): Validates that config load + template render produces the correct
query text when a use case has user_prompt_template and input_fields.

ADR-062: User Prompt Templates Parameter Injection.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.models import UseCase
from src.orchestrator.app.orchestrator.template_renderer import render_user_prompt_template
from src.orchestrator.app.schemas.use_case_config import (
    UseCaseConfig,
)
from src.orchestrator.app.services.use_case_config_loader import UseCaseConfigLoader


@pytest.mark.asyncio
async def test_template_rendering_through_config_load(async_db_session: AsyncSession) -> None:
    """
    Load a use case config with user_prompt_template from DB and render with inputs.

    Exercises: DB -> UseCaseConfigLoader.load_config -> UseCaseConfig.from_dict
    -> render_user_prompt_template. Validates the full pipeline without calling
    the execute HTTP endpoint.
    """
    base = UseCaseConfig()
    base_dict = base.model_dump()
    base_dict["user_prompt_template"] = {
        "template": "Analyze incident {{incident_id}} with severity {{severity}}.",
        "fallback_mode": "concatenate",
    }
    config_dict = base_dict

    use_case = UseCase(
        use_case_id="test_template_pipeline_uc",
        name="Test Template Pipeline",
        description="Use case for template rendering integration test",
        category="test",
        intent_type="QUERY",
        is_active=True,
        lifecycle_state="published",
        version=1,
        config_json=config_dict,
        metadata_json={},
    )
    async_db_session.add(use_case)
    await async_db_session.commit()
    await async_db_session.refresh(use_case)

    loader = UseCaseConfigLoader(async_db_session)
    loaded = await loader.load_config(str(use_case.id))
    assert loaded is not None
    assert loaded.user_prompt_template is not None
    assert "{{incident_id}}" in loaded.user_prompt_template.template
    assert "{{severity}}" in loaded.user_prompt_template.template

    inputs = {"incident_id": "INC-001", "severity": "high"}
    rendered = render_user_prompt_template(
        template=loaded.user_prompt_template.template,
        inputs=inputs,
        fallback_mode=loaded.user_prompt_template.fallback_mode,
    )
    assert rendered == "Analyze incident INC-001 with severity high."


@pytest.mark.asyncio
async def test_legacy_concatenation_path_when_no_template(async_db_session: AsyncSession) -> None:
    """When user_prompt_template is None, config still loads; render is not used in execute."""
    base = UseCaseConfig()
    config_dict = base.model_dump()

    use_case = UseCase(
        use_case_id="test_legacy_uc",
        name="Test Legacy Concatenation",
        description="Use case with no template",
        category="test",
        intent_type="QUERY",
        is_active=True,
        lifecycle_state="published",
        version=1,
        config_json=config_dict,
        metadata_json={},
    )
    async_db_session.add(use_case)
    await async_db_session.commit()
    await async_db_session.refresh(use_case)

    loader = UseCaseConfigLoader(async_db_session)
    loaded = await loader.load_config(str(use_case.id))
    assert loaded is not None
    assert loaded.user_prompt_template is None
