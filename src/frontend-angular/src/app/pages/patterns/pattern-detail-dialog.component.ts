/**
 * Pattern Detail Dialog Component
 * Displays full pattern information with copy-to-clipboard functionality
 */

import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import {
  PATTERN_CATEGORIES,
  PromptPattern,
} from '../../api/models/prompt-patterns.models';

@Component({
  selector: 'app-pattern-detail-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatButtonModule,
    MatChipsModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './pattern-detail-dialog.component.html',
  styleUrls: ['./pattern-detail-dialog.component.scss'],
})
export class PatternDetailDialogComponent {
  pattern: PromptPattern;
  categoryInfo: any;

  constructor(
    public dialogRef: MatDialogRef<PatternDetailDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { pattern: PromptPattern },
    private snackBar: MatSnackBar
  ) {
    this.pattern = data.pattern;
    this.categoryInfo = PATTERN_CATEGORIES.find(
      (c) => c.id === this.pattern.category
    ) || {
      id: this.pattern.category,
      label: this.pattern.category,
      icon: 'shapes',
      description: '',
      color: '#757575',
    };
  }

  copyToClipboard(text: string, label: string): void {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        this.snackBar.open(`${label} copied to clipboard`, 'Close', {
          duration: 2000,
        });
      })
      .catch((err) => {
        console.error('Failed to copy to clipboard:', err);
        this.snackBar.open('Failed to copy to clipboard', 'Close', {
          duration: 2000,
        });
      });
  }

  close(): void {
    this.dialogRef.close();
  }
}
