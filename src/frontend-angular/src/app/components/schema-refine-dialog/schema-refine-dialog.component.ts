/**
 * Schema Refine Dialog Component
 *
 * Shows a side-by-side comparison of the current output
 * schema and a schema inferred from actual execution output.
 * The user can Replace, Merge, or Cancel.
 *
 * @see ADR-063 Amendment 2 — Schema Feedback Loop
 */

import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

import {
  MergeStrategy,
  SchemaInferenceService,
} from '../../services/schema-inference.service';

/** Roles that can modify the use case schema (Merge/Replace). */
export const SCHEMA_MODIFY_ROLES = [
  'admin',
  'developer',
  'use_case_admin',
  'corpus_admin',
] as const;

/** Data passed when opening the dialog. */
export interface SchemaRefineDialogData {
  currentSchema: string | null;
  structuredData: Record<string, unknown>;
  useCaseId: string;
  /** If false, Merge and Replace are hidden — only Cancel. Used for non-AIOps-developer users. */
  canModifySchema?: boolean;
}

/** Result returned when the dialog closes. */
export interface SchemaRefineDialogResult {
  strategy: MergeStrategy;
  schema: string | null;
}

@Component({
  selector: 'app-schema-refine-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
  ],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>auto_fix_high</mat-icon>
      Refine Schema from Output
    </h2>
    <mat-dialog-content class="dialog-content">
      <div class="schema-compare">
        <div class="schema-panel">
          <h4>Current Schema</h4>
          <pre class="schema-code">{{
            currentSchemaFormatted || '(none)'
          }}</pre>
        </div>
        <div class="schema-panel">
          <h4>Inferred from Output</h4>
          <pre class="schema-code">{{
            inferredSchemaFormatted
          }}</pre>
        </div>
      </div>
      @if (diff.added.length > 0) {
        <div class="diff-summary">
          <mat-icon>add_circle</mat-icon>
          <span>
            {{ diff.added.length }} new field(s):
            {{ diff.added.join(', ') }}
          </span>
        </div>
      }
      @if (diff.added.length === 0
        && diff.matching.length > 0) {
        <div class="diff-summary match">
          <mat-icon>check_circle</mat-icon>
          <span>
            Schemas already match on all
            {{ diff.matching.length }} fields.
          </span>
        </div>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button
        mat-button
        (click)="close('cancel')"
      >
        Cancel
      </button>
      @if (canModifySchema) {
        <button
          mat-button
          color="accent"
          (click)="close('merge')"
          [disabled]="diff.added.length === 0"
        >
          <mat-icon>merge</mat-icon>
          Merge (add missing)
        </button>
        <button
          mat-flat-button
          color="primary"
          (click)="close('replace')"
        >
          <mat-icon>swap_horiz</mat-icon>
          Replace with inferred
        </button>
      }
    </mat-dialog-actions>
  `,
  styles: [
    `
      /* ADR-012: Material CSS-variable tokens with fallbacks */
      .dialog-content {
        min-width: 600px;
        max-height: 60vh;
      }
      .schema-compare {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
      }
      .schema-panel h4 {
        margin: 0 0 0.5rem;
        font-size: 0.875rem;
        color: var(--mat-sys-outline, #666);
      }
      .schema-code {
        background: var(--mat-sys-surface-variant, #f5f5f5);
        border: 1px solid var(--mat-sys-outline-variant, #e0e0e0);
        border-radius: 6px;
        padding: 0.75rem;
        font-family: var(--mat-font-family-mono, monospace);
        font-size: 0.8rem;
        max-height: 300px;
        overflow: auto;
        white-space: pre-wrap;
        word-break: break-word;
      }
      .diff-summary {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 1rem;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        background: var(--mat-sys-primary-container, #e3f2fd);
        color: var(--mat-sys-on-primary-container, #1565c0);
        font-size: 0.875rem;
      }
      .diff-summary.match {
        background: var(--mat-sys-success-container, #e8f5e9);
        color: var(--mat-sys-on-success-container, #2e7d32);
      }
    `,
  ],
})
export class SchemaRefineDialogComponent {
  currentSchemaFormatted: string;
  inferredSchemaFormatted: string;
  inferredSchemaObj: Record<string, unknown>;
  currentSchemaObj: Record<string, unknown> | null;
  diff: { added: string[]; matching: string[] };
  canModifySchema: boolean;

  constructor(
    private dialogRef: MatDialogRef<
      SchemaRefineDialogComponent,
      SchemaRefineDialogResult
    >,
    @Inject(MAT_DIALOG_DATA)
    public data: SchemaRefineDialogData,
    private schemaInference: SchemaInferenceService
  ) {
    this.canModifySchema = data.canModifySchema !== false;
    this.inferredSchemaObj = this.schemaInference.infer(
      data.structuredData
    );
    this.inferredSchemaFormatted = JSON.stringify(
      this.inferredSchemaObj,
      null,
      2
    );

    this.currentSchemaObj = this.parseCurrentSchema(
      data.currentSchema
    );
    this.currentSchemaFormatted = this.currentSchemaObj
      ? JSON.stringify(this.currentSchemaObj, null, 2)
      : '';

    this.diff = this.schemaInference.diff(
      this.currentSchemaObj,
      this.inferredSchemaObj
    );
  }

  /** Close dialog with chosen strategy. */
  close(strategy: MergeStrategy): void {
    let schema: string | null = null;

    if (strategy === 'replace') {
      schema = this.inferredSchemaFormatted;
    } else if (
      strategy === 'merge'
      && this.currentSchemaObj
    ) {
      const merged = this.schemaInference.merge(
        this.currentSchemaObj,
        this.inferredSchemaObj
      );
      schema = JSON.stringify(merged, null, 2);
    } else if (strategy === 'merge') {
      schema = this.inferredSchemaFormatted;
    }

    this.dialogRef.close({ strategy, schema });
  }

  /** Parse current schema string to object. */
  private parseCurrentSchema(
    text: string | null
  ): Record<string, unknown> | null {
    if (!text?.trim()) return null;
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  }
}
