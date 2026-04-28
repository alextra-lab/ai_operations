/**
 * Domain-Grouped Schema Presets
 *
 * Each preset contains a JSON Schema and an optional
 * recommended visualization template ID.
 * Organized by domain (Security, Legal, HR, etc.) per
 * ADR-066 and ADR-067.
 *
 * Domain expertise is expressed through presets, not
 * template names. Templates are structural/layout-based.
 */

import {
  SchemaPreset,
} from '../components/schema-editor/schema-editor.component';

/** All domain schema presets. */
export const DOMAIN_SCHEMA_PRESETS: SchemaPreset[] = [
  // =========================================================
  // Security
  // =========================================================
  {
    id: 'security-threat-triage',
    label: 'Threat Triage',
    group: 'Security',
    recommendedTemplateId: 'score-table-timeline',
    schema: JSON.stringify(
      {
        type: 'object',
        required: [
          'score', 'confidence', 'items', 'events',
        ],
        properties: {
          score: {
            type: 'string',
            enum: [
              'low', 'medium', 'high', 'critical',
            ],
          },
          confidence: {
            type: 'number',
            minimum: 0,
            maximum: 1,
          },
          items: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                type: { type: 'string' },
                value: { type: 'string' },
                context: { type: 'string' },
              },
            },
          },
          events: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                timestamp: {
                  type: 'string',
                  format: 'date-time',
                },
                description: { type: 'string' },
                severity: { type: 'string' },
              },
            },
          },
        },
      },
      null,
      2
    ),
  },
  {
    id: 'security-ioc-list',
    label: 'IOC List',
    group: 'Security',
    recommendedTemplateId: 'filterable-table',
    schema: JSON.stringify(
      {
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
                first_seen: {
                  type: 'string',
                  format: 'date-time',
                },
              },
            },
          },
        },
      },
      null,
      2
    ),
  },
  {
    id: 'security-incident-summary',
    label: 'Incident Summary',
    group: 'Security',
    recommendedTemplateId: 'score-timeline',
    schema: JSON.stringify(
      {
        type: 'object',
        required: ['events', 'metric', 'status'],
        properties: {
          events: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                timestamp: { type: 'string' },
                description: { type: 'string' },
                severity: { type: 'string' },
              },
            },
          },
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
      null,
      2
    ),
  },
  {
    id: 'security-alert-correlation',
    label: 'Alert Correlation',
    group: 'Security',
    recommendedTemplateId: 'multi-table',
    schema: JSON.stringify(
      {
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
                  items: {
                    type: 'object',
                    properties: {
                      alert_id: { type: 'string' },
                      source: { type: 'string' },
                      severity: { type: 'string' },
                      timestamp: { type: 'string' },
                    },
                  },
                },
              },
            },
          },
        },
      },
      null,
      2
    ),
  },

  // =========================================================
  // Legal
  // =========================================================
  {
    id: 'legal-contract-review',
    label: 'Contract Review',
    group: 'Legal',
    recommendedTemplateId: 'kv-summary',
    schema: JSON.stringify(
      {
        type: 'object',
        required: ['summary'],
        properties: {
          summary: {
            type: 'object',
            properties: {
              contract_type: { type: 'string' },
              parties: { type: 'string' },
              effective_date: { type: 'string' },
              expiry_date: { type: 'string' },
              key_terms: { type: 'string' },
              risk_areas: { type: 'string' },
              recommendation: { type: 'string' },
            },
          },
        },
      },
      null,
      2
    ),
  },
  {
    id: 'legal-compliance-check',
    label: 'Compliance Check',
    group: 'Legal',
    recommendedTemplateId: 'filterable-table',
    schema: JSON.stringify(
      {
        type: 'object',
        required: ['items'],
        properties: {
          items: {
            type: 'array',
            items: {
              type: 'object',
              required: ['requirement', 'status'],
              properties: {
                requirement: { type: 'string' },
                status: {
                  type: 'string',
                  enum: [
                    'compliant',
                    'non_compliant',
                    'partial',
                    'not_applicable',
                  ],
                },
                evidence: { type: 'string' },
                recommendation: { type: 'string' },
              },
            },
          },
        },
      },
      null,
      2
    ),
  },

  // =========================================================
  // IT Operations
  // =========================================================
  {
    id: 'itops-health-check',
    label: 'Health Check',
    group: 'IT Operations',
    recommendedTemplateId: 'bar-chart',
    schema: JSON.stringify(
      {
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
                unit: { type: 'string' },
                status: {
                  type: 'string',
                  enum: [
                    'healthy',
                    'warning',
                    'critical',
                  ],
                },
              },
            },
          },
        },
      },
      null,
      2
    ),
  },
  {
    id: 'itops-change-impact',
    label: 'Change Impact',
    group: 'IT Operations',
    recommendedTemplateId: 'comparison-grid',
    schema: JSON.stringify(
      {
        type: 'object',
        required: ['left', 'right'],
        properties: {
          left: {
            type: 'object',
            required: ['title', 'content'],
            properties: {
              title: { type: 'string' },
              content: { type: 'string' },
            },
          },
          right: {
            type: 'object',
            required: ['title', 'content'],
            properties: {
              title: { type: 'string' },
              content: { type: 'string' },
            },
          },
        },
      },
      null,
      2
    ),
  },

  // =========================================================
  // General
  // =========================================================
  {
    id: 'general-summary-report',
    label: 'Summary Report',
    group: 'General',
    recommendedTemplateId: 'kv-summary',
    schema: JSON.stringify(
      {
        type: 'object',
        required: ['summary'],
        properties: {
          summary: {
            type: 'object',
            additionalProperties: true,
          },
        },
      },
      null,
      2
    ),
  },
  {
    id: 'general-categorized-list',
    label: 'Categorized List',
    group: 'General',
    recommendedTemplateId: 'auto-table',
    schema: JSON.stringify(
      {
        type: 'object',
        required: ['data'],
        properties: {
          data: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                category: { type: 'string' },
                name: { type: 'string' },
                description: { type: 'string' },
                priority: { type: 'string' },
              },
            },
          },
        },
      },
      null,
      2
    ),
  },
  {
    id: 'general-decision-matrix',
    label: 'Decision Matrix',
    group: 'General',
    recommendedTemplateId: 'filterable-table',
    schema: JSON.stringify(
      {
        type: 'object',
        required: ['items'],
        properties: {
          items: {
            type: 'array',
            items: {
              type: 'object',
              required: ['option', 'score'],
              properties: {
                option: { type: 'string' },
                score: { type: 'number' },
                pros: { type: 'string' },
                cons: { type: 'string' },
                recommendation: { type: 'string' },
              },
            },
          },
        },
      },
      null,
      2
    ),
  },
];
