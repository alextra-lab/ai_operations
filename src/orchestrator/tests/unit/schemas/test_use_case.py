"""
Unit tests for UseCase schemas.

Tests validation of UseCaseListItem and UseCaseListResponse schemas,
including enum conversion, type validation, and field defaults.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from app.schemas.intent import RequestType
from app.schemas.use_case import UseCaseListItem, UseCaseListResponse
from pydantic import ValidationError


class TestUseCaseListItem:
    """Test UseCaseListItem schema validation."""

    def test_valid_use_case_list_item(self):
        """Test creating a valid UseCaseListItem."""
        use_case_id = uuid4()
        item = UseCaseListItem(
            id=use_case_id,
            name="Test Use Case",
            description="Test description",
            category="test",
            intent_type=RequestType.QUERY,
            is_active=True,
            lifecycle_state="published",
            version="1.0",
            updated_at=datetime.now(),
        )
        assert item.id == use_case_id
        assert item.name == "Test Use Case"
        assert item.intent_type == RequestType.QUERY

    def test_use_case_list_item_with_optional_fields(self):
        """Test UseCaseListItem with optional fields."""
        use_case_id = uuid4()
        item = UseCaseListItem(
            id=use_case_id,
            name="Test Use Case",
            intent_type=RequestType.SUMMARIZATION,
            icon="shield",
            tags=["test", "example"],
        )
        assert item.icon == "shield"
        assert item.tags == ["test", "example"]
        assert item.description is None
        assert item.category is None

    def test_use_case_list_item_defaults(self):
        """Test UseCaseListItem default values."""
        use_case_id = uuid4()
        item = UseCaseListItem(
            id=use_case_id,
            name="Test Use Case",
            intent_type=RequestType.QUERY,
        )
        assert item.is_active is True
        assert item.lifecycle_state == "published"
        assert item.version == "1.0"
        assert item.icon is None
        assert item.tags == []

    def test_use_case_list_item_all_intent_types(self):
        """Test UseCaseListItem with all RequestType enum values."""
        use_case_id = uuid4()
        for intent_type in [
            RequestType.QUERY,
            RequestType.RULE_GENERATION,
            RequestType.SUMMARIZATION,
            RequestType.ENRICHMENT,
        ]:
            item = UseCaseListItem(
                id=use_case_id,
                name=f"Test {intent_type.value}",
                intent_type=intent_type,
            )
            assert item.intent_type == intent_type

    def test_use_case_list_item_missing_required_fields(self):
        """Test UseCaseListItem validation with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            UseCaseListItem(
                name="Test Use Case",
                intent_type=RequestType.QUERY,
            )
        assert "id" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            UseCaseListItem(
                id=uuid4(),
                intent_type=RequestType.QUERY,
            )
        assert "name" in str(exc_info.value)

    def test_use_case_list_item_name_min_length(self):
        """Test UseCaseListItem name min_length validation."""
        with pytest.raises(ValidationError) as exc_info:
            UseCaseListItem(
                id=uuid4(),
                name="",
                intent_type=RequestType.QUERY,
            )
        assert "name" in str(exc_info.value)


class TestUseCaseListResponse:
    """Test UseCaseListResponse schema validation."""

    def test_valid_use_case_list_response(self):
        """Test creating a valid UseCaseListResponse."""
        items = [
            UseCaseListItem(
                id=uuid4(),
                name="Use Case 1",
                intent_type=RequestType.QUERY,
            ),
            UseCaseListItem(
                id=uuid4(),
                name="Use Case 2",
                intent_type=RequestType.SUMMARIZATION,
            ),
        ]
        response = UseCaseListResponse(use_cases=items, total=2)
        assert len(response.use_cases) == 2
        assert response.total == 2

    def test_empty_use_case_list_response(self):
        """Test UseCaseListResponse with empty list."""
        response = UseCaseListResponse(use_cases=[], total=0)
        assert len(response.use_cases) == 0
        assert response.total == 0

    def test_use_case_list_response_total_mismatch(self):
        """Test UseCaseListResponse with total not matching items count."""
        # This should still work - total can be different from items count
        # (e.g., when paginated)
        items = [
            UseCaseListItem(
                id=uuid4(),
                name="Use Case 1",
                intent_type=RequestType.QUERY,
            ),
        ]
        response = UseCaseListResponse(use_cases=items, total=5)
        assert len(response.use_cases) == 1
        assert response.total == 5

    def test_use_case_list_response_missing_required_fields(self):
        """Test UseCaseListResponse validation with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            UseCaseListResponse(use_cases=[])
        assert "total" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            UseCaseListResponse(total=0)
        assert "use_cases" in str(exc_info.value)

    def test_use_case_list_response_total_ge_zero(self):
        """Test UseCaseListResponse total must be >= 0."""
        # Total can be 0
        response = UseCaseListResponse(use_cases=[], total=0)
        assert response.total == 0

        # Total cannot be negative
        with pytest.raises(ValidationError) as exc_info:
            UseCaseListResponse(use_cases=[], total=-1)
        assert "total" in str(exc_info.value)


class TestUseCaseSchemaFieldNames:
    """Test that schema field names match API contract."""

    def test_response_uses_use_cases_field(self):
        """Test that UseCaseListResponse uses 'use_cases' field name."""
        items = [
            UseCaseListItem(
                id=uuid4(),
                name="Test Use Case",
                intent_type=RequestType.QUERY,
            ),
        ]
        response = UseCaseListResponse(use_cases=items, total=1)

        # Verify field name in dict representation
        response_dict = response.model_dump()
        assert "use_cases" in response_dict
        assert "total" in response_dict
        assert "items" not in response_dict  # Should NOT have 'items' field

    def test_json_serialization(self):
        """Test JSON serialization produces correct field names."""
        items = [
            UseCaseListItem(
                id=uuid4(),
                name="Test Use Case",
                intent_type=RequestType.QUERY,
            ),
        ]
        response = UseCaseListResponse(use_cases=items, total=1)

        # Serialize to JSON
        json_str = response.model_dump_json()
        import json

        data = json.loads(json_str)

        assert "use_cases" in data
        assert "total" in data
        assert len(data["use_cases"]) == 1
