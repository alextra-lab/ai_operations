import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';

import { ModelDetailedResponse } from '../../../../api/models/model-registry.models';

export interface ModelEditDialogData {
  modelId: string;
  model?: ModelDetailedResponse;
}

@Component({
  selector: 'app-model-edit-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="model-edit-dialog">
      <h2 mat-dialog-title>
        <mat-icon>edit</mat-icon>
        Edit Model Metadata
      </h2>

      <mat-dialog-content *ngIf="editForm; else loading">
        <form [formGroup]="editForm" class="edit-form">
          <!-- Basic Information -->
          <section class="form-section">
            <h3>Basic Information</h3>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Model ID</mat-label>
              <input matInput formControlName="model_id" readonly />
              <mat-icon matSuffix>lock</mat-icon>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Model Name</mat-label>
              <input matInput formControlName="name" readonly />
              <mat-hint>Cannot be modified</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Description</mat-label>
              <textarea
                matInput
                formControlName="description"
                rows="3"
                placeholder="Model description..."
              ></textarea>
            </mat-form-field>
          </section>

          <!-- Status -->
          <section class="form-section">
            <h3>Status</h3>
            <div class="checkbox-group">
              <mat-checkbox formControlName="is_available">
                <strong>Available</strong>
                <p class="checkbox-hint">Mark model as available for use</p>
              </mat-checkbox>
            </div>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Health Status</mat-label>
              <mat-select formControlName="health_status">
                <mat-option value="healthy">Healthy</mat-option>
                <mat-option value="degraded">Degraded</mat-option>
                <mat-option value="unavailable">Unavailable</mat-option>
                <mat-option value="unknown">Unknown</mat-option>
              </mat-select>
            </mat-form-field>

            <div class="checkbox-group">
              <mat-checkbox formControlName="deprecated">
                <strong>Deprecated</strong>
                <p class="checkbox-hint">
                  Mark model as deprecated (not recommended for new use cases)
                </p>
              </mat-checkbox>
            </div>
          </section>

          <!-- Performance Characteristics -->
          <section class="form-section">
            <h3>Performance (Optional)</h3>
            <div class="form-row">
              <mat-form-field appearance="outline">
                <mat-label>Context Window</mat-label>
                <input
                  matInput
                  type="number"
                  formControlName="context_window"
                  placeholder="128000"
                />
                <mat-hint>Max tokens in context</mat-hint>
              </mat-form-field>

              <mat-form-field appearance="outline">
                <mat-label>Max Output Tokens</mat-label>
                <input
                  matInput
                  type="number"
                  formControlName="max_output_tokens"
                  placeholder="4096"
                />
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline">
                <mat-label>Typical Latency (ms)</mat-label>
                <input
                  matInput
                  type="number"
                  formControlName="typical_latency_ms"
                  placeholder="1500"
                />
              </mat-form-field>

              <mat-form-field appearance="outline">
                <mat-label>Tokens per Second</mat-label>
                <input
                  matInput
                  type="number"
                  step="0.1"
                  formControlName="tokens_per_second"
                  placeholder="50.0"
                />
              </mat-form-field>
            </div>
          </section>

          <!-- Pricing (Optional) -->
          <section class="form-section">
            <h3>Pricing (Optional)</h3>
            <p class="section-hint">
              Prices are in EUR per 1M tokens. Leave empty to use environment
              defaults or per-model pricing history.
            </p>

            <div class="form-row">
              <mat-form-field appearance="outline">
                <mat-label>Input Cost (per 1M)</mat-label>
                <input
                  matInput
                  type="number"
                  step="0.01"
                  formControlName="input_price_per_million"
                  placeholder="0.50"
                />
                <span matPrefix>€&nbsp;</span>
              </mat-form-field>

              <mat-form-field appearance="outline">
                <mat-label>Output Cost (per 1M)</mat-label>
                <input
                  matInput
                  type="number"
                  step="0.01"
                  formControlName="output_price_per_million"
                  placeholder="2.00"
                />
                <span matPrefix>€&nbsp;</span>
              </mat-form-field>
            </div>
          </section>
        </form>
      </mat-dialog-content>

      <ng-template #loading>
        <mat-dialog-content class="loading-content">
          <mat-spinner diameter="50"></mat-spinner>
          <p>Loading model details...</p>
        </mat-dialog-content>
      </ng-template>

      <mat-dialog-actions align="end">
        <button mat-button (click)="cancel()">Cancel</button>
        <button
          mat-raised-button
          color="primary"
          (click)="save()"
          [disabled]="!editForm || editForm.invalid || saving"
        >
          <mat-icon>save</mat-icon>
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [
    `
      .model-edit-dialog {
        min-width: 600px;
        max-width: 800px;
      }

      h2[mat-dialog-title] {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 0 0 16px 0;
      }

      mat-dialog-content {
        max-height: 70vh;
        overflow-y: auto;
      }

      .loading-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px;
        gap: 16px;
      }

      .edit-form {
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .form-section {
        padding-bottom: 24px;
        border-bottom: 1px solid #e0e0e0;
      }

      .form-section:last-child {
        border-bottom: none;
      }

      .form-section h3 {
        font-size: 16px;
        font-weight: 500;
        margin: 0 0 16px 0;
        color: #424242;
      }

      .section-hint {
        margin: -8px 0 16px 0;
        font-size: 13px;
        color: #757575;
        font-style: italic;
      }

      .full-width {
        width: 100%;
      }

      .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }

      .checkbox-group {
        margin-bottom: 16px;
      }

      .checkbox-group mat-checkbox {
        display: block;
      }

      .checkbox-hint {
        margin: 4px 0 0 32px;
        font-size: 12px;
        color: #757575;
      }

      mat-form-field {
        margin-bottom: 8px;
      }

      mat-dialog-actions {
        padding: 16px 0 0 0;
        margin: 0;
      }
    `,
  ],
})
export class ModelEditDialogComponent implements OnInit {
  editForm!: FormGroup;
  saving = false;

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<ModelEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ModelEditDialogData
  ) {}

  ngOnInit(): void {
    this.initializeForm();
  }

  initializeForm(): void {
    if (!this.data.model) {
      return;
    }

    this.editForm = this.fb.group({
      model_id: [{ value: this.data.model.model_id, disabled: true }],
      name: [{ value: this.data.model.name, disabled: true }],
      description: [this.data.model.description || ''],
      is_available: [this.data.model.is_available],
      health_status: [this.data.model.health_status || 'unknown'],
      deprecated: [this.data.model.deprecated || false],
      context_window: [this.data.model.context_window, [Validators.min(0)]],
      max_output_tokens: [
        this.data.model.max_output_tokens,
        [Validators.min(0)],
      ],
      typical_latency_ms: [
        this.data.model.typical_latency_ms,
        [Validators.min(0)],
      ],
      tokens_per_second: [
        this.data.model.tokens_per_second,
        [Validators.min(0)],
      ],
      input_price_per_million: [
        this.data.model.input_price_per_million,
        [Validators.min(0)],
      ],
      output_price_per_million: [
        this.data.model.output_price_per_million,
        [Validators.min(0)],
      ],
    });
  }

  cancel(): void {
    this.dialogRef.close();
  }

  save(): void {
    if (!this.editForm || this.editForm.invalid) {
      return;
    }

    const formValue = this.editForm.getRawValue();

    // Only send changed fields (excluding readonly fields)
    const updates: any = {};

    if (formValue.description !== this.data.model?.description) {
      updates.description = formValue.description;
    }
    if (formValue.is_available !== this.data.model?.is_available) {
      updates.is_available = formValue.is_available;
    }
    if (formValue.health_status !== this.data.model?.health_status) {
      updates.health_status = formValue.health_status;
    }
    if (formValue.deprecated !== this.data.model?.deprecated) {
      updates.deprecated = formValue.deprecated;
    }
    if (formValue.context_window !== this.data.model?.context_window) {
      updates.context_window = formValue.context_window;
    }
    if (formValue.max_output_tokens !== this.data.model?.max_output_tokens) {
      updates.max_output_tokens = formValue.max_output_tokens;
    }
    if (formValue.typical_latency_ms !== this.data.model?.typical_latency_ms) {
      updates.typical_latency_ms = formValue.typical_latency_ms;
    }
    if (formValue.tokens_per_second !== this.data.model?.tokens_per_second) {
      updates.tokens_per_second = formValue.tokens_per_second;
    }
    if (
      formValue.input_price_per_million !==
      this.data.model?.input_price_per_million
    ) {
      updates.input_price_per_million = formValue.input_price_per_million;
    }
    if (
      formValue.output_price_per_million !==
      this.data.model?.output_price_per_million
    ) {
      updates.output_price_per_million = formValue.output_price_per_million;
    }

    this.dialogRef.close({
      action: 'save',
      modelId: this.data.modelId,
      updates,
    });
  }
}
