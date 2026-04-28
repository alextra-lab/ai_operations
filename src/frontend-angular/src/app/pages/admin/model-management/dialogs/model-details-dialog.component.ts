import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ModelDetailedResponse } from '../../../../api/models/model-registry.models';

export interface ModelDetailsDialogData {
  modelId: string;
  model?: ModelDetailedResponse;
}

@Component({
  selector: 'app-model-details-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  template: `
    <div class="model-details-dialog">
      <h2 mat-dialog-title>
        <mat-icon>psychology</mat-icon>
        Model Details
      </h2>

      <mat-dialog-content *ngIf="data.model; else loading">
        <!-- Basic Information -->
        <section class="detail-section">
          <h3>Basic Information</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Model ID</label>
              <span class="value monospace">{{ data.model.model_id }}</span>
            </div>
            <div class="detail-item">
              <label>Name</label>
              <span class="value">{{ data.model.name }}</span>
            </div>
            <div class="detail-item">
              <label>Provider</label>
              <mat-chip>{{ data.model.provider }}</mat-chip>
            </div>
            <div class="detail-item">
              <label>Type</label>
              <mat-chip>{{ data.model.model_type }}</mat-chip>
            </div>
            <div class="detail-item">
              <label>Version</label>
              <span class="value">{{ data.model.version || 'N/A' }}</span>
            </div>
            <div class="detail-item">
              <label>Status</label>
              <mat-chip
                [class]="data.model.is_available ? 'available' : 'unavailable'"
              >
                <mat-icon>{{
                  data.model.is_available ? 'check_circle' : 'cancel'
                }}</mat-icon>
                {{ data.model.is_available ? 'Available' : 'Unavailable' }}
              </mat-chip>
            </div>
          </div>
          <div class="detail-item full-width" *ngIf="data.model.description">
            <label>Description</label>
            <p class="description">{{ data.model.description }}</p>
          </div>
        </section>

        <!-- Capabilities -->
        <section class="detail-section">
          <h3>Capabilities</h3>
          <div class="capabilities-grid">
            <div
              class="capability-item"
              [class.enabled]="data.model.capabilities.supports_tools"
            >
              <mat-icon>{{
                data.model.capabilities.supports_tools
                  ? 'check_circle'
                  : 'cancel'
              }}</mat-icon>
              <span>Tools/Functions</span>
            </div>
            <div
              class="capability-item"
              [class.enabled]="data.model.capabilities.supports_vision"
            >
              <mat-icon>{{
                data.model.capabilities.supports_vision
                  ? 'check_circle'
                  : 'cancel'
              }}</mat-icon>
              <span>Vision</span>
            </div>
            <div
              class="capability-item"
              [class.enabled]="data.model.capabilities.supports_audio"
            >
              <mat-icon>{{
                data.model.capabilities.supports_audio
                  ? 'check_circle'
                  : 'cancel'
              }}</mat-icon>
              <span>Audio</span>
            </div>
            <div
              class="capability-item"
              [class.enabled]="data.model.capabilities.supports_streaming"
            >
              <mat-icon>{{
                data.model.capabilities.supports_streaming
                  ? 'check_circle'
                  : 'cancel'
              }}</mat-icon>
              <span>Streaming</span>
            </div>
            <div
              class="capability-item"
              [class.enabled]="data.model.capabilities.supports_json_mode"
            >
              <mat-icon>{{
                data.model.capabilities.supports_json_mode
                  ? 'check_circle'
                  : 'cancel'
              }}</mat-icon>
              <span>JSON Mode</span>
            </div>
            <div
              class="capability-item"
              [class.enabled]="data.model.is_reasoning_model"
            >
              <mat-icon>{{
                data.model.is_reasoning_model ? 'check_circle' : 'cancel'
              }}</mat-icon>
              <span>Reasoning</span>
            </div>
          </div>
        </section>

        <!-- Performance Characteristics -->
        <section class="detail-section">
          <h3>Performance</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Context Window</label>
              <span class="value"
                >{{
                  formatNumber(data.model.performance.context_window)
                }}
                tokens</span
              >
            </div>
            <div class="detail-item">
              <label>Max Input Tokens</label>
              <span class="value">{{
                formatNumber(data.model.performance.max_input_tokens)
              }}</span>
            </div>
            <div class="detail-item">
              <label>Max Output Tokens</label>
              <span class="value">{{
                formatNumber(data.model.performance.max_output_tokens)
              }}</span>
            </div>
            <div
              class="detail-item"
              *ngIf="data.model.performance.typical_latency_ms"
            >
              <label>Typical Latency</label>
              <span class="value"
                >{{ data.model.performance.typical_latency_ms }}ms</span
              >
            </div>
            <div
              class="detail-item"
              *ngIf="data.model.performance.tokens_per_second"
            >
              <label>Speed</label>
              <span class="value"
                >{{
                  data.model.performance.tokens_per_second.toFixed(1)
                }}
                tokens/sec</span
              >
            </div>
          </div>
        </section>

        <!-- Pricing -->
        <section class="detail-section" *ngIf="data.model.pricing">
          <h3>Pricing</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Input Cost</label>
              <span class="value"
                >€{{
                  data.model.pricing.input_price_per_million?.toFixed(4) ||
                    'N/A'
                }}
                / 1M tokens</span
              >
            </div>
            <div class="detail-item">
              <label>Output Cost</label>
              <span class="value"
                >€{{
                  data.model.pricing.output_price_per_million?.toFixed(4) ||
                    'N/A'
                }}
                / 1M tokens</span
              >
            </div>
            <div
              class="detail-item"
              *ngIf="data.model.estimated_cost_per_1k_tokens"
            >
              <label>Estimated Cost (1K tokens)</label>
              <span class="value"
                >€{{ data.model.estimated_cost_per_1k_tokens.toFixed(6) }}</span
              >
            </div>
          </div>
        </section>

        <!-- Configuration -->
        <section class="detail-section">
          <h3>Configuration</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Default Temperature</label>
              <span class="value">{{ data.model.default_temperature }}</span>
            </div>
            <div class="detail-item">
              <label>Temperature Range</label>
              <span class="value"
                >{{ data.model.temperature_range.min }} -
                {{ data.model.temperature_range.max }}</span
              >
            </div>
            <div
              class="detail-item full-width"
              *ngIf="data.model.recommended_use_cases?.length"
            >
              <label>Recommended Use Cases</label>
              <div class="use-cases">
                <mat-chip
                  *ngFor="let useCase of data.model.recommended_use_cases"
                >
                  {{ useCase }}
                </mat-chip>
              </div>
            </div>
          </div>
        </section>

        <!-- Metadata -->
        <section class="detail-section">
          <h3>Metadata</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <label>Created</label>
              <span class="value">{{ formatDate(data.model.created_at) }}</span>
            </div>
            <div class="detail-item">
              <label>Last Updated</label>
              <span class="value">{{ formatDate(data.model.updated_at) }}</span>
            </div>
            <div class="detail-item">
              <label>Health Status</label>
              <span class="value">{{ data.model.health_status }}</span>
            </div>
          </div>
        </section>
      </mat-dialog-content>

      <ng-template #loading>
        <mat-dialog-content class="loading-content">
          <mat-spinner diameter="50"></mat-spinner>
          <p>Loading model details...</p>
        </mat-dialog-content>
      </ng-template>

      <mat-dialog-actions align="end">
        <button mat-button (click)="close()">Close</button>
        <button mat-raised-button color="primary" (click)="openEdit()">
          <mat-icon>edit</mat-icon>
          Edit Model
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [
    `
      .model-details-dialog {
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

      .detail-section {
        margin-bottom: 24px;
        padding-bottom: 24px;
        border-bottom: 1px solid #e0e0e0;
      }

      .detail-section:last-child {
        border-bottom: none;
      }

      .detail-section h3 {
        font-size: 16px;
        font-weight: 500;
        margin: 0 0 16px 0;
        color: #424242;
      }

      .detail-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 16px;
      }

      .detail-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .detail-item.full-width {
        grid-column: 1 / -1;
      }

      .detail-item label {
        font-size: 12px;
        font-weight: 500;
        color: #757575;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .detail-item .value {
        font-size: 14px;
        color: #212121;
      }

      .detail-item .value.monospace {
        font-family: 'Courier New', monospace;
      }

      .description {
        margin: 0;
        font-size: 14px;
        line-height: 1.5;
        color: #424242;
      }

      .capabilities-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
      }

      .capability-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 4px;
        background: #f5f5f5;
        color: #757575;
      }

      .capability-item.enabled {
        background: #e8f5e9;
        color: #2e7d32;
      }

      .capability-item mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }

      .use-cases {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      mat-chip {
        font-size: 12px;
      }

      mat-chip.available {
        background: #e8f5e9;
        color: #2e7d32;
      }

      mat-chip.unavailable {
        background: #ffebee;
        color: #c62828;
      }

      mat-dialog-actions {
        padding: 16px 0 0 0;
        margin: 0;
      }
    `,
  ],
})
export class ModelDetailsDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ModelDetailsDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ModelDetailsDialogData
  ) {}

  formatNumber(num?: number): string {
    if (!num && num !== 0) return 'N/A';
    return num.toLocaleString();
  }

  formatDate(date?: string): string {
    if (!date) return 'N/A';
    return new Date(date).toLocaleString();
  }

  close(): void {
    this.dialogRef.close();
  }

  openEdit(): void {
    this.dialogRef.close({ action: 'edit', modelId: this.data.modelId });
  }
}
