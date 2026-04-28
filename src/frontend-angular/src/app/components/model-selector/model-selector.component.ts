import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

// Angular Material imports
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';

import {
  Model,
  ModelDetailedResponse,
} from '../../api/models/model-registry.models';
import { ModelRegistryService } from '../../api/services/model-registry.service';

@Component({
  selector: 'app-model-selector',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    MatCardModule,
  ],
  templateUrl: './model-selector.component.html',
  styleUrls: ['./model-selector.component.scss'],
})
export class ModelSelectorComponent implements OnInit {
  @Input() useCaseType?: string;
  @Input() preselectedModelId?: string;
  @Output() modelSelected = new EventEmitter<ModelDetailedResponse>();

  models: Model[] = [];
  selectedModelId?: string;
  selectedModel?: ModelDetailedResponse;
  loading = false;

  constructor(private modelRegistryService: ModelRegistryService) {}

  ngOnInit(): void {
    this.loadModels();
  }

  // =========================================================================
  // Data Loading
  // =========================================================================

  loadModels(): void {
    this.loading = true;
    this.modelRegistryService
      .listModels(undefined, 'llm', true, false, false, 1, 100)
      .subscribe({
        next: (response) => {
          this.models = response.models;
          if (this.preselectedModelId) {
            this.selectedModelId = this.preselectedModelId;
            this.loadSelectedModel();
          }
          this.loading = false;
        },
        error: (error) => {
          console.error('Error loading models:', error);
          this.loading = false;
        },
      });
  }

  loadSelectedModel(): void {
    if (!this.selectedModelId) return;

    this.modelRegistryService.getModel(this.selectedModelId).subscribe({
      next: (model) => {
        this.selectedModel = model;
        this.modelSelected.emit(model);
      },
      error: (error) => {
        console.error('Error loading model details:', error);
      },
    });
  }

  // =========================================================================
  // Event Handlers
  // =========================================================================

  onModelChange(modelId: string): void {
    this.selectedModelId = modelId;
    this.loadSelectedModel();
  }

  // =========================================================================
  // Utility Methods
  // =========================================================================

  formatNumber(num?: number): string {
    if (!num) return 'N/A';
    return num.toLocaleString();
  }

  formatCost(cost?: number): string {
    if (!cost) return 'N/A';
    return `$${cost.toFixed(4)}`;
  }
}
