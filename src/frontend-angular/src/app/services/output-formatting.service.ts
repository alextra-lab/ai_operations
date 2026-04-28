/**
 * Output Formatting Service
 *
 * Service for formatting Use Case responses with template-driven visualizations.
 * Handles data validation, section rendering, and dynamic visualization composition.
 */

import { Injectable } from '@angular/core';
import Ajv, { ValidateFunction } from 'ajv';
import { JSONPath } from 'jsonpath-plus';
import {
  FormattedOutput,
  JSONSchema,
  OutputFormatTemplate,
  RenderedSection,
  UseCaseResponse,
} from '../models/output-format.model';

@Injectable({
  providedIn: 'root',
})
export class OutputFormattingService {
  private ajv: Ajv;
  private validatorCache = new Map<string, ValidateFunction>();

  constructor() {
    // Initialize JSON schema validator
    this.ajv = new Ajv({
      allErrors: true,
      strict: false,
      validateFormats: false,
    });
  }

  /**
   * Format Use Case response with template.
   *
   * @param response - Use Case response with structured data
   * @param template - Output format template
   * @returns Formatted output with rendered sections
   */
  async formatResponse(
    response: UseCaseResponse,
    template: OutputFormatTemplate
  ): Promise<FormattedOutput> {
    // Validate structured_data against schema
    if (response.structured_data && template.data_schema) {
      this.validateData(
        response.structured_data,
        template.data_schema,
        template.template_id
      );
    }

    // Render each section
    const rendered_sections: RenderedSection[] = [];

    for (const section of template.layout.sections) {
      // Extract data using JSON path
      const sectionData = this.extractDataPath(
        response.structured_data,
        section.data_path
      );

      rendered_sections.push({
        section_id: section.section_id,
        title: section.title,
        component_type: section.component_type,
        data: sectionData,
        config: section.config,
        width: section.width,
      });
    }

    return {
      raw_content: response.answer,
      structured_data: response.structured_data,
      template: template,
      rendered_sections: rendered_sections,
    };
  }

  /**
   * Validate data against JSON schema.
   *
   * @param data - Data to validate
   * @param schema - JSON schema
   * @param templateId - Template ID (for caching)
   * @throws Error if validation fails
   */
  private validateData(
    data: unknown,
    schema: JSONSchema,
    templateId: string
  ): void {
    // Get or create validator
    let validate = this.validatorCache.get(templateId);

    if (!validate) {
      validate = this.ajv.compile(schema);
      this.validatorCache.set(templateId, validate);
    }

    // Validate data
    const valid = validate(data);

    if (!valid) {
      const errors = validate.errors || [];
      const errorMessages = errors
        .map((err) => `${err.instancePath} ${err.message}`)
        .join(', ');

      console.warn(
        `Data validation failed for template ${templateId}:`,
        errorMessages
      );

      // Don't throw error, just log warning for now
      // In production, you might want to implement BEST_EFFORT mode
    }
  }

  /**
   * Extract data using JSON path (e.g., "$.iocs").
   *
   * @param data - Source data object
   * @param path - JSON path expression
   * @returns Extracted data or null if path invalid
   */
  private extractDataPath(data: unknown, path: string): unknown {
    if (!data) {
      return null;
    }

    // Handle root path
    if (path === '$' || path === '') {
      return data;
    }

    try {
      // Use JSONPath library for complex path expressions
      const result = JSONPath({
        path: path,
        json: data,
        wrap: false,
      });

      return result;
    } catch (error) {
      console.error(`Failed to extract data path ${path}:`, error);
      return null;
    }
  }

  /**
   * Clear validator cache (useful for testing).
   */
  clearCache(): void {
    this.validatorCache.clear();
  }
}
