/**
 * Template Detail Component
 *
 * Displays comprehensive template information including:
 * - Template content and metadata
 * - Version history and comparison
 * - Approval workflow actions
 * - Version activation
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { LucideAngularModule } from 'lucide-angular';
import {
  TemplateDiffResponse,
  TemplateResponse,
  TemplateVersionCreate,
  TemplateVersionResponse,
} from '../../api/models/template.models';
import { TemplateService } from '../../api/services/template.service';

@Component({
  selector: 'app-template-detail',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatTabsModule,
    MatChipsModule,
    MatDividerModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatCheckboxModule,
  ],
  templateUrl: './template-detail.component.html',
  styleUrls: ['./template-detail.component.scss'],
})
export class TemplateDetailComponent implements OnInit, OnDestroy {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  templateId: string | null = null;
  template: TemplateResponse | null = null;
  versions: TemplateVersionResponse[] = [];
  selectedVersion1: number | null = null;
  selectedVersion2: number | null = null;
  diffResult: TemplateDiffResponse | null = null;

  loading = false;
  processing = false;

  newVersionForm: FormGroup;
  approvalForm: FormGroup;

  private destroy$ = new Subject<void>();

  constructor(
    private templateService: TemplateService,
    private route: ActivatedRoute,
    private router: Router,
    private fb: FormBuilder,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.newVersionForm = this.fb.group({
      template_content: ['', [Validators.required, Validators.minLength(10)]],
      change_notes: [''],
    });

    this.approvalForm = this.fb.group({
      approval_notes: [''],
    });
  }

  ngOnInit(): void {
    this.route.paramMap.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      this.templateId = params.get('id');
      if (this.templateId) {
        this.loadTemplateDetails(this.templateId);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ========================================================================
  // Data Loading
  // ========================================================================

  loadTemplateDetails(templateId: string): void {
    this.loading = true;

    // Load template
    this.templateService
      .getTemplate(templateId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (template) => {
          this.template = template;
          this.loadVersionHistory(templateId);
        },
        error: (error) => {
          this.snackBar.open(
            `Error loading template: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  loadVersionHistory(templateId: string): void {
    this.templateService
      .getTemplateVersions(templateId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.versions = response.versions;
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.snackBar.open(
            `Error loading versions: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.loading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  // ========================================================================
  // Version Control Actions
  // ========================================================================

  createNewVersion(): void {
    if (this.newVersionForm.invalid || !this.templateId || !this.template) {
      return;
    }

    this.processing = true;
    const versionData: TemplateVersionCreate = {
      template_content: this.newVersionForm.get('template_content')?.value,
      variables: this.template.variables, // Inherit from current
      metadata_json: this.template.metadata_json, // Inherit from current
      change_notes: this.newVersionForm.get('change_notes')?.value,
    };

    this.templateService
      .createTemplateVersion(this.templateId, versionData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.snackBar.open('New version created', 'Close', {
            duration: 3000,
          });
          this.newVersionForm.reset();
          if (this.templateId) {
            this.loadTemplateDetails(this.templateId);
          }
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.snackBar.open(
            `Error creating version: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  activateVersion(versionNumber: number): void {
    if (!this.templateId) return;

    const confirm = window.confirm(
      `Activate version ${versionNumber}? This will deactivate all other versions.`
    );

    if (!confirm) return;

    this.processing = true;
    this.templateService
      .activateTemplateVersion(this.templateId, versionNumber)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.snackBar.open(`Version ${versionNumber} activated`, 'Close', {
            duration: 3000,
          });
          if (this.templateId) {
            this.loadTemplateDetails(this.templateId);
          }
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.snackBar.open(
            `Error activating version: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  compareVersions(): void {
    if (!this.templateId || !this.selectedVersion1 || !this.selectedVersion2) {
      this.snackBar.open('Please select two versions to compare', 'Close', {
        duration: 3000,
      });
      return;
    }

    this.processing = true;
    this.templateService
      .compareTemplateVersions(
        this.templateId,
        this.selectedVersion1,
        this.selectedVersion2
      )
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (diff) => {
          this.diffResult = diff;
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.snackBar.open(
            `Error comparing versions: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  // ========================================================================
  // Approval Workflow Actions
  // ========================================================================

  approveTemplate(): void {
    if (!this.templateId) return;

    this.processing = true;
    const notes = this.approvalForm.get('approval_notes')?.value;

    this.templateService
      .approveTemplate(this.templateId, notes)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.snackBar.open('Template approved', 'Close', { duration: 3000 });
          this.approvalForm.reset();
          if (this.templateId) {
            this.loadTemplateDetails(this.templateId);
          }
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.snackBar.open(
            `Error approving template: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  rejectTemplate(): void {
    if (!this.templateId) return;

    const reason = prompt('Enter rejection reason (required):');
    if (!reason || !reason.trim()) {
      return;
    }

    this.processing = true;
    this.templateService
      .rejectTemplate(this.templateId, reason)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.snackBar.open('Template rejected', 'Close', { duration: 3000 });
          if (this.templateId) {
            this.loadTemplateDetails(this.templateId);
          }
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.snackBar.open(
            `Error rejecting template: ${error.message}`,
            'Close',
            { duration: 5000, panelClass: ['error-snackbar'] }
          );
          this.processing = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  // ========================================================================
  // Navigation Actions
  // ========================================================================

  editTemplate(): void {
    if (this.templateId) {
      this.router.navigate(['/templates', this.templateId, 'edit']);
    }
  }

  backToLibrary(): void {
    this.router.navigate(['/templates/library']);
  }

  deleteTemplate(): void {
    if (!this.templateId || !this.template) return;

    const confirm = window.confirm(
      `Delete all versions of template '${this.template.template_id}'? This cannot be undone.`
    );

    if (confirm) {
      this.templateService
        .deleteTemplate(this.templateId)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (result) => {
            this.snackBar.open(
              `Template deleted: ${result.versions_deleted} versions removed`,
              'Close',
              { duration: 3000 }
            );
            this.router.navigate(['/templates/library']);
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

  // ========================================================================
  // UI Helpers
  // ========================================================================

  getStatusClass(status: string): string {
    return this.templateService.getDeploymentStatusClass(status);
  }

  getStatusName(status: string): string {
    return this.templateService.getDeploymentStatusName(status);
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  }

  canApprove(): boolean {
    return this.template?.deployment_status === 'pending';
  }

  canReject(): boolean {
    return (
      this.template?.deployment_status === 'pending' ||
      this.template?.deployment_status === 'approved'
    );
  }

  toggleVersionSelection(slot: number, versionNumber: number): void {
    if (slot === 1) {
      this.selectedVersion1 =
        this.selectedVersion1 === versionNumber ? null : versionNumber;
    } else {
      this.selectedVersion2 =
        this.selectedVersion2 === versionNumber ? null : versionNumber;
    }
  }

  hasMetadata(): boolean {
    return this.template
      ? Object.keys(this.template.metadata_json).length > 0
      : false;
  }
}
