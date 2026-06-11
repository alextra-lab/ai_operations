/**
 * Collection Edit Dialog Component
 *
 * Dialog for editing an existing collection's mutable properties.
 * Only description and is_active can be modified.
 * Embedding model is immutable after creation.
 *
 * Reference: P2-F3-ENHANCED-Collection-Management.md - Task 2.2
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { LucideAngularModule } from 'lucide-angular';
import {
  Collection,
  CollectionUpdate,
} from '../../api/models/collection.models';
import { CollectionService } from '../../api/services/collection.service';

@Component({
  selector: 'app-collection-edit-dialog',
  templateUrl: './collection-edit-dialog.component.html',
  styleUrls: ['./collection-edit-dialog.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
  ],
})
export class CollectionEditDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  editForm: FormGroup;
  isSubmitting = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private collectionService: CollectionService,
    private dialogRef: MatDialogRef<CollectionEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public collection: Collection
  ) {
    this.editForm = this.fb.group({
      description: [collection.description || ''],
      is_active: [collection.is_active],
      // Preflight configuration (P4-DOC-07)
      auto_chunk_enabled: [collection.auto_chunk_enabled ?? true],
      preflight_sample_tokens: [collection.preflight_sample_tokens ?? 10000],
    });
  }

  ngOnInit(): void {
    // No additional initialization needed
  }

  /**
   * Check if form has changes
   */
  hasChanges(): boolean {
    const form = this.editForm.value;
    return (
      form.description !== this.collection.description ||
      form.is_active !== this.collection.is_active ||
      form.auto_chunk_enabled !== this.collection.auto_chunk_enabled ||
      form.preflight_sample_tokens !== this.collection.preflight_sample_tokens
    );
  }

  /**
   * Submit form and update collection
   */
  onSubmit(): void {
    if (!this.hasChanges() || this.isSubmitting) {
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    const formValue = this.editForm.value;
    const updateData: CollectionUpdate = {
      description: formValue.description?.trim() || undefined,
      is_active: formValue.is_active,
      // Auto-chunking configuration (P4-DOC-07)
      auto_chunk_enabled: formValue.auto_chunk_enabled,
      preflight_sample_tokens: formValue.preflight_sample_tokens,
    };

    this.collectionService
      .updateCollection(this.collection.id, updateData)
      .subscribe({
        next: (updatedCollection) => {
          this.dialogRef.close(updatedCollection);
        },
        error: (error) => {
          this.errorMessage = error.message;
          this.isSubmitting = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
      });
  }

  /**
   * Cancel and close dialog
   */
  onCancel(): void {
    this.dialogRef.close();
  }
}
