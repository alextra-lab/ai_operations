"""
Visualization Specification Models for AI Operations Platform.

Defines the portable visualization spec that accompanies structured_data
in the execution API response. Uses Vega-Lite for charts/gauges/timelines
and a lightweight TableSpec for tabular data.

Three-Layer Model:
  1. structured_data — Raw JSON (always present when format is json/yaml/structured)
  2. visualization_spec — Vega-Lite + table spec (when template_id configured)
  3. MCP Apps UI — Future HTML bundle in sandboxed iframe

@see ADR-068: Portable Visualization Specification (Vega-Lite)
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class TableColumn(BaseModel):
    """Column definition for table visualization."""

    field: str = Field(..., description="Property name in the data objects")
    header: str = Field(..., description="Display header for the column")
    sortable: bool = Field(default=False, description="Whether column is sortable")
    copyable: bool = Field(default=False, description="Whether cell values are copyable")
    width: str | None = Field(default=None, description="CSS width (e.g. '300px')")


class TableSpec(BaseModel):
    """Lightweight table specification (non-Vega-Lite)."""

    columns: list[TableColumn] = Field(
        default_factory=list,
        description="Column definitions",
    )
    data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Row data (array of objects)",
    )
    filterable: bool = Field(default=False, description="Enable client-side filtering")
    sortable: bool = Field(default=False, description="Enable client-side sorting")
    paginated: bool = Field(default=False, description="Enable client-side pagination")
    export_formats: list[str] = Field(
        default_factory=list,
        description="Supported export formats",
    )


class VisualizationSection(BaseModel):
    """Single section in the visualization layout."""

    section_id: str = Field(..., description="Unique section identifier")
    title: str = Field(..., description="Section title for display")
    type: Literal["vega-lite", "table"] = Field(
        ...,
        description="Section type: 'vega-lite' for charts/gauges/timelines, 'table' for tabular data",
    )
    vega_lite_spec: dict[str, Any] | None = Field(
        default=None,
        description="Vega-Lite specification (when type='vega-lite')",
    )
    table_spec: TableSpec | None = Field(
        default=None,
        description="Table specification (when type='table')",
    )
    width: str = Field(
        default="full",
        description="Layout width hint: 'full', 'half', 'third', 'two-thirds'",
    )


class VisualizationSpec(BaseModel):
    """
    Portable visualization specification.

    Included in the execution API response when a template_id is configured
    and structured_data is present. Consumers can render using any Vega-Lite
    compatible library (web, Python, etc.) and the table spec for tabular data.
    """

    version: str = Field(default="1.0", description="Spec format version")
    layout: Literal["single", "grid", "tabs"] = Field(
        default="grid",
        description="Layout arrangement: single section, grid, or tabbed",
    )
    sections: list[VisualizationSection] = Field(
        default_factory=list,
        description="Ordered list of visualization sections",
    )
