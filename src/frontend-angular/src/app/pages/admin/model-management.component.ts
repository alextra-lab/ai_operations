import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

// Angular Material imports
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject } from 'rxjs';
import { finalize, takeUntil } from 'rxjs/operators';

import {
  Model,
  ModelDetailedResponse,
  ModelListResponse,
} from '../../api/models/model-registry.models';
import { ModelRegistryService } from '../../api/services/model-registry.service';
import {
  ModelDetailsDialogComponent,
  ModelDetailsDialogData,
} from './model-management/dialogs/model-details-dialog.component';
import {
  ModelEditDialogComponent,
  ModelEditDialogData,
} from './model-management/dialogs/model-edit-dialog.component';
import {
  ModelPricingDialogComponent,
  ModelPricingDialogData,
} from './model-management/dialogs/model-pricing-dialog.component';

@Component({
  selector: 'app-model-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatTableModule,
    MatPaginatorModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatDialogModule,
  ],
  templateUrl: './model-management.component.html',
  styleUrls: ['./model-management.component.scss'],
})
export class ModelManagementComponent implements OnInit, OnDestroy {
  models: Model[] = [];
  totalModels = 0;
  pageSize = 20;
  currentPage = 0;
  loading = false;
  syncing = false;

  filterProvider?: string;
  filterModelType?: string;
  showHidden = false;

  displayedColumns = [
    'model_id',
    'provider_type',
    'provider',
    'model_type',
    'context_window',
    'embedding_dimensions',
    'is_available',
    'actions',
  ];

  private destroy$ = new Subject<void>();

