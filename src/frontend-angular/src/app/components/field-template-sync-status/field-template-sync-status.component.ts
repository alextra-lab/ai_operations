/**
 * Displays synchronization status between input fields and template variables.
 * Shows synced, warnings (field_only), and errors (template_only).
 */
import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

import type { FieldSyncStatus } from '../user-interaction-config/user-interaction-config.component';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-field-template-sync-status',
  templateUrl: './field-template-sync-status.component.html',
  styleUrls: ['./field-template-sync-status.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatButtonModule,
    MatTooltipModule,
  ],
})
export class FieldTemplateSyncStatusComponent {
  @Input() statuses: FieldSyncStatus[] = [];

  @Output() createField = new EventEmitter<string>();
  @Output() insertIntoTemplate = new EventEmitter<string>();

  get syncedItems(): FieldSyncStatus[] {
    return this.statuses.filter((s) => s.status === 'synced');
  }

  get warningItems(): FieldSyncStatus[] {
    return this.statuses.filter((s) => s.status === 'field_only');
  }

  get errorItems(): FieldSyncStatus[] {
    return this.statuses.filter((s) => s.status === 'template_only');
  }

  get hasAnyItems(): boolean {
    return this.statuses.length > 0;
  }

  getIcon(status: FieldSyncStatus['status']): string {
    switch (status) {
      case 'synced':
        return 'circle-check';
      case 'field_only':
        return 'triangle-alert';
      case 'template_only':
        return 'circle-alert';
    }
  }

  getIconClass(status: FieldSyncStatus['status']): string {
    switch (status) {
      case 'synced':
        return 'text-green-600';
      case 'field_only':
        return 'text-amber-600';
      case 'template_only':
        return 'text-red-600';
    }
  }

  onCreateField(varName: string): void {
    this.createField.emit(varName);
  }

  onInsertIntoTemplate(fieldName: string): void {
    this.insertIntoTemplate.emit(fieldName);
  }
}
