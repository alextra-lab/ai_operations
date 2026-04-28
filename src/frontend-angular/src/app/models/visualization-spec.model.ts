/**
 * Visualization Spec Models (Frontend)
 *
 * TypeScript interfaces matching the backend
 * VisualizationSpec Pydantic models.
 * Used to render portable Vega-Lite visualizations
 * from the execution API response.
 *
 * @see ADR-068: Portable Visualization Specification
 */

/** Column definition for table sections. */
export interface VizTableColumn {
  field: string;
  header: string;
  sortable?: boolean;
  copyable?: boolean;
  width?: string;
}

/** Lightweight table specification. */
export interface VizTableSpec {
  columns: VizTableColumn[];
  data: Record<string, unknown>[];
  filterable?: boolean;
  sortable?: boolean;
  paginated?: boolean;
  export_formats?: string[];
}

/** Section types in a visualization spec. */
export type VizSectionType = 'vega-lite' | 'table';

/** Layout types for the spec. */
export type VizLayout = 'single' | 'grid' | 'tabs';

/** Single section in the visualization layout. */
export interface VizSection {
  section_id: string;
  title: string;
  type: VizSectionType;
  vega_lite_spec?: Record<string, unknown>;
  table_spec?: VizTableSpec;
  width?: string;
}

/**
 * Portable visualization specification.
 *
 * Included in the execution API response when
 * template_id + structured_data are present.
 */
export interface VisualizationSpec {
  version: string;
  layout: VizLayout;
  sections: VizSection[];
}
