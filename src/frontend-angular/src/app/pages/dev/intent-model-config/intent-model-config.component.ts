/**
 * Intent Model Configuration Component
 *
 * Admin UI for configuring intent-to-model defaults (ADR-069).
 */

import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { toLucideIconName } from '../../../shared/icons/material-icon-map';
import {
  AvailableModel,
  IntentConfigRow,
} from './models/intent-model-config.models';
import { IntentModelConfigService } from './services/intent-model-config.service';

@Component({
  selector: 'app-intent-model-config',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatSelectModule,
    MatInputModule,
    MatFormFieldModule,
    MatTableModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatSnackBarModule,
    MatDialogModule,
  ],
  templateUrl: './intent-model-config.component.html',
  styleUrls: ['./intent-model-config.component.scss'],
})
export class IntentModelConfigComponent implements OnInit {
  loading = false;
  intents: IntentConfigRow[] = [];
  availableModels: AvailableModel[] = [];
  displayedColumns = [
    'icon',
    'display_name',
    'current_model',
    'model_details',
    'actions',
  ];

  /**
   * Normalize a Material icon name from the intent summary API to a registered
   * Lucide name via the shared map (with a safe registered fallback so an
   * unmapped value can never throw during render).
   */
  private normalizeIcon(icon: string | null): string {
    return toLucideIconName(icon);
  }

  constructor(
    private intentModelService: IntentModelConfigService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  /**
   * Load intent summaries and available models
   */
  async loadData(): Promise<void> {
    this.loading = true;
    try {
      const [summaries, models] = await Promise.all([
        this.intentModelService.getIntentModelSummary().toPromise(),
        this.intentModelService.getAvailableModels().toPromise(),
      ]);

      this.availableModels = models || [];
      this.intents = (summaries || []).map((summary) => ({
        ...summary,
        icon: this.normalizeIcon(summary.icon),
        isEditing: false,
        selectedModel: summary.current_model_id,
        selectedTemperature: summary.current_temperature,
        notes: null,
      }));
    } catch (error) {
      console.error('Failed to load intent model configuration:', error);
      this.snackBar.open(
        'Failed to load configuration. Please try again.',
        'Close',
        { duration: 5000 }
      );
    } finally {
      this.loading = false;
    }
  }

  /**
   * Start editing mode for an intent
   */
  startEdit(intent: IntentConfigRow): void {
    intent.isEditing = true;
    intent.selectedModel = intent.current_model_id;
    intent.selectedTemperature = intent.current_temperature;
    intent.notes = null;
  }

  /**
   * Cancel editing mode
   */
  cancelEdit(intent: IntentConfigRow): void {
    intent.isEditing = false;
    intent.selectedModel = intent.current_model_id;
    intent.selectedTemperature = intent.current_temperature;
    intent.notes = null;
  }

  /**
   * Save model configuration for an intent
   */
  async saveConfiguration(intent: IntentConfigRow): Promise<void> {
    if (!intent.selectedModel) {
      this.snackBar.open('Please select a model', 'Close', { duration: 3000 });
      return;
    }

    try {
      await this.intentModelService
        .updateIntentModelDefault(intent.intent_code, {
          model_id: intent.selectedModel,
          temperature: intent.selectedTemperature ?? undefined,
          notes: intent.notes,
        })
        .toPromise();

      intent.current_model_id = intent.selectedModel;
      intent.current_temperature = intent.selectedTemperature;
      intent.has_default = true;
      intent.isEditing = false;

      this.snackBar.open(
        `Successfully configured ${intent.display_name}`,
        'Close',
        { duration: 3000 }
      );

      // Refresh cache to apply changes
      await this.refreshCache();
    } catch (error) {
      console.error('Failed to save configuration:', error);
      this.snackBar.open('Failed to save configuration', 'Close', {
        duration: 5000,
      });
    }
  }

  /**
   * View configuration history for an intent
   */
  async viewHistory(intent: IntentConfigRow): Promise<void> {
    try {
      const history = await this.intentModelService
        .getIntentModelHistory(intent.intent_code)
        .toPromise();

      // TODO: Open dialog with history
      console.log('History for', intent.intent_code, history);

      // For now, just show a message
      this.snackBar.open(
        `History loaded: ${history?.length || 0} entries`,
        'Close',
        { duration: 3000 }
      );
    } catch (error) {
      console.error('Failed to load history:', error);
      this.snackBar.open('Failed to load history', 'Close', {
        duration: 5000,
      });
    }
  }

  /**
   * Refresh the model selector cache
   */
  async refreshCache(): Promise<void> {
    try {
      await this.intentModelService.refreshCache().toPromise();
      console.log('Model selector cache refreshed');
    } catch (error) {
      console.error('Failed to refresh cache:', error);
      // Non-critical error, don't show snackbar
    }
  }

  /**
   * Get model details for display
   */
  getModelDetails(modelId: string | null): AvailableModel | null {
    if (!modelId) return null;
    return this.availableModels.find((m) => m.model_id === modelId) || null;
  }

  /**
   * Get model provider for a model ID
   */
  getModelProvider(modelId: string | null): string {
    const model = this.getModelDetails(modelId);
    return model?.provider || 'Unknown';
  }

  /**
   * Get model capabilities for display
   */
  getModelCapabilities(modelId: string | null): string[] {
    const model = this.getModelDetails(modelId);
    return model?.capabilities || [];
  }

  /**
   * Check if all intents have configured defaults
   */
  get allConfigured(): boolean {
    return this.intents.every((i) => i.has_default);
  }

  /**
   * Get count of configured intents
   */
  get configuredCount(): number {
    return this.intents.filter((i) => i.has_default).length;
  }

  /**
   * Get count of unconfigured intents
   */
  get unconfiguredCount(): number {
    return this.intents.filter((i) => !i.has_default).length;
  }
}
