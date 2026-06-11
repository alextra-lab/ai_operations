/**
 * Dynamic Form Test Component
 *
 * Test page for the P3-F1 Dynamic Form Generator implementation.
 * Fetches use case configs from backend and renders dynamic forms.
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import {
  ExecutionResponse,
  UseCase,
  UseCaseConfig,
} from '../../api/models/use-case.models';
import { UseCaseExecutionService } from '../../api/services/use-case-execution.service';
import { UseCaseService } from '../../api/services/use-case.service';
import { ExecutionMetricsComponent } from '../../components/execution-metrics/execution-metrics.component';
import { LLMContentRendererComponent } from '../../components/llm-content-renderer/llm-content-renderer.component';
import { SourceCitationComponent } from '../../components/source-citation/source-citation.component';
import { DynamicFormComponent } from '../../features/dynamic-forms/components/dynamic-form.component';

@Component({
  selector: 'app-dynamic-form-test',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatSelectModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatChipsModule,
    DynamicFormComponent,
    ExecutionMetricsComponent,
    SourceCitationComponent,
    LLMContentRendererComponent,
  ],
  template: `
    <div class="test-container">
      <mat-card class="header-card">
        <mat-card-header>
          <mat-card-title>P3-F1: Dynamic Form Generator Test</mat-card-title>
          <mat-card-subtitle
            >Testing template-driven form generation from backend
            configs</mat-card-subtitle
          >
        </mat-card-header>
      </mat-card>

      <!-- Use Case Selector -->
      <mat-card class="selector-card">
        <mat-card-content>
          <div class="selector-content">
            <label for="use-case-select" class="selector-label"
              >Select Use Case:</label
            >
            <mat-select
              [(ngModel)]="selectedUseCaseId"
              (selectionChange)="onUseCaseSelected()"
              placeholder="Choose a use case..."
              class="use-case-select"
            >
              <mat-option *ngFor="let uc of useCases" [value]="uc.use_case_id">
                {{ uc.name }} ({{ uc.category }})
              </mat-option>
            </mat-select>
          </div>

          <!-- Loading Indicator -->
          @if (isLoadingConfig) {
            <div class="loading-indicator">
              <mat-spinner diameter="30"></mat-spinner>
              <span>Loading use case configuration...</span>
            </div>
          }

          <!-- Config Display -->
          @if (currentConfig && !isLoadingConfig) {
            <div class="config-info">
              <h4>Configuration Loaded:</h4>
              <div class="config-chips">
                <mat-chip
                  >{{
                    currentConfig.template_config.input_fields.length
                  }}
                  fields</mat-chip
                >
                <mat-chip>{{ currentConfig.intent_type }}</mat-chip>
                <mat-chip>{{
                  currentConfig.template_config.output_format
                }}</mat-chip>
              </div>
            </div>
          }
        </mat-card-content>
      </mat-card>

      <!-- Dynamic Form -->
      @if (currentConfig && !isLoadingConfig) {
        <mat-card class="form-card">
          <mat-card-content>
            <app-dynamic-form
              [templateConfig]="currentConfig.template_config"
              [title]="currentConfig.name"
              [description]="currentConfig.description"
              submitButtonText="Execute Use Case"
              (formSubmit)="onFormSubmit($event)"
              (formChange)="onFormChange($event)"
            >
            </app-dynamic-form>
          </mat-card-content>
        </mat-card>
      }

      <!-- Execution Results -->
      @if (executionResult) {
        <mat-card class="results-card">
          <mat-card-header>
            <mat-card-title>Execution Results</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <!-- Response -->
            <div class="result-section">
              <h3>Response</h3>
              <app-llm-content-renderer [content]="executionResult.response">
              </app-llm-content-renderer>
            </div>

            <mat-divider></mat-divider>

            <!-- Metrics -->
            <div class="result-section">
              <h3>Execution Metrics</h3>
              <app-execution-metrics [metrics]="executionResult.metrics">
              </app-execution-metrics>
            </div>

            <mat-divider></mat-divider>

            <!-- Sources -->
            @if (
              executionResult.sources && executionResult.sources.length > 0
            ) {
              <div class="result-section">
                <h3>
                  Retrieved Sources ({{ executionResult.sources.length }})
                </h3>
                <app-source-citation
                  *ngFor="let source of executionResult.sources"
                  [source]="source"
                >
                </app-source-citation>
              </div>
            }
          </mat-card-content>
        </mat-card>
      }

      <!-- Form Values Debug (Development Only) -->
      @if (currentFormValues && showDebug) {
        <mat-card class="debug-card">
          <mat-card-header>
            <mat-card-title>Debug: Form Values</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <pre>{{ currentFormValues | json }}</pre>
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [
    `
      .test-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
      }

      .header-card {
        margin-bottom: 2rem;
      }

      .selector-card {
        margin-bottom: 2rem;
      }

      .selector-content {
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }

      .selector-label {
        font-weight: 500;
        font-size: 1rem;
      }

      .use-case-select {
        width: 100%;
      }

      .loading-indicator {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem;
        margin-top: 1rem;
        background-color: #f5f5f5;
        border-radius: 4px;
      }

      .config-info {
        margin-top: 1rem;
        padding: 1rem;
        background-color: #e8f5e9;
        border-radius: 4px;
      }

      .config-info h4 {
        margin: 0 0 0.5rem 0;
        color: #2e7d32;
      }

      .config-chips {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
      }

      .form-card {
        margin-bottom: 2rem;
      }

      .results-card {
        margin-bottom: 2rem;
      }

      .result-section {
        margin: 1.5rem 0;
      }

      .result-section h3 {
        margin-bottom: 1rem;
        color: #1976d2;
      }

      .debug-card {
        margin-bottom: 2rem;
        background-color: #fff3e0;
      }

      .debug-card pre {
        background-color: #424242;
        color: #f5f5f5;
        padding: 1rem;
        border-radius: 4px;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.875rem;
      }

      mat-divider {
        margin: 1.5rem 0;
      }
    `,
  ],
})
export class DynamicFormTestComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  useCases: UseCase[] = [];
  selectedUseCaseId: string | null = null;
  currentConfig: UseCaseConfig | null = null;
  isLoadingConfig = false;
  currentFormValues: any = null;
  executionResult: ExecutionResponse | null = null;
  showDebug = true; // Set to false in production

  constructor(
    private useCaseService: UseCaseService,
    private executionService: UseCaseExecutionService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadUseCases();
  }

  /**
   * Load available use cases from backend
   */
  loadUseCases(): void {
    this.useCaseService.getAvailableUseCases().subscribe({
      next: (response) => {
        // Response is already an array or has use_cases property
        this.useCases = Array.isArray(response)
          ? response
          : (response as any).use_cases || [];
        this.showSuccess(`Loaded ${this.useCases.length} use cases`);
      },
      error: (error) => {
        console.error('Error loading use cases:', error);
        this.showError('Failed to load use cases');
      },
    });
  }

  /**
   * Load use case configuration when selected
   */
  onUseCaseSelected(): void {
    if (!this.selectedUseCaseId) {
      return;
    }

    this.isLoadingConfig = true;
    this.currentConfig = null;
    this.executionResult = null;

    this.useCaseService.getUseCaseConfig(this.selectedUseCaseId).subscribe({
      next: (config) => {
        this.currentConfig = config;
        this.isLoadingConfig = false;
        queueMicrotask(() => this.cdr.detectChanges());
        this.showSuccess(`Loaded config for: ${config.name}`);
      },
      error: (error) => {
        console.error('Error loading use case config:', error);
        this.isLoadingConfig = false;
        queueMicrotask(() => this.cdr.detectChanges());
        this.showError('Failed to load use case configuration');
      },
    });
  }

  /**
   * Handle form submission
   */
  onFormSubmit(formValues: Record<string, any>): void {
    this.currentFormValues = formValues;

    if (!this.selectedUseCaseId) {
      this.showError('No use case selected');
      return;
    }

    // Execute the use case
    this.executionService
      .executeUseCase({
        use_case_id: this.selectedUseCaseId,
        inputs: formValues,
      })
      .subscribe({
        next: (result) => {
          this.executionResult = result;
          this.showSuccess('Execution completed successfully');
        },
        error: (error) => {
          console.error('Execution error:', error);
          this.showError(
            'Execution failed: ' + (error.message || 'Unknown error')
          );
        },
      });
  }

  /**
   * Handle form changes
   */
  onFormChange(formValues: Record<string, any>): void {
    this.currentFormValues = formValues;
  }

  /**
   * Show success message
   */
  private showSuccess(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 3000,
      panelClass: ['success-snackbar'],
    });
  }

  /**
   * Show error message
   */
  private showError(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar'],
    });
  }
}
