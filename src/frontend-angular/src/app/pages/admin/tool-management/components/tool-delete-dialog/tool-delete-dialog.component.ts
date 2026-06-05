/**
 * Tool Delete Dialog Component
 *
 * Confirmation dialog for deleting tools.
 */

import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { ToolListItem } from '../../models/tool-management.models';
import { ToolAdminService } from '../../services/tool-admin.service';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-tool-delete-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule,
  ],
  templateUrl: './tool-delete-dialog.component.html',
  styleUrls: ['./tool-delete-dialog.component.scss'],
})
export class ToolDeleteDialogComponent {
  confirmCheckbox = false;
  confirmInput = '';
  isDeleting = false;
  error: string | null = null;

  constructor(
    private toolService: ToolAdminService,
    private dialogRef: MatDialogRef<ToolDeleteDialogComponent>,
    private snackBar: MatSnackBar,
    @Inject(MAT_DIALOG_DATA) public data: { tool: ToolListItem }
  ) {}

  get canDelete(): boolean {
    return (
      this.confirmCheckbox &&
      this.confirmInput === this.data.tool.tool_id &&
      !this.isDeleting
    );
  }

  onDelete(): void {
    if (!this.canDelete) {
      return;
    }

    this.isDeleting = true;
    this.error = null;

    this.toolService.deleteTool(this.data.tool.id).subscribe({
      next: () => {
        this.snackBar.open('Tool deleted successfully', 'Close', {
          duration: 3000,
        });
        this.dialogRef.close(true);
      },
      error: (err) => {
        console.error('Error deleting tool:', err);
        this.error =
          err.error?.detail || 'Failed to delete tool. Please try again.';
        this.isDeleting = false;
      },
    });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }
}
