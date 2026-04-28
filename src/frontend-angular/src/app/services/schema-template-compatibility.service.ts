/**
 * Schema-Template Compatibility Service
 *
 * Validates that a user's output schema matches the
 * selected visualization template's expected data paths.
 * Extracts root keys from template data_paths and checks
 * if schema properties contain matching keys.
 *
 * @see ADR-063 Amendment 1 — Schema-Template Compatibility
 */

import { Injectable } from '@angular/core';
import {
  OutputFormatTemplate,
  OutputSection,
} from '../models/output-format.model';

/** Compatibility status levels. */
export type CompatibilityLevel =
  | 'full'
  | 'partial'
  | 'none'
  | 'no_template'
  | 'no_schema';

/** Single field compatibility result. */
export interface FieldCompatibility {
  path: string;
  found: boolean;
  expectedType?: string;
  actualType?: string;
}

/** Overall compatibility result. */
export interface CompatibilityResult {
  level: CompatibilityLevel;
  message: string;
  fields: FieldCompatibility[];
  matchCount: number;
  totalPaths: number;
}

@Injectable({
  providedIn: 'root',
})
export class SchemaTemplateCompatibilityService {
  /**
   * Validate schema against template data paths.
   *
   * @param schemaText - JSON Schema as string
   * @param template - Selected output template
   * @returns Compatibility result
   */
  validate(
    schemaText: string | null,
    template: OutputFormatTemplate | null
  ): CompatibilityResult {
    if (!template) {
      return this.result('no_template', 'No template selected');
    }
    if (!schemaText?.trim()) {
      return this.result('no_schema', 'No schema defined');
    }

    let schema: Record<string, unknown>;
    try {
      schema = JSON.parse(schemaText);
    } catch {
      return this.result('none', 'Schema is invalid JSON');
    }

    const paths = this.extractDataPaths(template);
    if (paths.length === 0) {
      return this.result(
        'full',
        'Template has no data paths to validate'
      );
    }

    const fields = paths.map((path) =>
      this.checkPath(path, schema)
    );
    const matchCount = fields.filter((f) => f.found).length;

    return this.buildResult(fields, matchCount, paths.length);
  }

  /**
   * Extract root-level JSONPath keys from template sections.
   *
   * Converts `$.items`, `$.metric.severity` etc.
   * to root property names (`items`, `metric`).
   */
  private extractDataPaths(
    template: OutputFormatTemplate
  ): string[] {
    const sections: OutputSection[] =
      template.layout?.sections ?? [];
    const paths: string[] = [];

    for (const section of sections) {
      if (!section.data_path) continue;
      const rootKey = this.rootKeyFromJsonPath(
        section.data_path
      );
      if (rootKey && !paths.includes(rootKey)) {
        paths.push(rootKey);
      }
    }
    return paths;
  }

  /**
   * Extract root property name from JSONPath.
   *
   * `$.items` → `items`
   * `$.metric.severity` → `metric`
   */
  private rootKeyFromJsonPath(jsonPath: string): string | null {
    const match = jsonPath.match(/^\$\.(\w+)/);
    return match ? match[1] : null;
  }

  /**
   * Check if a root key exists in schema properties.
   */
  private checkPath(
    rootKey: string,
    schema: Record<string, unknown>
  ): FieldCompatibility {
    const props = (schema['properties'] ??
      {}) as Record<string, Record<string, unknown>>;
    const prop = props[rootKey];

    if (!prop) {
      return { path: rootKey, found: false };
    }

    return {
      path: rootKey,
      found: true,
      expectedType: undefined,
      actualType: (prop['type'] as string) ?? undefined,
    };
  }

  /** Build final result from field checks. */
  private buildResult(
    fields: FieldCompatibility[],
    matchCount: number,
    totalPaths: number
  ): CompatibilityResult {
    if (matchCount === totalPaths) {
      return {
        level: 'full',
        message: `Schema matches all ${totalPaths} `
          + 'template data paths',
        fields,
        matchCount,
        totalPaths,
      };
    }
    if (matchCount > 0) {
      const missing = totalPaths - matchCount;
      return {
        level: 'partial',
        message: `${matchCount}/${totalPaths} paths matched`
          + ` (${missing} missing)`,
        fields,
        matchCount,
        totalPaths,
      };
    }
    return {
      level: 'none',
      message: 'No template data paths found in schema',
      fields,
      matchCount,
      totalPaths,
    };
  }

  /** Convenience factory for simple results. */
  private result(
    level: CompatibilityLevel,
    message: string
  ): CompatibilityResult {
    return {
      level,
      message,
      fields: [],
      matchCount: 0,
      totalPaths: 0,
    };
  }
}
