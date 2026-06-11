/**
 * Template Library Component
 *
 * Displays a comprehensive list of prompt templates with search, filtering,
 * and management capabilities. Admin-only access.
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
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
import { Router } from '@angular/router';
import { Observable, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';

import { LucideAngularModule } from 'lucide-angular';
import {
  DeploymentStatus,
  TemplateListResponse,
  TemplateResponse,
} from '../../api/models/template.models';
import { TemplateService } from '../../api/services/template.service';

@Component({
  selector: 'app-template-library',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatTableModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatPaginatorModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatCheckboxModule,
  ],
  templateUrl: './template-library.component.html',
  styleUrls: ['./template-library.component.scss'],
})
export class TemplateLibraryComponent implements OnInit, OnDestroy {
  // Table configuration
  displayedColumns: string[] = [
    'template_id',
    'prompt_type',
    'version_number',
    'deployment_status',
    'updated_at',
    'actions',
  ];

  // Data
  templates$: Observable<TemplateListResponse> | null = null;
  templates: TemplateResponse[] = [];
  totalCount = 0;
  isLoading = false;

  // Pagination
  pageSize = 50;
  currentPage = 1;
  pageSizeOptions = [10, 25, 50, 100];

  // Filters
  filterForm: FormGroup;
  deploymentStatuses = [
    { value: '', label: 'All Statuses' },
    { value: DeploymentStatus.DRAFT, label: 'Draft' },
    { value: DeploymentStatus.PENDING, label: 'Pending' },
    { value: DeploymentStatus.APPROVED, label: 'Approved' },
    { value: DeploymentStatus.DEPLOYED, label: 'Deployed' },
  ];

  private destroy$ = new Subject<void>();

  constructor(
    private templateService: TemplateService,
    private fb: FormBuilder,
    private router: Router,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.filterForm = this.fb.group({
      searchTerm: [''],
      deploymentStatus: [''],
      activeOnly: [false],
    });
  }

  ngOnInit(): void {
    this.loadTemplates();
    this.setupFilterSubscription();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========================================================================
  // Data Loading
  // ========================================================================

  loadTemplates(): void {
    this.isLoading = true;
    const filters = this.buildFilters();

    this.templateService
      .listTemplates(filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.templates = response.templates;
          this.totalCount = response.total_count;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading templates:', error);
          this.snackBar.open(
            `Error loading templates: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.isLoading = false;
        },
      });
  }

  private buildFilters(): any {
    const formValue = this.filterForm.value;
    return {
      page: this.currentPage,
      page_size: this.pageSize,
      template_id_filter: formValue.searchTerm || undefined,
      deployment_status: formValue.deploymentStatus || undefined,
      active_only: formValue.activeOnly || undefined,
    };
  }

  private setupFilterSubscription(): void {
    this.filterForm.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(() => {
        this.currentPage = 1; // Reset to first page on filter change
        this.loadTemplates();
      });
  }

  // ========================================================================
  // Pagination
  // ========================================================================

  onPageChange(event: PageEvent): void {
    this.currentPage = event.pageIndex + 1;
    this.pageSize = event.pageSize;
    this.loadTemplates();
  }

  // ========================================================================
  // Template Actions
  // ========================================================================

  viewTemplate(template: TemplateResponse): void {
    this.router.navigate(['/templates', template.template_id]);
  }

  editTemplate(template: TemplateResponse): void {
    this.router.navigate(['/templates', template.template_id, 'edit']);
  }

  deleteTemplate(template: TemplateResponse): void {
    const confirmDelete = confirm(
      `Delete all versions of template '${template.template_id}'? This cannot be undone.`
    );

    if (confirmDelete) {
      this.templateService
        .deleteTemplate(template.template_id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (result) => {
            this.snackBar.open(
              `Template deleted: ${result.versions_deleted} versions removed`,
              'Close',
              { duration: 3000 }
            );
            this.loadTemplates();
          },
          error: (error) => {
            this.snackBar.open(
              `Error deleting template: ${error.message}`,
              'Close',
              { duration: 5000, panelClass: ['error-snackbar'] }
            );
          },
        });
    }
  }

  approveTemplate(template: TemplateResponse): void {
    const notes = prompt('Approval notes (optional):');
    if (notes !== null) {
      // User didn't cancel
      this.templateService
        .approveTemplate(template.template_id, notes)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.snackBar.open('Template approved', 'Close', {
              duration: 3000,
            });
            this.loadTemplates();
          },
          error: (error) => {
            this.snackBar.open(
              `Error approving template: ${error.message}`,
              'Close',
              { duration: 5000, panelClass: ['error-snackbar'] }
            );
          },
        });
    }
  }

  rejectTemplate(template: TemplateResponse): void {
    const reason = prompt('Rejection reason (required):');
    if (reason && reason.trim()) {
      this.templateService
        .rejectTemplate(template.template_id, reason)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.snackBar.open('Template rejected', 'Close', {
              duration: 3000,
            });
            this.loadTemplates();
          },
          error: (error) => {
            this.snackBar.open(
              `Error rejecting template: ${error.message}`,
              'Close',
              { duration: 5000, panelClass: ['error-snackbar'] }
            );
          },
        });
    }
  }

  createNewTemplate(): void {
    this.router.navigate(['/templates/new']);
  }

  // ========================================================================
  // UI Helpers
  // ========================================================================

  getStatusClass(status: string): string {
    return this.templateService.getDeploymentStatusClass(status);
  }

  getStatusName(status: string): string {
    return this.templateService.getDeploymentStatusName(status);
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  canApprove(template: TemplateResponse): boolean {
    return template.deployment_status === DeploymentStatus.PENDING;
  }

  canReject(template: TemplateResponse): boolean {
    return (
      template.deployment_status === DeploymentStatus.PENDING ||
      template.deployment_status === DeploymentStatus.APPROVED
    );
  }
}
