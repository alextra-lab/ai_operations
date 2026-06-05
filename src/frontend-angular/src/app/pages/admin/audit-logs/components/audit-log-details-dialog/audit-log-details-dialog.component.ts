import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { AuditLogEntry } from '../../models/audit-logs.models';
import { LucideAngularModule } from 'lucide-angular';

/**
 * Dialog component for displaying detailed audit log information.
 */
@Component({
  selector: 'app-audit-log-details-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatChipsModule,
  ],
  templateUrl: './audit-log-details-dialog.component.html',
  styleUrls: ['./audit-log-details-dialog.component.scss'],
})
export class AuditLogDetailsDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<AuditLogDetailsDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { log: AuditLogEntry }
  ) {}

  close(): void {
    this.dialogRef.close();
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  getDetailsKeys(): string[] {
    return Object.keys(this.data.log.details || {});
  }

  formatValue(value: any): string {
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  }
}
