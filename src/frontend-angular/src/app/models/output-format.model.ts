/**
 * Output Format Models
 *
 * TypeScript interfaces for output formatting templates and configurations.
 * These models define how Use Case responses are rendered with visualizations.
 */

/**
 * Visualization component types supported by the system
 */
export type VisualizationType =
  | 'text'
  | 'table'
  | 'chart'
  | 'gauge'
  | 'timeline'
  | 'network-graph'
  | 'code-block'
  | 'mermaid'
  | 'katex'
  | 'custom';

/**
 * Export format types supported by visualizers
 */
export type ExportFormat = 'pdf' | 'csv' | 'json' | 'excel';

/**
 * Layout types for template sections
 */
export type LayoutType = 'single' | 'grid' | 'tabs';

/**
 * Section width options (for grid layouts)
 */
export type SectionWidth = 'full' | 'half' | 'third' | 'two-thirds';

/**
 * Chart types for chart visualizer
 */
export type ChartType =
  | 'bar'
  | 'line'
  | 'pie'
  | 'doughnut'
  | 'radar'
  | 'scatter';

/**
 * Configuration for a single output section
 */
export interface OutputSection {
  section_id: string;
  title: string;
  component_type: VisualizationType;
  data_path: string; // JSON path in structured_data (e.g., "$.iocs")
  config: ComponentConfig;
  width?: SectionWidth;
}

/**
 * Base component configuration interface
 */
export type ComponentConfig = Record<string, unknown>;

/**
 * Configuration for table visualizer
 */
export interface TableConfig extends ComponentConfig {
  columns: TableColumn[];
  filterable?: boolean;
  sortable?: boolean;
  paginated?: boolean;
  actions?: TableAction[];
  export?: ExportFormat[];
  /** When true, data is array of { [tab_title_field]: string, [tab_data_field]: row[] }; one tab per item. */
  tabbed?: boolean;
  /** Field on each tab item used as tab label (e.g. 'title'). */
  tab_title_field?: string;
  /** Field on each tab item containing row array for that tab (e.g. 'rows'). */
  tab_data_field?: string;
}

/**
 * Table column configuration
 */
export interface TableColumn {
  field: string;
  header: string;
  sortable?: boolean;
  copyable?: boolean;
  width?: string;
}

/**
 * Table action button configuration
 */
export interface TableAction {
  label: string;
  icon: string;
  handler: string; // Name of handler function
}

/**
 * Configuration for chart visualizer
 */
export interface ChartConfig extends ComponentConfig {
  chart_type: ChartType;
  label?: string;
  colors?: string[];
  show_legend?: boolean;
  legend_position?: 'top' | 'bottom' | 'left' | 'right';
  chart_options?: Record<string, unknown>;
}

/**
 * Configuration for gauge visualizer
 */
export interface GaugeConfig extends ComponentConfig {
  min: number;
  max: number;
  thresholds: GaugeThreshold[];
  format?: 'number' | 'percent';
}

/**
 * Gauge threshold definition
 */
export interface GaugeThreshold {
  value: number;
  color: string;
  label: string;
}

/**
 * Configuration for timeline visualizer
 */
export interface TimelineConfig extends ComponentConfig {
  time_field: string;
  label_field: string;
  severity_field?: string;
  details_field?: string;
}

/**
 * Template layout configuration
 */
export interface TemplateLayout {
  type: LayoutType;
  sections: OutputSection[];
}

/**
 * Output format template definition
 */
export interface OutputFormatTemplate {
  template_id: string;
  name: string;
  description: string;
  data_schema: JSONSchema; // JSON Schema for data validation
  layout: TemplateLayout;
  export_formats: ExportFormat[];
}

/**
 * JSON Schema interface (simplified)
 */
export interface JSONSchema {
  type?: string;
  properties?: Record<string, JSONSchema>;
  required?: string[];
  items?: JSONSchema;
  enum?: unknown[];
  minimum?: number;
  maximum?: number;
  [key: string]: unknown;
}

/**
 * Formatted output result
 */
export interface FormattedOutput {
  raw_content: string;
  structured_data?: unknown;
  template?: OutputFormatTemplate;
  rendered_sections: RenderedSection[];
}

/**
 * Rendered section with resolved data
 */
export interface RenderedSection {
  section_id: string;
  title: string;
  component_type: VisualizationType;
  data: unknown;
  config: ComponentConfig;
  width?: SectionWidth;
}

/**
 * Use Case response with structured data
 */
export interface UseCaseResponse {
  answer: string;
  structured_data?: unknown;
  template_id?: string;
}
