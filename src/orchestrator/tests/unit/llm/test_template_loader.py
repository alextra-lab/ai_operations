import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.llm.template_loader import TemplateLoader
from app.schemas.prompt import PromptTemplate


def make_db_template(template_id="t1", template=None, variables=None, active=True):
    db_template = MagicMock()
    if variables is None:
        variables = ["var1"]
    if template is None:
        # Ensure template contains all variable placeholders
        template = " ".join([f"{{{v}}}" for v in variables])
    db_template.template_id = template_id
    db_template.template_content = template  # Use template_content for async version
    db_template.template = template  # Keep for backward compatibility
    db_template.variables = variables
    db_template.is_active_version = active
    db_template.active = active
    return db_template


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def tmp_templates_dir(tmp_path):
    # Create a temp directory with a sample template file
    template_data = {
        "template_id": "file1",
        "template": "{v1} {v2}",
        "variables": ["v1", "v2"],
    }
    file = tmp_path / "file1.json"
    file.write_text(json.dumps(template_data))
    return str(tmp_path)


@pytest.mark.asyncio
async def test_get_template_cache(db):
    loader = TemplateLoader(db)
    t = PromptTemplate(template_id="t1", template="{v}", variables=["v"])
    loader._cache["t1"] = t
    result = await loader.get_template("t1")
    assert result is t


@pytest.mark.asyncio
async def test_get_template_db(db):
    loader = TemplateLoader(db)
    # Create a template that matches the validation requirements
    db_template = make_db_template(template_id="t1", template="{var1}", variables=["var1"])
    loader._get_db_template = AsyncMock(return_value=db_template)
    loader._get_file_template = MagicMock(return_value=None)
    result = await loader.get_template("t1")
    assert isinstance(result, PromptTemplate)
    assert result.template_id == "t1"
    assert loader._cache["t1"] == result


@pytest.mark.asyncio
async def test_get_template_file(db, tmp_templates_dir):
    loader = TemplateLoader(db, templates_dir=tmp_templates_dir)
    loader._get_db_template = AsyncMock(return_value=None)
    result = await loader.get_template("file1")
    assert isinstance(result, PromptTemplate)
    assert result.template_id == "file1"
    assert loader._cache["file1"] == result


@pytest.mark.asyncio
async def test_get_template_not_found(db):
    loader = TemplateLoader(db)
    loader._get_db_template = AsyncMock(return_value=None)
    loader._get_file_template = MagicMock(return_value=None)
    result = await loader.get_template("notfound")
    assert result is None


@pytest.mark.asyncio
async def test_list_templates_merges_db_and_file(db, tmp_templates_dir):
    loader = TemplateLoader(db, templates_dir=tmp_templates_dir)
    file_template = PromptTemplate(template_id="file1", template="{v1}", variables=["v1"])
    db_template = PromptTemplate(template_id="db1", template="{v2}", variables=["v2"])
    loader._list_file_templates = MagicMock(return_value=[file_template])
    loader._list_db_templates = AsyncMock(return_value=[db_template])
    result = await loader.list_templates()
    ids = {t.template_id for t in result}
    assert "file1" in ids and "db1" in ids


def test_reset_cache(db):
    loader = TemplateLoader(db)
    loader._cache["t1"] = PromptTemplate(template_id="t1", template="{v}", variables=["v"])
    loader.reset_cache()
    assert loader._cache == {}


def test_get_file_template_valid(tmp_templates_dir, db):
    loader = TemplateLoader(db, templates_dir=tmp_templates_dir)
    result = loader._get_file_template("file1")
    assert isinstance(result, PromptTemplate)
    assert result.template_id == "file1"
    # Ensure all variables are present in the template
    for var in result.variables:
        assert f"{{{var}}}" in result.template


def test_get_file_template_invalid_json(tmp_path, db):
    # Create a file with invalid JSON
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not json}")
    loader = TemplateLoader(db, templates_dir=str(tmp_path))
    with patch("app.llm.template_loader.logger") as mock_logger:
        assert loader._get_file_template("bad") is None
        assert mock_logger.error.called


from pydantic import ValidationError


def test_get_file_template_missing_key(tmp_path, db):
    # Create a file missing required keys
    bad_file = tmp_path / "bad2.json"
    bad_file.write_text(json.dumps({"template_id": "bad2"}))
    loader = TemplateLoader(db, templates_dir=str(tmp_path))
    with pytest.raises(ValidationError):
        loader._get_file_template("bad2")


def test_list_file_templates_invalid_json(tmp_path, db):
    # Directory with a file with invalid JSON
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not json}")
    loader = TemplateLoader(db, templates_dir=str(tmp_path))
    with patch("app.llm.template_loader.logger") as mock_logger:
        templates = loader._list_file_templates()
        assert templates == []
        assert mock_logger.error.called


def test_list_file_templates_missing_dir(db):
    loader = TemplateLoader(db, templates_dir="/nonexistent/path")
    with patch("app.llm.template_loader.logger") as mock_logger:
        assert loader._list_file_templates() == []
        assert mock_logger.warning.called


@pytest.mark.asyncio
async def test_get_template_missing_logs_warning(db):
    loader = TemplateLoader(db)
    loader._get_db_template = AsyncMock(return_value=None)
    loader._get_file_template = MagicMock(return_value=None)
    with patch("app.llm.template_loader.logger") as mock_logger:
        result = await loader.get_template("notfound")
        assert result is None
        assert mock_logger.warning.called


def test_list_file_templates_handles_missing_dir(db):
    loader = TemplateLoader(db, templates_dir="/nonexistent/path")
    assert loader._list_file_templates() == []


@pytest.mark.asyncio
async def test_list_db_templates_handles_invalid_variables(db):
    loader = TemplateLoader(db)
    # Create templates - bad one will fail validation, good one should pass
    # The good template needs proper format: template must contain {v} placeholder
    bad_db_template = make_db_template(template_id="bad", template="no vars", variables="notalist")
    good_db_template = make_db_template(
        template_id="good", template="Hello {v} world", variables=["v"]
    )
    # Mock async execute pattern
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [bad_db_template, good_db_template]
    db.execute = AsyncMock(return_value=mock_result)
    result = await loader._list_db_templates()
    ids = {t.template_id for t in result}
    # Bad template should be filtered out due to validation errors
    # Good template should pass validation
    assert "good" in ids
    for t in result:
        assert isinstance(t.variables, list)
