/**
 * Use Case List Component
 *
 * Displays a Material table of all use cases with filtering, search,
 * pagination, and admin actions (create, edit, clone, delete, toggle active).
 *
 * Reference: USE_CASE_MANAGEMENT_PLAN.md - Task 1.7
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';

import {
  LifecycleState,
  UseCaseListFilters,
  UseCaseResponse,
} from '../../api/models/use-case-management.models';
import {
  CategoryConfig,
  IntentTypeConfig,
} from '../../api/models/platform-config.models';
import { PlatformConfigService } from '../../api/services/platform-config.service';
import { UseCaseManagementService } from '../../api/services/use-case-management.service';
import {
  StateTransitionDialogComponent,
  StateTransitionDialogResult,
} from './state-transition-dialog.component';

@Component({
  selector: 'app-use-case-list',
  templateUrl: './use-case-list.component.html',
  styleUrls: ['./use-case-list.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatDividerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule,
    MatSortModule,
    MatTableModule,
  ],
})
export class UseCaseListComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // Page context
  pageTitle = 'AIOps Library'; // Default title

  // Data
  useCases: UseCaseResponse[] = [];
  filteredUseCases: UseCaseResponse[] = [];
  totalCount = 0;
  isLoading = false;

  // Table columns
  displayedColumns: string[] = [
    'name',
    'category',
    'intent_type',
    'lifecycle_state',
    'is_active',
    'version',
    'updated_at',
    'actions',
  ];

  // Filters (ADR-067: dynamic from backend)
  filterForm: FormGroup;
  categories: CategoryConfig[] = [];
  lifecycleStates = Object.values(LifecycleState);
  intentTypes: IntentTypeConfig[] = [];

  // Pagination
  currentPage = 1;
  pageSize = 20;
  pageSizeOptions = [10, 20, 50, 100];

  // Search
  searchQuery = '';

  constructor(
    private useCaseService: UseCaseManagementService,
    private platformConfig: PlatformConfigService,
    private router: Router,
    private route: ActivatedRoute,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private fb: FormBuilder
  ) {
    this.filterForm = this.fb.group({
      search: [''],
      category: [''],
      lifecycle_state: [''],
      is_active: [null],
      intent_type: [''],
    });
  }

  ngOnInit(): void {
    // Set page title from route data (defaults to 'My AI Operations')
    this.route.data.pipe(takeUntil(this.destroy$)).subscribe((data) => {
      this.pageTitle = data['pageTitle'] || 'My AI Operations';
    });

    // ADR-067: Load dynamic categories and intent types
    this.platformConfig
      .loadCategories()
      .pipe(takeUntil(this.destroy$))
      .subscribe((cats) => {
        this.categories = cats;
      });
    this.platformConfig
      .loadIntentTypes()
      .pipe(takeUntil(this.destroy$))
      .subscribe((types) => {
        this.intentTypes = types;
      });

    this.setupFilters();
    this.loadUseCases();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Setup filter form with debounced search
   */
  private setupFilters(): void {
    this.filterForm.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(() => {
        this.currentPage = 1; // Reset to first page
        this.loadUseCases();
      });
  }

  /**
   * Load use cases from backend
   */
  loadUseCases(): void {
    this.isLoading = true;

    const filters: UseCaseListFilters = {
      page: this.currentPage,
      page_size: this.pageSize,
    };

    const formValue = this.filterForm.value;

    if (formValue.search) {
      filters.search_query = formValue.search;
    }
    if (formValue.category) {
      filters.category = formValue.category;
    }
    if (formValue.lifecycle_state) {
      filters.lifecycle_state = formValue.lifecycle_state;
    }
    if (formValue.is_active !== null && formValue.is_active !== '') {
      filters.is_active =
        formValue.is_active === 'true' || formValue.is_active === true;
    }
    if (formValue.intent_type) {
      filters.intent_type = formValue.intent_type;
    }

    this.useCaseService
      .listUseCases(filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.useCases = response.use_cases || [];
          this.totalCount = response.total_count || this.useCases.length;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading use cases:', error);
          this.showError('Failed to load AI operations: ' + error.message);
          this.isLoading = false;
        },
      });
  }

  /**
   * Handle page change
   */
  onPageChange(event: { pageIndex: number; pageSize: number }): void {
    this.currentPage = event.pageIndex + 1;
    this.pageSize = event.pageSize;
    this.loadUseCases();
  }

  /**
   * Clear all filters
   */
  clearFilters(): void {
    this.filterForm.reset();
    this.currentPage = 1;
    this.loadUseCases();
  }

  /**
   * Navigate to use case creation wizard
   */
  createUseCase(): void {
    this.router.navigate(['/dev/use-cases/wizard']);
  }

  /**
   * Navigate to use case editor
   */
  editUseCase(useCase: UseCaseResponse): void {
    // Navigate with UUID (id), as required by backend API
    this.router.navigate(['/dev/use-cases/edit', useCase.id]);
  }

  /**
   * Clone a use case
   */
  cloneUseCase(useCase: UseCaseResponse): void {
    const newId = `cloned_${useCase.use_case_id}_${Date.now()}`;
    const newName = `${useCase.name} (Copy)`;

    this.useCaseService
      .cloneUseCase(useCase.id, newId, newName)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (cloned) => {
          this.showSuccess(`AI operation cloned successfully: ${cloned.name}`);
          this.loadUseCases();
        },
        error: (error) => {
          this.showError('Failed to clone AI operation: ' + error.message);
        },
      });
  }

  /**
   * Delete a use case (with confirmation)
   */
  deleteUseCase(useCase: UseCaseResponse): void {
    const confirmed = confirm(
      `Are you sure you want to delete "${useCase.name}"?\n\nThis action cannot be undone.`
    );

    if (confirmed) {
      this.useCaseService
        .deleteUseCase(useCase.id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.showSuccess('AI operation deleted successfully');
            this.loadUseCases();
          },
          error: (error) => {
            this.showError('Failed to delete AI operation: ' + error.message);
          },
        });
    }
  }

  /**
   * Toggle use case active state
   */
  toggleActive(useCase: UseCaseResponse): void {
    // Note: Backend doesn't have a direct toggle endpoint
    // Active state is controlled by publish/unpublish transitions
    this.showInfo('To change active state, please edit the AI operation');
    this.editUseCase(useCase);
  }

  /**
   * Execute use case (navigate to execution page)
   */
  executeUseCase(useCase: UseCaseResponse): void {
    // Navigate to execution page relative to current route
    // This keeps us in the AIOps Development context (/dev/use-cases/:id)
    this.router.navigate([useCase.id], { relativeTo: this.route });
  }

  /**
   * Navigate to use case detail/preview
   */
  viewUseCase(useCase: UseCaseResponse): void {
    // Navigate with UUID (id), as required by backend API
    this.router.navigate(['/dev/use-cases/view', useCase.id]);
  }

  /**
   * Get lifecycle state display information
   */
  getStateClass(state: string): string {
    return this.useCaseService.getLifecycleStateClass(state);
  }

  getStateName(state: string): string {
    return this.useCaseService.getLifecycleStateName(state);
  }

  getStateIcon(state: string): string {
    return this.useCaseService.getLifecycleStateIcon(state);
  }

  /**
   * ADR-067: Get display name for a category code.
   */
  getCategoryDisplayName(code: string): string {
    const cat = this.categories.find(
      (c) => c.category_code === code
    );
    return cat?.display_name ?? code;
  }

  /**
   * ADR-067: Get display name for an intent type code.
   */
  getIntentDisplayName(code: string): string {
    const intent = this.intentTypes.find(
      (t) => t.intent_code === code
    );
    return intent?.display_name ?? code;
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  /**
   * Check if user can perform actions
   */
  canEdit(useCase: UseCaseResponse): boolean {
    // TODO: Check user permissions based on useCase state/ownership
    return useCase !== null; // Placeholder check
  }

  canDelete(useCase: UseCaseResponse): boolean {
    // TODO: Check user permissions and use case state
    // Typically can't delete published use cases
    return useCase.lifecycle_state !== LifecycleState.PUBLISHED;
  }

  canClone(useCase: UseCaseResponse): boolean {
    // TODO: Check user permissions
    return useCase !== null; // Placeholder check
  }

  // ========================================================================
  // Lifecycle Management Methods
  // ========================================================================

  /**
   * Check if use case can transition states
   */
  canTransition(useCase: UseCaseResponse): boolean {
    const allowed = this.useCaseService.getAllowedNextStates(
      useCase.lifecycle_state
    );
    return allowed.length > 0;
  }

  /**
   * Get allowed next states for a use case
   */
  getAllowedNextStates(useCase: UseCaseResponse): string[] {
    return this.useCaseService.getAllowedNextStates(useCase.lifecycle_state);
  }

  /**
   * Transition use case to a new lifecycle state
   */
  transitionState(useCase: UseCaseResponse, targetState?: string): void {
    const allowedStates = this.getAllowedNextStates(useCase);

    if (allowedStates.length === 0) {
      this.showError('No valid transitions from current state');
      return;
    }

    // Use provided target or first allowed state
    const initialTarget = targetState || allowedStates[0];

    // Open confirmation dialog
    const dialogRef = this.dialog.open(StateTransitionDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      data: {
        useCase: useCase,
        targetState: initialTarget,
        allowedStates: allowedStates,
      },
    });

    dialogRef.afterClosed().subscribe((result: StateTransitionDialogResult) => {
      if (result?.confirmed) {
        this.performStateTransition(useCase, result.targetState, result.notes);
      }
    });
  }

  /**
   * Actually perform the state transition via API
   */
  private performStateTransition(
    useCase: UseCaseResponse,
    targetState: string,
    notes?: string
  ): void {
    this.isLoading = true;

    this.useCaseService
      .transitionState(useCase.id, {
        to_state: targetState,
        approval_notes: notes,
      })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.showSuccess(
            `AI operation transitioned to ${this.getStateName(targetState)}`
          );
          this.loadUseCases();
        },
        error: (error: Error) => {
          this.showError(
            `Failed to transition state: ${error.message || 'Unknown error'}`
          );
          this.isLoading = false;
        },
      });
  }

  /**
   * Helper methods for common state transitions
   */
  sendToReview(useCase: UseCaseResponse): void {
    this.transitionState(useCase, LifecycleState.REVIEW);
  }

  publishUseCase(useCase: UseCaseResponse): void {
    this.transitionState(useCase, LifecycleState.PUBLISHED);
  }

  archiveUseCase(useCase: UseCaseResponse): void {
    this.transitionState(useCase, LifecycleState.ARCHIVED);
  }

  returnToDraft(useCase: UseCaseResponse): void {
    this.transitionState(useCase, LifecycleState.DRAFT);
  }

  /**
   * Show success notification
   */
  private showSuccess(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 3000,
      panelClass: ['success-snackbar'],
    });
  }

  /**
   * Show error notification
   */
  private showError(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar'],
    });
  }

  /**
   * Show info notification
   */
  private showInfo(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 3000,
      panelClass: ['info-snackbar'],
    });
  }
}
