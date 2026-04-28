/**
 * Structured Output Renderer Component
 *
 * Renders formatted Use Case responses with template-driven visualizations.
 * Dynamically selects and configures visualizer components based on section type.
 *
 * Supports:
 * - Table visualizations (sortable, filterable, paginated)
 * - Chart visualizations (bar, line, pie)
 * - Gauge visualizations (single value metrics)
 * - Timeline visualizations (chronological events)
 * - Text/panel (comparison-grid side-by-side; config display=panel)
 * - Text/key-value grid (kv-summary; config display=key-value-grid)
 *
 * Related: P4-TOOLS-06, P3-F5, ADR-045
 */

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';

// Angular Material
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';

// Internal imports
import {
  ChartConfig,
  FormattedOutput,
  GaugeConfig,
  RenderedSection,
  TableConfig,
  TimelineConfig,
} from '../../models/output-format.model';
import { ChartVisualizerComponent } from '../visualizers/chart-visualizer/chart-visualizer.component';
import { GaugeVisualizerComponent } from '../visualizers/gauge-visualizer/gauge-visualizer.component';
import { TableVisualizerComponent } from '../visualizers/table-visualizer/table-visualizer.component';
import { TimelineVisualizerComponent } from '../visualizers/timeline-visualizer/timeline-visualizer.component';

@Component({
  selector: 'app-structured-output-renderer',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatDividerModule,
    MatIconModule,
    TableVisualizerComponent,
    ChartVisualizerComponent,
    GaugeVisualizerComponent,
    TimelineVisualizerComponent,
  ],
  templateUrl: './structured-output-renderer.component.html',
  styleUrls: ['./structured-output-renderer.component.scss'],
})
export class StructuredOutputRendererComponent implements OnInit {
  @Input() formattedOutput!: FormattedOutput;
  @Output() actionClick = new EventEmitter<{
    handler: string;
    data: unknown;
  }>();

  // Rendered sections (may be filtered/reordered)
  visibleSections: RenderedSection[] = [];

  ngOnInit(): void {
    this.setupVisibleSections();
  }

  /**
   * Setup visible sections (apply filters, ordering, etc.)
   */
  private setupVisibleSections(): void {
    if (!this.formattedOutput || !this.formattedOutput.rendered_sections) {
      this.visibleSections = [];
      return;
    }

    // Filter out sections with no data
    this.visibleSections = this.formattedOutput.rendered_sections.filter(
      (section) => this.hasSectionData(section)
    );
  }

  /**
   * Check if section has data to display
   */
  private hasSectionData(section: RenderedSection): boolean {
    if (!section.data) {
      return false;
    }

    // Array data: check if not empty
    if (Array.isArray(section.data)) {
      return section.data.length > 0;
    }

    // Object data: check if not null/undefined
    return section.data !== null && section.data !== undefined;
  }

  /**
   * Get section width class for layout
   */
  getSectionWidthClass(section: RenderedSection): string {
    switch (section.width) {
      case 'half':
        return 'section-half';
      case 'third':
        return 'section-third';
      case 'two-thirds':
        return 'section-two-thirds';
      case 'full':
      default:
        return 'section-full';
    }
  }

  /**
   * Get icon for component type
   */
  getComponentIcon(type: string): string {
    switch (type) {
      case 'table':
        return 'table_chart';
      case 'chart':
        return 'bar_chart';
      case 'gauge':
        return 'speed';
      case 'timeline':
        return 'timeline';
      case 'text':
        return 'subject';
      default:
        return 'dashboard';
    }
  }

  /**
   * Whether section is a text panel (e.g. comparison-grid left/right).
   */
  isTextPanel(section: RenderedSection): boolean {
    const config = section.config as Record<string, unknown>;
    return config?.['display'] === 'panel';
  }

  /**
   * Whether section is a key-value grid (e.g. kv-summary).
   */
  isTextKeyValueGrid(section: RenderedSection): boolean {
    const config = section.config as Record<string, unknown>;
    return config?.['display'] === 'key-value-grid';
  }

  /**
   * Title for panel display (from data using config.title_field).
   */
  getTextPanelTitle(section: RenderedSection): string {
    const config = section.config as Record<string, unknown>;
    const field = (config?.['title_field'] as string) ?? 'title';
    const obj = section.data as Record<string, unknown>;
    const v = obj?.[field];
    return typeof v === 'string' ? v : String(v ?? section.title);
  }

  /**
   * Content for panel display (from data using config.content_field).
   * Preserves newlines for display.
   */
  getTextPanelContent(section: RenderedSection): string {
    const config = section.config as Record<string, unknown>;
    const field = (config?.['content_field'] as string) ?? 'content';
    const obj = section.data as Record<string, unknown>;
    const v = obj?.[field];
    return typeof v === 'string' ? v : String(v ?? '');
  }

  /**
   * Key-value pairs from object (for key-value-grid display).
   */
  getKeyValuePairs(data: unknown): { key: string; value: string }[] {
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      return [];
    }
    const obj = data as Record<string, unknown>;
    return Object.entries(obj).map(([key, value]) => ({
      key,
      value: value != null ? String(value) : '',
    }));
  }

  /**
   * Handle action click from visualizer
   */
  onActionClick(event: { handler: string; data: unknown }): void {
    this.actionClick.emit(event);
  }

  /**
   * Track sections for *ngFor performance
   */
  trackBySection(index: number, section: RenderedSection): string {
    return section.section_id;
  }

  /**
   * Type-safe cast to array data
   */
  asDataArray(data: unknown): unknown[] {
    if (Array.isArray(data)) {
      return data;
    }
    return [];
  }

  /**
   * Type-safe cast to TableConfig
   */
  asTableConfig(config: unknown): TableConfig {
    return config as TableConfig;
  }

  /**
   * Type-safe cast to ChartConfig
   */
  asChartConfig(config: unknown): ChartConfig {
    return config as ChartConfig;
  }

  /**
   * Type-safe cast to GaugeConfig
   */
  asGaugeConfig(config: unknown): GaugeConfig {
    return config as GaugeConfig;
  }

  /**
   * Type-safe cast to TimelineConfig
   */
  asTimelineConfig(config: unknown): TimelineConfig {
    return config as TimelineConfig;
  }

  /**
   * Extract numeric value from gauge data
   */
  asGaugeValue(data: unknown): number {
    if (typeof data === 'number') {
      return data;
    }
    if (typeof data === 'object' && data !== null && 'value' in data) {
      const value = (data as { value: unknown }).value;
      return typeof value === 'number' ? value : 0;
    }
    return 0;
  }
}
