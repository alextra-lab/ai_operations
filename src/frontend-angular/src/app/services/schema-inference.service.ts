/**
 * Schema Inference Service
 *
 * Extracts a minimal JSON Schema from a plain JSON value.
 * Shared utility used by both the Schema Editor ("Import
 * from Example") and the "Refine Schema from Output" feature.
 *
 * @see ADR-063 Amendment 2 — Schema Feedback Loop
 */

import { Injectable } from '@angular/core';

/** Merge strategy when combining schemas. */
export type MergeStrategy = 'replace' | 'merge' | 'cancel';

@Injectable({
  providedIn: 'root',
})
export class SchemaInferenceService {
  /**
   * Infer a minimal JSON Schema from a plain value.
   *
   * @param value - Any JSON-parseable value
   * @returns JSON Schema object
   */
  infer(value: unknown): Record<string, unknown> {
    return this.inferFromValue(value);
  }

  /**
   * Infer schema and return as formatted string.
   *
   * @param value - Any JSON-parseable value
   * @returns Formatted JSON Schema string
   */
  inferAsString(value: unknown): string {
    return JSON.stringify(this.infer(value), null, 2);
  }

  /**
   * Merge an inferred schema into an existing schema,
   * adding any missing properties from inferred that
   * are not in the current schema.
   *
   * @param current - Current schema object
   * @param inferred - Inferred schema object
   * @returns Merged schema object
   */
  merge(
    current: Record<string, unknown>,
    inferred: Record<string, unknown>
  ): Record<string, unknown> {
    const merged = structuredClone(current);

    const currentProps =
      (merged['properties'] ?? {}) as Record<
        string,
        unknown
      >;
    const inferredProps =
      (inferred['properties'] ?? {}) as Record<
        string,
        unknown
      >;

    // Add missing properties from inferred
    for (const key of Object.keys(inferredProps)) {
      if (!(key in currentProps)) {
        currentProps[key] = inferredProps[key];
      }
    }
    merged['properties'] = currentProps;

    // Merge required arrays (union)
    const currentReq =
      (merged['required'] as string[]) ?? [];
    const inferredReq =
      (inferred['required'] as string[]) ?? [];
    const unionReq = [
      ...new Set([...currentReq, ...inferredReq]),
    ];
    merged['required'] = unionReq;

    // Ensure type is object
    merged['type'] = 'object';

    return merged;
  }

  /**
   * Compare two schemas and return differences.
   *
   * @param current - Current schema (may be empty)
   * @param inferred - Inferred schema from output
   * @returns Object with added and matching fields
   */
  diff(
    current: Record<string, unknown> | null,
    inferred: Record<string, unknown>
  ): { added: string[]; matching: string[] } {
    const cProps = Object.keys(
      ((current ?? {})['properties'] ?? {}) as Record<
        string,
        unknown
      >
    );
    const iProps = Object.keys(
      (inferred['properties'] ?? {}) as Record<
        string,
        unknown
      >
    );

    const added = iProps.filter(
      (p) => !cProps.includes(p)
    );
    const matching = iProps.filter((p) =>
      cProps.includes(p)
    );

    return { added, matching };
  }

  /** Recursive schema inference. */
  private inferFromValue(
    value: unknown
  ): Record<string, unknown> {
    if (value === null) {
      return { type: 'null' };
    }
    if (Array.isArray(value)) {
      const itemSchema =
        value.length > 0
          ? this.inferFromValue(value[0])
          : { type: 'object' };
      return { type: 'array', items: itemSchema };
    }
    if (typeof value === 'object') {
      const obj = value as Record<string, unknown>;
      const properties: Record<string, unknown> = {};
      const required: string[] = [];
      for (const key of Object.keys(obj)) {
        required.push(key);
        properties[key] = this.inferFromValue(obj[key]);
      }
      return { type: 'object', required, properties };
    }
    if (typeof value === 'number') {
      return { type: 'number' };
    }
    if (typeof value === 'boolean') {
      return { type: 'boolean' };
    }
    return { type: 'string' };
  }
}
