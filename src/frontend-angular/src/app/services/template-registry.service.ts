/**
 * Template Registry Service
 *
 * Service for managing output format templates.
 * Provides built-in structural templates and template
 * lookup functionality.
 *
 * ADR-066: Templates use structural/layout-descriptive
 * names, NOT domain-specific names. Domain expertise is
 * expressed through schema presets, not template names.
 *
 * Built-in templates:
 *   score-table-timeline  (was: threat-triage-dashboard)
 *   filterable-table      (was: ioc-extraction-table)
 *   score-timeline        (was: incident-summary)
 *   auto-table            (was: simple-table)
 *   bar-chart             (was: metrics-dashboard)
 *   kv-summary            (new)
 *   multi-table           (new)
 *   comparison-grid       (new)
 */

import { Injectable } from '@angular/core';
import {
  OutputFormatTemplate,
} from '../models/output-format.model';
import {
  OutputTemplateApiResponse,
  OutputTemplateApiService,
} from '../api/services/output-template.service';

@Injectable({
  providedIn: 'root',
})
export class TemplateRegistryService {
  private templates =
    new Map<string, OutputFormatTemplate>();
  private customLoaded = false;

  constructor(
    private outputTemplateApi: OutputTemplateApiService
  ) {
    this.registerBuiltInTemplates();
  }

  /**
   * Load custom templates from backend and merge
   * with built-in templates. Safe to call multiple
   * times; only fetches once.
   */
  async loadCustomTemplates(): Promise<void> {
    if (this.customLoaded) return;
    try {
      const response = await this.outputTemplateApi
        .list(1, 200)
        .toPromise();
      if (response?.templates) {
        for (const tpl of response.templates) {
          // Custom templates don't overwrite built-ins
          if (!this.templates.has(tpl.template_id)) {
            this.register(
              this.mapApiToTemplate(tpl)
            );
          }
        }
      }
      this.customLoaded = true;
    } catch {
      // Graceful fallback: built-ins still work
      this.customLoaded = true;
    }
  }

  /** Convert API response to frontend model. */
  private mapApiToTemplate(
    api: OutputTemplateApiResponse
  ): OutputFormatTemplate {
    return {
      template_id: api.template_id,
      name: api.name,
      description: api.description,
      data_schema: api.data_schema as any,
      layout: api.layout as any,
      export_formats: api.export_formats as any,
    };
  }

