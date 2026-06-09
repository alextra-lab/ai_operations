/**
 * Schema editor with JSON/JSON Schema validation for the Output Contract section.
 * Supports syntax validation, structure validation (Ajv), format, and import from example.
 *
 * @see USE_CASE_AUTHORING_COMPLETE_SPEC.md Phase 4, Feature 4b
 */

import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTabsModule } from '@angular/material/tabs';
import Ajv from 'ajv';
import { LucideAngularModule } from 'lucide-angular';

/** Validation error for the schema editor. */
export interface SchemaValidationError {
  level: 'syntax' | 'schema' | 'compatibility';
  message: string;
}

/** Result of schema validation. */
export interface SchemaValidationResult {
  valid: boolean;
  errors: SchemaValidationError[];
}

/** Preset schema option (e.g. from templates). */
export interface SchemaPreset {
  id: string;
  label: string;
  schema: string;
  /** Optional domain group for grouped display. */
  group?: string;
  /** Optional recommended template ID. */
  recommendedTemplateId?: string;
}

/** Compatibility status passed from parent. */
export interface CompatibilityStatus {
  level: 'full' | 'partial' | 'none' | 'no_template' | 'no_schema';
  message: string;
}

/**
 * Infer a minimal JSON Schema from a plain value (for "Import from Example").
 */
function inferSchemaFromValue(value: unknown): Record<string, unknown> {
  if (value === null) {
    return { type: 'null' };
  }
  if (Array.isArray(value)) {
    const itemSchema =
      value.length > 0 ? inferSchemaFromValue(value[0]) : { type: 'object' };
    return { type: 'array', items: itemSchema };
  }
  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const properties: Record<string, unknown> = {};
    const required: string[] = [];
    for (const key of Object.keys(obj)) {
      required.push(key);
      properties[key] = inferSchemaFromValue(obj[key]);
    }
    return {
      type: 'object',
      required,
      properties,
    };
  }
  if (typeof value === 'number') {
    return { type: 'number' };
  }
  if (typeof value === 'boolean') {
    return { type: 'boolean' };
  }
  return { type: 'string' };
}

@Component({
  selector: 'app-schema-editor',
  templateUrl: './schema-editor.component.html',
  styleUrls: ['./schema-editor.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTabsModule,
  ],
})
export class SchemaEditorComponent implements OnChanges {
  @Input() schema = '';
  @Input() presetSchemas: SchemaPreset[] = [];
  @Input() compatibility: CompatibilityStatus | null = null;
  @Output() schemaChange = new EventEmitter<string>();
  @Output() validationChange = new EventEmitter<SchemaValidationResult>();
  @Output() presetApplied = new EventEmitter<SchemaPreset>();

  validationResult: SchemaValidationResult = {
    valid: true,
    errors: [],
  };
  exampleJson = '';
  activeTabIndex = 0;

  /** Presets grouped by domain (if groups exist). */
  get groupedPresets(): Map<string, SchemaPreset[]> {
    const grouped = new Map<string, SchemaPreset[]>();
    for (const preset of this.presetSchemas) {
      const group = preset.group ?? 'Templates';
      const list = grouped.get(group) ?? [];
      list.push(preset);
      grouped.set(group, list);
    }
    return grouped;
  }

  /** Whether presets have domain groups. */
  get hasGroupedPresets(): boolean {
    return this.presetSchemas.some((p) => !!p.group);
  }

  private ajv = new Ajv({ strict: false, allErrors: true });

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['schema']) {
      this.validateSchema(this.schema);
    }
  }

  onSchemaInput(value: string): void {
    this.schema = value;
    this.validateSchema(value);
    this.schemaChange.emit(value);
  }

  /**
   * Validate schema: syntax (JSON) then structure (JSON Schema).
   */
  private validateSchema(schemaText: string): void {
    if (!schemaText?.trim()) {
      this.validationResult = { valid: true, errors: [] };
      this.validationChange.emit(this.validationResult);
      return;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(schemaText);
    } catch (e) {
      const err = e as Error;
      this.validationResult = {
        valid: false,
        errors: [
          {
            level: 'syntax',
            message: `Invalid JSON: ${err.message}`,
          },
        ],
      };
      this.validationChange.emit(this.validationResult);
      return;
    }

    try {
      this.ajv.compile(parsed as Record<string, unknown>);
      this.validationResult = { valid: true, errors: [] };
    } catch (e) {
      const err = e as Error;
      this.validationResult = {
        valid: false,
        errors: [
          {
            level: 'schema',
            message: `Invalid JSON Schema: ${err.message}`,
          },
        ],
      };
    }
    this.validationChange.emit(this.validationResult);
  }

  formatSchema(): void {
    if (!this.schema?.trim()) return;
    try {
      const parsed = JSON.parse(this.schema);
      this.schema = JSON.stringify(parsed, null, 2);
      this.schemaChange.emit(this.schema);
      this.validationResult = { valid: true, errors: [] };
      this.validationChange.emit(this.validationResult);
    } catch {
      // Keep current state if invalid
    }
  }

  clearSchema(): void {
    this.schema = '';
    this.schemaChange.emit('');
    this.validationResult = { valid: true, errors: [] };
    this.validationChange.emit(this.validationResult);
  }

  /**
   * Generate schema from example JSON and emit.
   */
  generateFromExample(): void {
    const text = this.exampleJson?.trim();
    if (!text) return;
    try {
      const example = JSON.parse(text);
      const schemaObj = inferSchemaFromValue(example);
      this.schema = JSON.stringify(schemaObj, null, 2);
      this.schemaChange.emit(this.schema);
      this.validateSchema(this.schema);
      this.activeTabIndex = 0;
    } catch (e) {
      const err = e as Error;
      this.validationResult = {
        valid: false,
        errors: [
          { level: 'syntax', message: `Example JSON invalid: ${err.message}` },
        ],
      };
      this.validationChange.emit(this.validationResult);
    }
  }

  applyPreset(preset: SchemaPreset): void {
    try {
      const parsed = JSON.parse(preset.schema);
      this.schema = JSON.stringify(parsed, null, 2);
      this.schemaChange.emit(this.schema);
      this.validateSchema(this.schema);
      this.activeTabIndex = 0;
    } catch {
      this.schema = preset.schema;
      this.schemaChange.emit(preset.schema);
      this.validateSchema(preset.schema);
      this.activeTabIndex = 0;
    }
    this.presetApplied.emit(preset);
  }
}
