"""
Visualization Spec Generator for AI Operations Platform.

Translates output formatting templates (component_type-based) into
portable Vega-Lite specifications. This allows any Vega-Lite compatible
consumer (web, Python, notebook) to render the same visualization
without the Angular-specific rendering pipeline.

Component mapping:
  gauge     → vega-lite (arc/radial mark)
  chart     → vega-lite (bar/line/pie marks)
  timeline  → vega-lite (temporal point/tick mark)
  table     → table (TableSpec with column definitions + data)

@see ADR-068: Portable Visualization Specification (Vega-Lite)
"""

from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ..schemas.visualization_spec import (
    TableColumn,
    TableSpec,
    VisualizationSection,
    VisualizationSpec,
)

logger = configure_logging(service_name="visualization_spec_generator")


class VisualizationSpecGenerator:
    """
    Generates a portable VisualizationSpec from a template
    definition and structured_data.
    """

    def generate(
        self,
        template: dict[str, Any],
        structured_data: dict[str, Any],
    ) -> VisualizationSpec:
        """
        Generate visualization spec from template + data.

        Args:
            template: Template definition dict with layout.sections
            structured_data: Parsed structured data from LLM output

        Returns:
            VisualizationSpec with Vega-Lite and/or table sections
        """
        layout_def = template.get("layout", {})
        layout_type = layout_def.get("type", "grid")
        sections_def = layout_def.get("sections", [])

        sections: list[VisualizationSection] = []
        for section_def in sections_def:
            section = self._translate_section(section_def, structured_data)
            if section:
                sections.append(section)

        return VisualizationSpec(
            version="1.0",
            layout=layout_type,
            sections=sections,
        )

    def _translate_section(
        self,
        section_def: dict[str, Any],
        structured_data: dict[str, Any],
    ) -> VisualizationSection | None:
        """Translate a single template section to a viz section."""
        component_type = section_def.get("component_type", "text")
        section_id = section_def.get("section_id", "unknown")
        title = section_def.get("title", "")
        data_path = section_def.get("data_path", "")
        config = section_def.get("config", {})
        width = section_def.get("width", "full")

        # Extract data using JSONPath-like root key
        data = self._extract_data(data_path, structured_data)

        if component_type == "gauge":
            return self._gauge_to_vega_lite(section_id, title, data, config, width)
        if component_type == "chart":
            return self._chart_to_vega_lite(section_id, title, data, config, width)
        if component_type == "timeline":
            return self._timeline_to_vega_lite(section_id, title, data, config, width)
        if component_type == "table":
            return self._table_to_spec(section_id, title, data, config, width)
        # text and other types: skip for visualization spec
        return None

    def _extract_data(
        self,
        data_path: str,
        structured_data: dict[str, Any],
    ) -> Any:
        """Extract data using simple JSONPath ($.key.subkey)."""
        if not data_path or not data_path.startswith("$"):
            return structured_data

        parts = data_path.lstrip("$.").split(".")
        current: Any = structured_data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _gauge_to_vega_lite(
        self,
        section_id: str,
        title: str,
        data: Any,
        config: dict[str, Any],
        width: str,
    ) -> VisualizationSection:
        """Convert gauge component to Vega-Lite arc mark."""
        value = float(data) if data is not None else 0
        min_val = config.get("min", 0)
        max_val = config.get("max", 1)
        fmt = config.get("format", "number")
        thresholds = config.get("thresholds", [])

        # Determine color from thresholds
        color = "#1976d2"
        for t in thresholds:
            if value <= t.get("value", 0):
                color = t.get("color", color)
                break

        # Normalize to 0-1 for arc
        normalized = (value - min_val) / (max_val - min_val) if max_val != min_val else 0

        vega_spec: dict[str, Any] = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "width": 200,
            "height": 200,
            "data": {
                "values": [
                    {"value": normalized, "label": "value"},
                    {"value": 1 - normalized, "label": "remaining"},
                ],
            },
            "mark": {"type": "arc", "innerRadius": 60},
            "encoding": {
                "theta": {
                    "field": "value",
                    "type": "quantitative",
                    "stack": True,
                },
                "color": {
                    "field": "label",
                    "type": "nominal",
                    "scale": {
                        "domain": ["value", "remaining"],
                        "range": [color, "#e0e0e0"],
                    },
                    "legend": None,
                },
            },
            "layer": [
                {
                    "mark": {"type": "arc", "innerRadius": 60},
                },
                {
                    "mark": {
                        "type": "text",
                        "fontSize": 24,
                        "fontWeight": "bold",
                    },
                    "encoding": {
                        "text": {
                            "value": (f"{value:.0%}" if fmt == "percent" else str(value)),
                        },
                    },
                },
            ],
        }

        return VisualizationSection(
            section_id=section_id,
            title=title,
            type="vega-lite",
            vega_lite_spec=vega_spec,
            width=width,
        )

    def _chart_to_vega_lite(
        self,
        section_id: str,
        title: str,
        data: Any,
        config: dict[str, Any],
        width: str,
    ) -> VisualizationSection:
        """Convert chart component to Vega-Lite bar/line/pie."""
        chart_type = config.get("chart_type", "bar")
        items = data if isinstance(data, list) else []

        if chart_type == "pie":
            vega_spec = self._pie_chart(title, items)
        elif chart_type == "line":
            vega_spec = self._line_chart(title, items)
        else:
            vega_spec = self._bar_chart(title, items)

        return VisualizationSection(
            section_id=section_id,
            title=title,
            type="vega-lite",
            vega_lite_spec=vega_spec,
            width=width,
        )

    def _bar_chart(
        self,
        title: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate Vega-Lite bar chart spec."""
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "width": "container",
            "height": 300,
            "data": {"values": items},
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "x": {
                    "field": "label",
                    "type": "nominal",
                    "axis": {"labelAngle": -45},
                },
                "y": {
                    "field": "value",
                    "type": "quantitative",
                },
                "color": {
                    "field": "label",
                    "type": "nominal",
                    "legend": None,
                },
            },
        }

    def _line_chart(
        self,
        title: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate Vega-Lite line chart spec."""
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "width": "container",
            "height": 300,
            "data": {"values": items},
            "mark": {"type": "line", "point": True, "tooltip": True},
            "encoding": {
                "x": {
                    "field": "label",
                    "type": "nominal",
                },
                "y": {
                    "field": "value",
                    "type": "quantitative",
                },
            },
        }

    def _pie_chart(
        self,
        title: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate Vega-Lite pie (arc) chart spec."""
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "width": 300,
            "height": 300,
            "data": {"values": items},
            "mark": {"type": "arc", "tooltip": True},
            "encoding": {
                "theta": {
                    "field": "value",
                    "type": "quantitative",
                },
                "color": {
                    "field": "label",
                    "type": "nominal",
                },
            },
        }

    def _timeline_to_vega_lite(
        self,
        section_id: str,
        title: str,
        data: Any,
        config: dict[str, Any],
        width: str,
    ) -> VisualizationSection:
        """Convert timeline to Vega-Lite temporal tick marks."""
        items = data if isinstance(data, list) else []
        time_field = config.get("time_field", "timestamp")
        label_field = config.get("label_field", "description")
        severity_field = config.get("severity_field")

        encoding: dict[str, Any] = {
            "x": {
                "field": time_field,
                "type": "temporal",
                "title": "Time",
            },
            "y": {
                "field": label_field,
                "type": "nominal",
                "title": "",
            },
            "tooltip": [
                {"field": time_field, "type": "temporal"},
                {"field": label_field, "type": "nominal"},
            ],
        }

        if severity_field:
            encoding["color"] = {
                "field": severity_field,
                "type": "nominal",
                "scale": {
                    "domain": [
                        "low",
                        "medium",
                        "high",
                        "critical",
                    ],
                    "range": [
                        "#4caf50",
                        "#ff9800",
                        "#f57c00",
                        "#f44336",
                    ],
                },
            }

        vega_spec: dict[str, Any] = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "width": "container",
            "height": max(100, len(items) * 30),
            "data": {"values": items},
            "mark": {
                "type": "circle",
                "size": 100,
                "tooltip": True,
            },
            "encoding": encoding,
        }

        return VisualizationSection(
            section_id=section_id,
            title=title,
            type="vega-lite",
            vega_lite_spec=vega_spec,
            width=width,
        )

    def _table_to_spec(
        self,
        section_id: str,
        title: str,
        data: Any,
        config: dict[str, Any],
        width: str,
    ) -> VisualizationSection:
        """Convert table component to TableSpec."""
        items = data if isinstance(data, list) else []
        col_defs = config.get("columns", [])

        # Auto-detect columns if not defined
        if not col_defs and items:
            col_defs = [{"field": k, "header": k.replace("_", " ").title()} for k in items[0]]

        columns = [
            TableColumn(
                field=c.get("field", ""),
                header=c.get("header", c.get("field", "")),
                sortable=c.get("sortable", False),
                copyable=c.get("copyable", False),
                width=c.get("width"),
            )
            for c in col_defs
        ]

        table_spec = TableSpec(
            columns=columns,
            data=items,
            filterable=config.get("filterable", False),
            sortable=config.get("sortable", False),
            paginated=config.get("paginated", False),
            export_formats=config.get("export", []),
        )

        return VisualizationSection(
            section_id=section_id,
            title=title,
            type="table",
            table_spec=table_spec,
            width=width,
        )
