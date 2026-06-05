/**
 * UseCaseSelectorDialogComponent
 *
 * Dialog for selecting a Use Case to apply discovered parameters.
 * Supports three modes:
 * 1. Update existing draft
 * 2. Clone published Use Case → draft → apply
 * 3. Create new Use Case with pre-filled parameters
 *
 * Features:
 * - Smart filtering based on mode and permissions
 * - Parameter diff preview before applying
 * - Permission validation (draft-only modification)
 * - Audit trail metadata
 * - Navigate to wizard after injection
 *
 * Related: P4-TOOLS-05, ADR-045, ADR-018, ADR-020, ADR-041
 */

import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { map, Observable, startWith, switchMap } from 'rxjs';

import { LucideAngularModule } from 'lucide-angular';
import { QueryConfig } from '../../../../api/models/query-config.models';
import {
  CloneRequest,
  UseCaseListFilters,
  UseCaseResponse,
  UseCaseUpdate,
} from '../../../../api/models/use-case-management.models';
import { UseCaseManagementService } from '../../../../api/services/use-case-management.service';
import { UserProfile } from '../../../../core/auth/auth.models';
import { AuthService } from '../../../../core/auth/auth.service';

export interface UseCaseSelectorDialogData {
  mode: 'update' | 'clone';
  discoveredParams: Partial<QueryConfig>;
}

export interface UseCaseSelectorDialogResult {
  success: boolean;
  useCase?: UseCaseResponse;
  cloned?: boolean;
  error?: any;
}

@Component({
  selector: 'app-use-case-selector-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './use-case-selector-dialog.component.html',
  styleUrls: ['./use-case-selector-dialog.component.scss'],
})
export class UseCaseSelectorDialogComponent implements OnInit {
  useCases$!: Observable<UseCaseResponse[]>;
  searchControl = new FormControl('');
  selectedUseCase: UseCaseResponse | null = null;
  isLoading = false;
  currentUser: UserProfile | null = null;

  constructor(
    @Inject(MAT_DIALOG_DATA)
    public data: UseCaseSelectorDialogData,
    private dialogRef: MatDialogRef<UseCaseSelectorDialogComponent>,
    private useCaseService: UseCaseManagementService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private router: Router
  ) {
    // Get current user from auth state
    this.authService.getCurrentUser().subscribe((user: UserProfile | null) => {
      this.currentUser = user;
    });
  }

  ngOnInit(): void {
    this.loadUseCases();
  }

  /**
   * Load Use Cases with filtering based on mode
   */
  loadUseCases(): void {
    this.isLoading = true;

    const filters: UseCaseListFilters = {
      lifecycle_state: this.data.mode === 'update' ? 'draft' : 'published',
      page_size: 100,
    };

    this.useCases$ = this.useCaseService.listUseCases(filters).pipe(
      map((response) => response.use_cases),
      map((useCases) => this.filterEditableUseCases(useCases)),
      switchMap((useCases) =>
        this.searchControl.valueChanges.pipe(
          startWith(''),
          map((search) => this.filterBySearch(useCases, search || ''))
        )
      )
    );

    // Set loading to false after initial load
    this.useCases$.subscribe({
      next: () => (this.isLoading = false),
      error: () => (this.isLoading = false),
    });
  }

  /**
   * Filter Use Cases based on mode and permissions
   */
  filterEditableUseCases(useCases: UseCaseResponse[]): UseCaseResponse[] {
    if (!this.currentUser) {
      return [];
    }

    return useCases.filter((uc) => {
      if (this.data.mode === 'update') {
        // Only show drafts the user created
        return (
          uc.lifecycle_state === 'draft' &&
          uc.created_by_user_id === this.currentUser?.id
        );
      } else {
        // Show all published Use Cases (can be cloned)
        return uc.lifecycle_state === 'published';
      }
    });
  }

  /**
   * Filter Use Cases by search term
   */
  filterBySearch(
    useCases: UseCaseResponse[],
    search: string
  ): UseCaseResponse[] {
    if (!search || search.trim() === '') {
      return useCases;
    }

    const lowerSearch = search.toLowerCase();
    return useCases.filter(
      (uc) =>
        uc.name.toLowerCase().includes(lowerSearch) ||
        uc.use_case_id.toLowerCase().includes(lowerSearch) ||
        (uc.description &&
          uc.description.toLowerCase().includes(lowerSearch)) ||
        (uc.category && uc.category.toLowerCase().includes(lowerSearch))
    );
  }