  constructor(
    private modelRegistryService: ModelRegistryService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadModels();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // =========================================================================
  // Model Loading
  // =========================================================================

  loadModels(): void {
    this.loading = true;
    this.modelRegistryService
      .listModels(
        this.filterProvider,
        this.filterModelType,
        false, // Show all including unavailable
        true, // Include deprecated
        this.showHidden, // Include hidden models based on checkbox
        this.currentPage + 1,
        this.pageSize
      )
      .pipe(
        finalize(() => (this.loading = false)),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (response: ModelListResponse) => {
          this.models = response.models;
          this.totalModels = response.total;
        },
        error: (error) => {
          console.error('Error loading models:', error);
          this.snackBar.open('Failed to load models', 'Close', {
            duration: 5000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  onPageChange(event: PageEvent): void {
    this.currentPage = event.pageIndex;
    this.pageSize = event.pageSize;
    this.loadModels();
  }

  applyFilters(): void {
    this.currentPage = 0;
    this.loadModels();
  }

  clearFilters(): void {
    this.filterProvider = undefined;
    this.filterModelType = undefined;
    this.showHidden = false;
    this.currentPage = 0;
    this.loadModels();
  }

  // =========================================================================
  // Model Sync
  // =========================================================================

  syncModels(): void {
    this.syncing = true;
    this.modelRegistryService
      .syncModels()
      .pipe(
        finalize(() => (this.syncing = false)),
        takeUntil(this.destroy$)
      )
      .subscribe({
        next: (response) => {
          const message = `Sync complete: ${response.synced_models} models synchronized`;
          this.snackBar.open(message, 'Close', {
            duration: 5000,
          });
          this.loadModels(); // Refresh list
        },
        error: (error) => {
          console.error('Error syncing models:', error);
          this.snackBar.open('Failed to sync models', 'Close', {
            duration: 5000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  // =========================================================================
  // Model Actions
  // =========================================================================

  viewModelDetails(id: string): void {
    // Load full model details by database ID
    this.modelRegistryService
      .getModel(id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (model: ModelDetailedResponse) => {
          const dialogData: ModelDetailsDialogData = {
            modelId: id,
            model,
          };

          const dialogRef = this.dialog.open(ModelDetailsDialogComponent, {
            width: '800px',
            maxWidth: '90vw',
            maxHeight: '90vh',
            data: dialogData,
          });

          dialogRef.afterClosed().subscribe((result) => {
            if (result && result.action === 'edit') {
              this.editModel(result.modelId);
            }
          });
        },
        error: (error) => {
          console.error('Error loading model details:', error);
          this.snackBar.open('Failed to load model details', 'Close', {
            duration: 5000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  editModel(id: string): void {
    // Load full model details for editing by database ID
    this.modelRegistryService
      .getModel(id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (model: ModelDetailedResponse) => {
          const dialogData: ModelEditDialogData = {
            modelId: id,
            model,
          };

          const dialogRef = this.dialog.open(ModelEditDialogComponent, {
            width: '800px',
            maxWidth: '90vw',
            maxHeight: '90vh',
            data: dialogData,
          });

          dialogRef.afterClosed().subscribe((result) => {
            if (result && result.action === 'save') {
              this.updateModel(result.modelId, result.updates);
            }
          });
        },
        error: (error) => {
          console.error('Error loading model for edit:', error);
          this.snackBar.open('Failed to load model', 'Close', {
            duration: 5000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  onOpenPricing(event: Event, model: Model): void {
    // Blur the trigger before opening dialog to avoid aria-hidden focus clash
    const target = event.currentTarget as HTMLElement | null;
    if (target && typeof target.blur === 'function') {
      target.blur();
    }
    const active = document.activeElement as HTMLElement | null;
    if (active && active !== target && typeof active.blur === 'function') {
      active.blur();
    }

    const data: ModelPricingDialogData = { modelId: model.model_id };
    this.dialog.open(ModelPricingDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '95vh',
      autoFocus: true,
      restoreFocus: true,
      data,
    });
  }

  updateModel(id: string, updates: any): void {
    this.modelRegistryService
      .updateModelMetadata(id, updates)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.snackBar.open('Model updated successfully', 'Close', {
            duration: 3000,
          });
          this.loadModels(); // Refresh list
        },
        error: (error) => {
          console.error('Error updating model:', error);
          this.snackBar.open('Failed to update model', 'Close', {
            duration: 5000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  toggleHidden(model: Model): void {
    const newHiddenStatus = !model.is_hidden;
    const action = newHiddenStatus ? 'hidden' : 'visible';

    this.modelRegistryService
      .updateModelMetadata(model.id, {
        is_hidden: newHiddenStatus,
      })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.snackBar.open(`Model marked as ${action}`, 'Close', {
            duration: 3000,
          });
          this.loadModels(); // Refresh list
        },
        error: (error) => {
          console.error('Error toggling model visibility:', error);
          this.snackBar.open('Failed to update model visibility', 'Close', {
            duration: 5000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  deleteModel(model: Model): void {
    if (
      !confirm(
        `Delete model "${model.model_id}"? This will also delete pricing history.`
      )
    ) {
      return;
    }

    this.modelRegistryService
      .deleteModel(model.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.snackBar.open('Model deleted successfully', 'Close', {
            duration: 3000,
          });
          this.loadModels();
        },
        error: (error) => {
          console.error('Error deleting model:', error);
          this.snackBar.open('Failed to delete model', 'Close', {
            duration: 5000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  // =========================================================================
  // Utility Methods
  // =========================================================================

  formatNumber(num?: number): string {
    if (!num && num !== 0) return 'N/A';
    return num.toLocaleString();
  }

  getAvailabilityClass(isAvailable: boolean): string {
    return isAvailable ? 'available' : 'unavailable';
  }

  getAvailabilityIcon(isAvailable: boolean): string {
    return isAvailable ? 'check_circle' : 'cancel';
  }

  getAvailableCount(): number {
    return this.models.filter((m) => m.is_available).length;
  }

  getLLMCount(): number {
    return this.models.filter((m) => m.model_type === 'llm').length;
  }

  getEmbeddingCount(): number {
    return this.models.filter((m) => m.model_type === 'embedding').length;
  }
}
