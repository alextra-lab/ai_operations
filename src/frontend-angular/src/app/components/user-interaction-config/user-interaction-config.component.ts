/**
 * Combined panel for Input Fields and User Prompt Template configuration.
 * Provides tabbed interface with real-time synchronization validation.
 *
 * @see ADR-064-User-Interaction-Combined-Panel.md
 */
import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  InputField,
  UserPromptTemplateConfig,
} from '../../api/models/use-case.models';
import { InputFieldBuilderComponent } from '../input-field-builder/input-field-builder.component';
import { UserPromptTemplateEditorComponent } from '../user-prompt-template-editor/user-prompt-template-editor.component';
import { FieldTemplateSyncStatusComponent } from '../field-template-sync-status/field-template-sync-status.component';

/** Sync status for a single field/variable */
export interface FieldSyncStatus {
  fieldName: string;
  status: 'synced' | 'field_only' | 'template_only';
  message: string;
}

/** Overall validation result */
export interface SyncValidationResult {
  isValid: boolean;
  statuses: FieldSyncStatus[];
  errors: FieldSyncStatus[];
  warnings: FieldSyncStatus[];
}

const VARIABLE_PATTERN = /\{\{(\w+)\}\}/g;

function extractTemplateVariables(template: string): string[] {
  const set = new Set<string>();
  let m: RegExpExecArray | null;
  VARIABLE_PATTERN.lastIndex = 0;
  while ((m = VARIABLE_PATTERN.exec(template)) !== null) {
    set.add(m[1]);
  }
  return Array.from(set);
}

@Component({
  selector: 'app-user-interaction-config',
  templateUrl: './user-interaction-config.component.html',
  styleUrls: ['./user-interaction-config.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatExpansionModule,
    MatIconModule,
    MatTabsModule,
    MatTooltipModule,
    InputFieldBuilderComponent,
    UserPromptTemplateEditorComponent,
    FieldTemplateSyncStatusComponent,
  ],
})
export class UserInteractionConfigComponent implements OnChanges {
  @Input() inputFields: InputField[] = [];
  @Output() inputFieldsChange = new EventEmitter<InputField[]>();

  @Input() userPromptTemplate: UserPromptTemplateConfig | null = null;
  @Output() userPromptTemplateChange =
    new EventEmitter<UserPromptTemplateConfig | null>();

  @Output() validationChange = new EventEmitter<SyncValidationResult>();

  selectedTabIndex = signal(0);

  /** Compute sync status whenever inputs change */
  get syncStatus(): FieldSyncStatus[] {
    return this.computeSyncStatus();
  }

  get validationResult(): SyncValidationResult {
    const statuses = this.syncStatus;
    const errors = statuses.filter((s) => s.status === 'template_only');
    const warnings = statuses.filter((s) => s.status === 'field_only');
    return {
      isValid: errors.length === 0,
      statuses,
      errors,
      warnings,
    };
  }

  get hasErrors(): boolean {
    return this.validationResult.errors.length > 0;
  }

  get hasWarnings(): boolean {
    return this.validationResult.warnings.length > 0;
  }

  get canGenerateTemplate(): boolean {
    return (
      this.inputFields.length > 0 &&
      (!this.userPromptTemplate ||
        !this.userPromptTemplate.template?.trim())
    );
  }

  private computeSyncStatus(): FieldSyncStatus[] {
    const fieldNames = new Set(this.inputFields.map((f) => f.name));
    const templateVars = new Set(
      this.userPromptTemplate?.template
        ? extractTemplateVariables(this.userPromptTemplate.template)
        : []
    );

    const results: FieldSyncStatus[] = [];

    for (const fieldName of fieldNames) {
      if (templateVars.has(fieldName)) {
        results.push({
          fieldName,
          status: 'synced',
          message: 'Defined and used in template',
        });
      } else {
        results.push({
          fieldName,
          status: 'field_only',
          message: 'Defined but NOT used in template',
        });
      }
    }

    for (const varName of templateVars) {
      if (!fieldNames.has(varName)) {
        results.push({
          fieldName: varName,
          status: 'template_only',
          message: 'Used in template but NO field defined',
        });
      }
    }

    return results;
  }

  onInputFieldsChange(fields: InputField[]): void {
    this.inputFieldsChange.emit(fields);
    this.emitValidation();
  }

  onUserPromptTemplateChange(
    template: UserPromptTemplateConfig | null
  ): void {
    this.userPromptTemplateChange.emit(template);
    this.emitValidation();
  }

  ngOnChanges(): void {
    this.emitValidation();
  }

  private emitValidation(): void {
    setTimeout(() => {
      this.validationChange.emit(this.validationResult);
    }, 0);
  }

  /** Generate a starter template from current input fields. */
  generateTemplate(): void {
    if (!this.canGenerateTemplate) return;

    const lines = this.inputFields.map(
      (f) => `${f.label || this.formatLabel(f.name)}: {{${f.name}}}`
    );
    lines.push('');
    lines.push(
      'Please analyze the above information and provide your response.'
    );

    this.userPromptTemplateChange.emit({
      template: lines.join('\n'),
      variables: this.inputFields.map((f) => f.name),
      fallback_mode: 'concatenate',
    });

    this.selectedTabIndex.set(1);
  }

  /** Create a new input field for a template-only variable. */
  createFieldFromVariable(varName: string): void {
    const newField: InputField = {
      name: varName,
      type: 'text',
      label: this.formatLabel(varName),
      description: '',
      required: true,
      placeholder: `Enter ${this.formatLabel(varName).toLowerCase()}`,
    };
    this.inputFieldsChange.emit([...this.inputFields, newField]);
    this.selectedTabIndex.set(0);
  }

  /** Insert a field placeholder into the template. */
  insertFieldIntoTemplate(fieldName: string): void {
    const placeholder = `{{${fieldName}}}`;
    const current = this.userPromptTemplate?.template || '';
    const updated = current + (current ? '\n' : '') + placeholder;

    this.userPromptTemplateChange.emit({
      template: updated,
      variables: extractTemplateVariables(updated),
      fallback_mode: this.userPromptTemplate?.fallback_mode || 'concatenate',
    });
    this.selectedTabIndex.set(1);
  }

  private formatLabel(name: string): string {
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }
}