  /**
   * Check if parameters can be applied to Use Case
   */
  canApplyToUseCase(useCase: UseCaseResponse): boolean {
    if (!this.currentUser) {
      return false;
    }

    // Must be draft state for direct modification
    if (useCase.lifecycle_state !== 'draft') {
      return false;
    }

    // Must be creator or admin
    if (
      useCase.created_by_user_id !== this.currentUser.id &&
      !this.currentUser.roles.includes('admin')
    ) {
      return false;
    }

    return true;
  }

  /**
   * Select a Use Case
   */
  selectUseCase(useCase: UseCaseResponse): void {
    this.selectedUseCase = useCase;
  }

  /**
   * Confirm selection and apply parameters
   */
  onConfirm(): void {
    if (!this.selectedUseCase) {
      return;
    }

    if (this.data.mode === 'update') {
      this.injectParameters(this.selectedUseCase);
    } else {
      this.cloneAndInject(this.selectedUseCase);
    }
  }

  /**
   * Cancel dialog
   */
  onCancel(): void {
    this.dialogRef.close({ success: false });
  }

  /**
   * Inject parameters into existing draft Use Case
   */
  private injectParameters(useCase: UseCaseResponse): void {
    if (!this.currentUser) {
      return;
    }

    this.isLoading = true;

    const updateRequest: UseCaseUpdate = {
      config_json: this.mergeConfigs(
        useCase.config_json,
        this.data.discoveredParams
      ),
      metadata_json: {
        ...useCase.metadata_json,
        parameter_source: 'query_developer_tools',
        tuned_by_user_id: this.currentUser.id,
        tuned_at: new Date().toISOString(),
      },
    };

    this.useCaseService.updateUseCase(useCase.id, updateRequest).subscribe({
      next: (updated) => {
        this.isLoading = false;
        this.dialogRef.close({
          success: true,
          useCase: updated,
        });
        this.showSuccess(updated);
      },
      error: (error) => {
        this.isLoading = false;
        this.handleError(error);
      },
    });
  }

  /**
   * Clone published Use Case, then inject parameters
   */
  private cloneAndInject(sourceUseCase: UseCaseResponse): void {
    if (!this.currentUser) {
      return;
    }

    this.isLoading = true;

    const timestamp = Date.now();
    const cloneRequest: CloneRequest = {
      new_use_case_id: `${sourceUseCase.use_case_id}_tuned_${timestamp}`,
      new_name: `${sourceUseCase.name} (Tuned)`,
    };

    this.useCaseService
      .cloneUseCase(
        sourceUseCase.id,
        cloneRequest.new_use_case_id,
        cloneRequest.new_name
      )
      .pipe(
        switchMap((cloned) => {
          // Inject parameters into the draft clone
          const updateRequest: UseCaseUpdate = {
            config_json: this.mergeConfigs(
              cloned.config_json,
              this.data.discoveredParams
            ),
            metadata_json: {
              ...cloned.metadata_json,
              parameter_source: 'query_developer_tools',
              tuned_by_user_id: this.currentUser?.id,
              tuned_at: new Date().toISOString(),
              cloned_for_tuning: true,
              source_use_case_id: sourceUseCase.use_case_id,
            },
          };
          return this.useCaseService.updateUseCase(cloned.id, updateRequest);
        })
      )
      .subscribe({
        next: (updated) => {
          this.isLoading = false;
          this.dialogRef.close({
            success: true,
            useCase: updated,
            cloned: true,
          });
          this.showClonedSuccess(updated);
        },
        error: (error) => {
          this.isLoading = false;
          this.handleError(error);
        },
      });
  }