  /**
   * Register all built-in structural templates (ADR-066).
   */
  private registerBuiltInTemplates(): void {
    // ======================================================
    // 1. Score + Table + Timeline
    //    (was: threat-triage-dashboard)
    // ======================================================
    this.register({
      template_id: 'score-table-timeline',
      name: 'Score + Table + Timeline',
      description:
        'Gauge score, data table, and chronological '
        + 'timeline in a grid layout',
      data_schema: {
        type: 'object',
        required: [
          'score',
          'confidence',
          'items',
          'events',
        ],
        properties: {
          score: {
            type: 'string',
            enum: ['low', 'medium', 'high', 'critical'],
          },
          confidence: {
            type: 'number',
            minimum: 0,
            maximum: 1,
          },
          items: { type: 'array' },
          events: { type: 'array' },
        },
      },
      layout: {
        type: 'grid',
        sections: [
          {
            section_id: 'score-gauge',
            title: 'Score',
            component_type: 'gauge',
            data_path: '$.confidence',
            config: {
              min: 0,
              max: 1,
              format: 'percent',
              thresholds: [
                {
                  value: 0.3,
                  color: '#4caf50',
                  label: 'Low',
                },
                {
                  value: 0.6,
                  color: '#ff9800',
                  label: 'Medium',
                },
                {
                  value: 0.8,
                  color: '#f57c00',
                  label: 'High',
                },
                {
                  value: 1.0,
                  color: '#f44336',
                  label: 'Critical',
                },
              ],
            },
            width: 'third',
          },
          {
            section_id: 'data-table',
            title: 'Items',
            component_type: 'table',
            data_path: '$.items',
            config: {
              columns: [
                {
                  field: 'type',
                  header: 'Type',
                  sortable: true,
                },
                {
                  field: 'value',
                  header: 'Value',
                  copyable: true,
                },
                {
                  field: 'context',
                  header: 'Context',
                  width: '300px',
                },
              ],
              filterable: true,
              sortable: true,
              export: ['csv', 'json'],
            },
            width: 'full',
          },
          {
            section_id: 'event-timeline',
            title: 'Event Timeline',
            component_type: 'timeline',
            data_path: '$.events',
            config: {
              time_field: 'timestamp',
              label_field: 'description',
              severity_field: 'severity',
            },
            width: 'full',
          },
        ],
      },
      export_formats: ['pdf', 'json'],
    });

    // ======================================================
    // 2. Filterable Data Table
    //    (was: ioc-extraction-table)
    // ======================================================
    this.register({
      template_id: 'filterable-table',
      name: 'Filterable Data Table',
      description:
        'Single sortable, filterable table with '
        + 'export capabilities',
      data_schema: {
        type: 'object',
        required: ['items'],
        properties: {
          items: {
            type: 'array',
            items: {
              type: 'object',
              required: ['type', 'value'],
              properties: {
                type: { type: 'string' },
                value: { type: 'string' },
                context: { type: 'string' },
                confidence: { type: 'number' },
              },
            },
          },
        },
      },
      layout: {
        type: 'single',
        sections: [
          {
            section_id: 'data-table',
            title: 'Extracted Data',
            component_type: 'table',
            data_path: '$.items',
            config: {
              columns: [
                {
                  field: 'type',
                  header: 'Type',
                  sortable: true,
                },
                {
                  field: 'value',
                  header: 'Value',
                  copyable: true,
                },
                {
                  field: 'confidence',
                  header: 'Confidence',
                },
                {
                  field: 'context',
                  header: 'Context',
                  width: '400px',
                },
              ],
              filterable: true,
              sortable: true,
              paginated: true,
              export: ['csv', 'json', 'excel'],
            },
            width: 'full',
          },
        ],
      },
      export_formats: ['csv', 'json', 'excel'],
    });

    // ======================================================
    // 3. Score + Timeline
    //    (was: incident-summary)
    // ======================================================
    this.register({
      template_id: 'score-timeline',
      name: 'Score + Timeline',
      description:
        'Gauge metric with event timeline',
      data_schema: {
        type: 'object',
        required: ['events', 'metric', 'status'],
        properties: {
          events: { type: 'array' },
          metric: {
            type: 'object',
            properties: {
              severity: {
                type: 'number',
                minimum: 0,
                maximum: 10,
              },
              affected_count: { type: 'number' },
              data_loss: { type: 'boolean' },
            },
          },
          status: {
            type: 'string',
            enum: [
              'detected',
              'investigating',
              'contained',
              'resolved',
            ],
          },
        },
      },
      layout: {
        type: 'grid',
        sections: [
          {
            section_id: 'score-gauge',
            title: 'Severity',
            component_type: 'gauge',
            data_path: '$.metric.severity',
            config: {
              min: 0,
              max: 10,
              format: 'number',
              thresholds: [
                {
                  value: 3,
                  color: '#4caf50',
                  label: 'Low',
                },
                {
                  value: 6,
                  color: '#ff9800',
                  label: 'Medium',
                },
                {
                  value: 8,
                  color: '#f57c00',
                  label: 'High',
                },
                {
                  value: 10,
                  color: '#f44336',
                  label: 'Critical',
                },
              ],
            },
            width: 'third',
          },
          {
            section_id: 'event-timeline',
            title: 'Event Timeline',
            component_type: 'timeline',
            data_path: '$.events',
            config: {
              time_field: 'timestamp',
              label_field: 'description',
              severity_field: 'severity',
              details_field: 'details',
            },
            width: 'two-thirds',
          },
        ],
      },
      export_formats: ['pdf', 'json'],
    });

    // ======================================================
    // 4. Auto-Column Table
    //    (was: simple-table)
    // ======================================================
    this.register({
      template_id: 'auto-table',
      name: 'Auto-Column Table',
      description:
        'Generic table with auto-detected columns',
      data_schema: {
        type: 'object',
        required: ['data'],
        properties: {
          data: {
            type: 'array',
            items: { type: 'object' },
          },
        },
      },
      layout: {
        type: 'single',
        sections: [
          {
            section_id: 'data-table',
            title: 'Data',
            component_type: 'table',
            data_path: '$.data',
            config: {
              columns: [],
              filterable: true,
              sortable: true,
              export: ['csv', 'json'],
            },
            width: 'full',
          },
        ],
      },
      export_formats: ['csv', 'json'],
    });

    // ======================================================
    // 5. Bar Chart
    //    (was: metrics-dashboard)
    // ======================================================
    this.register({
      template_id: 'bar-chart',
      name: 'Bar Chart',
      description:
        'Bar chart for labeled numeric data',
      data_schema: {
        type: 'object',
        required: ['metrics'],
        properties: {
          metrics: {
            type: 'array',
            items: {
              type: 'object',
              required: ['label', 'value'],
              properties: {
                label: { type: 'string' },
                value: { type: 'number' },
              },
            },
          },
        },
      },
      layout: {
        type: 'grid',
        sections: [
          {
            section_id: 'bar-chart',
            title: 'Metrics',
            component_type: 'chart',
            data_path: '$.metrics',
            config: {
              chart_type: 'bar',
              show_legend: false,
              chart_options: {
                scales: {
                  y: { beginAtZero: true },
                },
              },
            },
            width: 'full',
          },
        ],
      },
      export_formats: ['pdf', 'json'],
    });

    // ======================================================
    // 6. Key-Value Summary (NEW — ADR-066)
    // ======================================================
    this.register({
      template_id: 'kv-summary',
      name: 'Key-Value Summary',
      description:
        'Grid of labeled values for single-object '
        + 'results',
      data_schema: {
        type: 'object',
        required: ['summary'],
        properties: {
          summary: {
            type: 'object',
            additionalProperties: true,
          },
        },
      },
      layout: {
        type: 'grid',
        sections: [
          {
            section_id: 'kv-grid',
            title: 'Summary',
            component_type: 'text',
            data_path: '$.summary',
            config: {
              display: 'key-value-grid',
              columns: 2,
            },
            width: 'full',
          },
        ],
      },
      export_formats: ['json'],
    });

    // ======================================================
    // 7. Multi-Table View (NEW — ADR-066)
    // ======================================================
    this.register({
      template_id: 'multi-table',
      name: 'Multi-Table View',
      description:
        'Multiple tables in a tabbed layout for '
        + 'results with collections',
      data_schema: {
        type: 'object',
        required: ['tables'],
        properties: {
          tables: {
            type: 'array',
            items: {
              type: 'object',
              required: ['title', 'rows'],
              properties: {
                title: { type: 'string' },
                rows: {
                  type: 'array',
                  items: { type: 'object' },
                },
              },
            },
          },
        },
      },
      layout: {
        type: 'tabs',
        sections: [
          {
            section_id: 'tabbed-tables',
            title: 'Results',
            component_type: 'table',
            data_path: '$.tables',
            config: {
              columns: [],
              filterable: true,
              sortable: true,
              tabbed: true,
              tab_title_field: 'title',
              tab_data_field: 'rows',
              export: ['csv', 'json'],
            },
            width: 'full',
          },
        ],
      },
      export_formats: ['csv', 'json'],
    });

    // ======================================================
    // 8. Comparison Grid (NEW — ADR-066)
    // ======================================================
    this.register({
      template_id: 'comparison-grid',
      name: 'Comparison Grid',
      description:
        'Side-by-side columns for before/after, '
        + 'option comparison, or diff views',
      data_schema: {
        type: 'object',
        required: ['left', 'right'],
        properties: {
          left: {
            type: 'object',
            required: ['title', 'content'],
            properties: {
              title: { type: 'string' },
              content: {},
            },
          },
          right: {
            type: 'object',
            required: ['title', 'content'],
            properties: {
              title: { type: 'string' },
              content: {},
            },
          },
        },
      },
      layout: {
        type: 'grid',
        sections: [
          {
            section_id: 'left-panel',
            title: 'Left',
            component_type: 'text',
            data_path: '$.left',
            config: {
              display: 'panel',
              title_field: 'title',
              content_field: 'content',
            },
            width: 'half',
          },
          {
            section_id: 'right-panel',
            title: 'Right',
            component_type: 'text',
            data_path: '$.right',
            config: {
              display: 'panel',
              title_field: 'title',
              content_field: 'content',
            },
            width: 'half',
          },
        ],
      },
      export_formats: ['json'],
    });
  }

  /**
   * Register a template.
   *
   * @param template - Template to register
   */
  register(template: OutputFormatTemplate): void {
    this.templates.set(
      template.template_id,
      template
    );
  }

  /**
   * Get template by ID.
   *
   * @param templateId - Template identifier
   * @returns Template or undefined if not found
   */
  get(
    templateId: string
  ): OutputFormatTemplate | undefined {
    return this.templates.get(templateId);
  }

  /**
   * List all registered templates.
   *
   * @returns Array of all templates
   */
  list(): OutputFormatTemplate[] {
    return Array.from(this.templates.values());
  }

  /**
   * Check if template exists.
   *
   * @param templateId - Template identifier
   * @returns True if template exists
   */
  has(templateId: string): boolean {
    return this.templates.has(templateId);
  }

  /**
   * Unregister a template (useful for testing).
   *
   * @param templateId - Template identifier
   */
  unregister(templateId: string): void {
    this.templates.delete(templateId);
  }

  /**
   * Clear all templates (useful for testing).
   */
  clearAll(): void {
    this.templates.clear();
  }
}
