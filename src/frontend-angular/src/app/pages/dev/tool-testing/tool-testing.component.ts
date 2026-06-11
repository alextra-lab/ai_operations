/**
 * Tool Testing Component
 *
 * T6-F4: Developer/admin interface for testing MCP tools.
 * Allows executing test calls and validating parameters.
 * Follows ADR-012 Layered Page Layout Pattern.
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, WritableSignal, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';

import { LucideAngularModule } from 'lucide-angular';
import {
  TestExecutionResult,
  ToolTestingService,
} from '../../../api/services/tool-testing.service';
import { ToolAdminService } from '../../admin/tool-management/services/tool-admin.service';
import { TestResultViewerComponent } from './components/test-result-viewer/test-result-viewer.component';
import {
  formatDuration,
  formatTimestamp,
  generateTestId,
  JsonValidationStatus,
  TestHistoryEntry,
  ToolOption,
} from './models/tool-testing.models';

@Component({
  selector: 'app-tool-testing',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTooltipModule,
    TestResultViewerComponent,
  ],
  templateUrl: './tool-testing.component.html',
  styleUrls: ['./tool-testing.component.scss'],
})
export class ToolTestingComponent implements OnInit, OnDestroy {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  private destroy$ = new Subject<void>();

  // Injected services
  private readonly testingService = inject(ToolTestingService);
  private readonly toolAdminService = inject(ToolAdminService);
  private readonly snackBar = inject(MatSnackBar);

  // Tool selection state
  tools: WritableSignal<ToolOption[]> = signal([]);
  selectedTool: WritableSignal<ToolOption | null> = signal(null);
  toolName = '';

  // Parameters state
  parametersJson = '{\n  \n}';
  jsonValidationStatus: JsonValidationStatus = 'valid';
  jsonError = '';

  // Execution state
  isLoadingTools = true;
  isExecuting = false;
  isValidating = false;

  // Results state
  currentResult: WritableSignal<TestExecutionResult | null> = signal(null);
  validationMessage: WritableSignal<string | null> = signal(null);
  validationSuccess: WritableSignal<boolean | null> = signal(null);

  // History state
  testHistory: WritableSignal<TestHistoryEntry[]> = signal([]);
  selectedHistoryEntry: WritableSignal<TestHistoryEntry | null> = signal(null);
  maxHistory = 10;

  ngOnInit(): void {
    this.loadTools();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Load available tools for selection
   */
  loadTools(): void {
    this.isLoadingTools = true;

    this.toolAdminService
      .listTools()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (tools) => {
          const toolOptions: ToolOption[] = tools
            .filter((t) => t.is_enabled)
            .map((t) => ({
              id: t.id,
              tool_id: t.tool_id,
              name: t.name,
              description: t.description ?? null,
              category: t.category,
              is_enabled: t.is_enabled,
              is_healthy: t.is_healthy,
            }));

          this.tools.set(toolOptions);
          this.isLoadingTools = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          console.error('Error loading tools:', error);
          this.snackBar.open('Failed to load tools', 'Close', {
            duration: 5000,
          });
          this.isLoadingTools = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  /**
   * Handle tool selection change
   */
  onToolSelect(tool: ToolOption): void {
    this.selectedTool.set(tool);
    this.toolName = tool.tool_id;
    this.currentResult.set(null);
    this.validationMessage.set(null);
    this.validationSuccess.set(null);
    this.selectedHistoryEntry.set(null);

    // Pre-fill with example if schema exists
    if (tool.parameters_schema) {
      const example = this.generateExampleFromSchema(tool.parameters_schema);
      this.parametersJson = JSON.stringify(example, null, 2);
    } else {
      this.parametersJson = '{\n  \n}';
    }

    this.validateJson();
  }

  /**
   * Generate example parameters from JSON schema
   */
  generateExampleFromSchema(
    schema: Record<string, unknown>
  ): Record<string, unknown> {
    const example: Record<string, unknown> = {};
    const properties = schema['properties'] as Record<string, unknown>;

    if (!properties) {
      return example;
    }

    for (const [key, prop] of Object.entries(properties)) {
      const propDef = prop as Record<string, unknown>;
      const type = propDef['type'] as string;

      switch (type) {
        case 'string':
          example[key] = propDef['default'] ?? 'example_value';
          break;
        case 'number':
        case 'integer':
          example[key] = propDef['default'] ?? 10;
          break;
        case 'boolean':
          example[key] = propDef['default'] ?? true;
          break;
        case 'array':
          example[key] = propDef['default'] ?? [];
          break;
        case 'object':
          example[key] = propDef['default'] ?? {};
          break;
        default:
          example[key] = null;
      }
    }

    return example;
  }

  /**
   * Validate JSON in the editor
   */
  validateJson(): void {
    const trimmed = this.parametersJson.trim();

    if (!trimmed || trimmed === '{}') {
      this.jsonValidationStatus = 'empty';
      this.jsonError = '';
      return;
    }

    try {
      JSON.parse(this.parametersJson);
      this.jsonValidationStatus = 'valid';
      this.jsonError = '';
    } catch {
      this.jsonValidationStatus = 'invalid';
      this.jsonError = 'Invalid JSON syntax';
    }
  }

  /**
   * Handle parameter input change
   */
  onParametersChange(): void {
    this.validateJson();
  }

  /**
   * Clear the parameters editor
   */
  clearParameters(): void {
    this.parametersJson = '{\n  \n}';
    this.jsonValidationStatus = 'empty';
    this.jsonError = '';
  }

  /**
   * Load example parameters
   */
  loadExample(): void {
    const tool = this.selectedTool();
    if (tool?.parameters_schema) {
      const example = this.generateExampleFromSchema(tool.parameters_schema);
      this.parametersJson = JSON.stringify(example, null, 2);
    } else {
      this.parametersJson = JSON.stringify(
        { query: 'example', limit: 10 },
        null,
        2
      );
    }
    this.validateJson();
  }

  /**
   * Validate parameters against schema
   */
  validateParameters(): void {
    const tool = this.selectedTool();
    if (!tool || this.jsonValidationStatus === 'invalid') {
      return;
    }

    this.isValidating = true;
    this.validationMessage.set(null);
    this.validationSuccess.set(null);

    let parameters: Record<string, unknown> = {};
    try {
      parameters = JSON.parse(this.parametersJson);
    } catch {
      this.snackBar.open('Invalid JSON', 'Close', { duration: 3000 });
      this.isValidating = false;
      queueMicrotask(() => this.cdr.detectChanges());
      return;
    }

    this.testingService
      .validateParameters({ tool_id: tool.id, parameters })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.isValidating = false;
          queueMicrotask(() => this.cdr.detectChanges());
          this.validationSuccess.set(result.valid);

          if (result.valid) {
            const msg = result.message || 'Parameters are valid';
            this.validationMessage.set(msg);
            this.snackBar.open(msg, 'Close', { duration: 3000 });
          } else {
            const msg = result.error || 'Validation failed';
            this.validationMessage.set(msg);
            this.snackBar.open(`Validation failed: ${msg}`, 'Close', {
              duration: 5000,
            });
          }
        },
        error: (error) => {
          this.isValidating = false;
          queueMicrotask(() => this.cdr.detectChanges());
          const msg = error.error?.detail || 'Validation request failed';
          this.validationMessage.set(msg);
          this.validationSuccess.set(false);
          this.snackBar.open(msg, 'Close', { duration: 5000 });
        },
      });
  }

  /**
   * Execute test call
   */
  executeTest(): void {
    const tool = this.selectedTool();
    if (!tool || this.jsonValidationStatus === 'invalid') {
      return;
    }

    this.isExecuting = true;
    this.currentResult.set(null);
    this.selectedHistoryEntry.set(null);

    let parameters: Record<string, unknown> = {};
    try {
      parameters = JSON.parse(this.parametersJson);
    } catch {
      this.snackBar.open('Invalid JSON', 'Close', { duration: 3000 });
      this.isExecuting = false;
      queueMicrotask(() => this.cdr.detectChanges());
      return;
    }

    const testToolName = this.toolName || tool.tool_id;

    this.testingService
      .executeTest({
        tool_id: tool.id,
        tool_name: testToolName,
        parameters,
      })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.isExecuting = false;
          queueMicrotask(() => this.cdr.detectChanges());
          this.currentResult.set(result);

          // Add to history
          this.addToHistory({
            id: generateTestId(),
            tool_id: tool.id,
            tool_name: testToolName,
            tool_display_name: tool.name,
            parameters,
            result,
            timestamp: new Date(),
          });

          if (result.success) {
            this.snackBar.open('Test executed successfully', 'Close', {
              duration: 3000,
            });
          } else {
            this.snackBar.open(
              `Test failed: ${result.error || 'Unknown error'}`,
              'Close',
              { duration: 5000 }
            );
          }
        },
        error: (error) => {
          this.isExecuting = false;
          queueMicrotask(() => this.cdr.detectChanges());
          const errorMsg = error.error?.detail || 'Test execution failed';
          this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
        },
      });
  }

  /**
   * Add entry to test history
   */
  private addToHistory(entry: TestHistoryEntry): void {
    const current = this.testHistory();
    const updated = [entry, ...current];

    if (updated.length > this.maxHistory) {
      updated.splice(this.maxHistory);
    }

    this.testHistory.set(updated);
  }

  /**
   * View a history entry
   */
  viewHistoryEntry(entry: TestHistoryEntry): void {
    this.selectedHistoryEntry.set(entry);
    this.currentResult.set(entry.result);

    // Also update the parameter editor to show what was used
    this.parametersJson = JSON.stringify(entry.parameters, null, 2);
    this.validateJson();
  }

  /**
   * Clear test history
   */
  clearHistory(): void {
    this.testHistory.set([]);
    this.selectedHistoryEntry.set(null);
    this.snackBar.open('History cleared', 'Close', { duration: 2000 });
  }

  /**
   * Check if execute button should be disabled
   */
  get isExecuteDisabled(): boolean {
    return (
      !this.selectedTool() ||
      this.jsonValidationStatus === 'invalid' ||
      this.isExecuting
    );
  }

  /**
   * Check if validate button should be disabled
   */
  get isValidateDisabled(): boolean {
    return (
      !this.selectedTool() ||
      this.jsonValidationStatus === 'invalid' ||
      this.isValidating
    );
  }

  /**
   * Format duration for display
   */
  formatDuration(ms: number): string {
    return formatDuration(ms);
  }

  /**
   * Format timestamp for display
   */
  formatTimestamp(date: Date): string {
    return formatTimestamp(date);
  }

  /**
   * Get status icon for history entry
   */
  getStatusIcon(entry: TestHistoryEntry): string {
    return entry.result.success ? 'circle-check' : 'circle-alert';
  }

  /**
   * Get status class for history entry
   */
  getStatusClass(entry: TestHistoryEntry): string {
    return entry.result.success ? 'success' : 'error';
  }
}