  /**
   * Merge discovered parameters into Use Case config
   */
  private mergeConfigs(
    existingConfig: Record<string, any>,
    discoveredParams: Partial<QueryConfig>
  ): Record<string, any> {
    const merged = { ...existingConfig };

    // Update models (LLM only) - use bracket notation for index signature
    if (discoveredParams.llm_model && merged['models']) {
      merged['models'] = {
        ...merged['models'],
        llm: discoveredParams.llm_model,
      };
    }

    // Update RAG configuration - use bracket notation
    if (discoveredParams.rag && merged['rag']) {
      merged['rag'] = {
        ...merged['rag'],
        top_k: discoveredParams.rag.top_k ?? merged['rag'].top_k,
        similarity_threshold:
          discoveredParams.rag.similarity_threshold ??
          merged['rag'].similarity_threshold,
        vector_collections:
          discoveredParams.rag.vector_collections ??
          merged['rag'].vector_collections,
        hybrid_bm25:
          discoveredParams.rag.hybrid_bm25 ?? merged['rag'].hybrid_bm25,
      };
    }

    // Update generation parameters (sampling) - use bracket notation
    if (discoveredParams.sampling && merged['generation_params']) {
      merged['generation_params'] = {
        ...merged['generation_params'],
        temperature:
          discoveredParams.sampling.temperature ??
          merged['generation_params'].temperature,
        max_tokens:
          discoveredParams.sampling.max_tokens ??
          merged['generation_params'].max_tokens,
        top_p:
          discoveredParams.sampling.top_p ?? merged['generation_params'].top_p,
      };

      // Add sampling preset if present
      if (discoveredParams.sampling.preset) {
        merged['generation_params']['sampling_preset'] =
          discoveredParams.sampling.preset;
      }
    }

    return merged;
  }

  /**
   * Show success message with navigation option
   */
  private showSuccess(useCase: UseCaseResponse): void {
    const snackBarRef = this.snackBar.open(
      `Parameters applied to "${useCase.name}"`,
      'View in Wizard',
      { duration: 5000 }
    );

    snackBarRef.onAction().subscribe(() => {
      this.router.navigate(['/dev/use-cases/edit', useCase.id]);
    });
  }

  /**
   * Show success message for cloned Use Case
   */
  private showClonedSuccess(useCase: UseCaseResponse): void {
    const snackBarRef = this.snackBar.open(
      `Cloned and tuned: "${useCase.name}"`,
      'Edit in Wizard',
      { duration: 7000 }
    );

    snackBarRef.onAction().subscribe(() => {
      this.router.navigate(['/dev/use-cases/edit', useCase.id]);
    });
  }

  /**
   * Handle API errors
   */
  private handleError(error: any): void {
    let message = 'Failed to apply parameters';

    if (error.status === 403) {
      message =
        'Permission denied: You can only update your own draft use cases';
    } else if (error.status === 400 && error.error?.detail) {
      message = `Invalid request: ${error.error.detail}`;
    } else if (error.message) {
      message = error.message;
    }

    this.snackBar.open(message, 'Close', { duration: 5000 });
    this.dialogRef.close({ success: false, error });
  }

  /**
   * Get parameter changes for preview
   */
  getParameterChanges(): { label: string; value: any }[] {
    const changes: { label: string; value: any }[] = [];
    const params = this.data.discoveredParams;

    if (params.llm_model) {
      changes.push({ label: 'LLM Model', value: params.llm_model });
    }

    if (params.sampling?.preset) {
      changes.push({
        label: 'Sampling Preset',
        value: params.sampling.preset,
      });
    }

    if (params.sampling?.temperature !== undefined) {
      changes.push({
        label: 'Temperature',
        value: params.sampling.temperature.toFixed(2),
      });
    }

    if (params.sampling?.max_tokens) {
      changes.push({
        label: 'Max Tokens',
        value: params.sampling.max_tokens,
      });
    }

    if (params.rag?.top_k) {
      changes.push({ label: 'Top K', value: params.rag.top_k });
    }

    if (params.rag?.similarity_threshold !== undefined) {
      changes.push({
        label: 'Similarity Threshold',
        value: params.rag.similarity_threshold.toFixed(2),
      });
    }

    if (params.rag?.hybrid_bm25 !== undefined) {
      changes.push({
        label: 'Hybrid BM25',
        value: params.rag.hybrid_bm25 ? 'Enabled' : 'Disabled',
      });
    }

    return changes;
  }
}
