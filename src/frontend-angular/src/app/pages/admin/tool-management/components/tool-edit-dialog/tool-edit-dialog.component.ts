/**
 * Tool Edit Dialog Component
 *
 * Dialog for editing tool configuration (metadata and limits only).
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { LucideAngularModule } from 'lucide-angular';
import { Tool, ToolUpdateRequest } from '../../models/tool-management.models';
import { ToolAdminService } from '../../services/tool-admin.service';

@Component({
  selector: 'app-tool-edit-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatChipsModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './tool-edit-dialog.component.html',
  styleUrls: ['./tool-edit-dialog.component.scss'],
})
export class ToolEditDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  form: FormGroup;
  tool: Tool | null = null;
  isSubmitting = false;
  isLoading = true;
  error: string | null = null;
  tagsInput = '';

  constructor(
    private fb: FormBuilder,
    private toolService: ToolAdminService,
    private dialogRef: MatDialogRef<ToolEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { toolId: string }
  ) {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(255)]],
      description: [''],
      timeout_seconds: [
        30,
        [Validators.required, Validators.min(1), Validators.max(300)],
      ],
      rate_limit_per_minute: [null, [Validators.min(1)]],
      health_check_interval_seconds: [300, [Validators.min(60)]],
      tags: [[]],
    });
  }

  ngOnInit(): void {
    this.loadTool();
  }

  loadTool(): void {
    this.isLoading = true;
    this.error = null;

    this.toolService.getTool(this.data.toolId).subscribe({
      next: (tool) => {
        this.tool = tool;
        this.form.patchValue({
          name: tool.name,
          description: tool.description || '',
          timeout_seconds: tool.timeout_seconds,
          rate_limit_per_minute: tool.rate_limit_per_minute,
          health_check_interval_seconds: tool.health_check_interval_seconds,
          tags: tool.tags || [],
        });
        this.tagsInput = tool.tags?.join(', ') || '';
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
      error: (err) => {
        this.error = 'Failed to load tool';
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
        console.error('Error loading tool:', err);
      },
    });
  }

  onTagsInputChange(): void {
    const tags = this.tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    this.form.patchValue({ tags });
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.error = null;

    const request: ToolUpdateRequest = {
      name: this.form.value.name,
      description: this.form.value.description || null,
      timeout_seconds: this.form.value.timeout_seconds,
      rate_limit_per_minute: this.form.value.rate_limit_per_minute || null,
      tags: this.form.value.tags,
    };

    this.toolService.updateTool(this.data.toolId, request).subscribe({
      next: () => {
        this.dialogRef.close(true);
      },
      error: (err) => {
        console.error('Error updating tool:', err);
        this.error =
          err.error?.detail || 'Failed to update tool. Please try again.';
        this.isSubmitting = false;
      },
    });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }
}
