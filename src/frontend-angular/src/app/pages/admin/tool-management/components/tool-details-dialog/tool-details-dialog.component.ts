/**
 * Tool Details Dialog Component
 *
 * Read-only dialog for viewing complete tool configuration.
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';

import { LucideAngularModule } from 'lucide-angular';
import { Tool } from '../../models/tool-management.models';
import { ToolAdminService } from '../../services/tool-admin.service';

@Component({
  selector: 'app-tool-details-dialog',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatChipsModule,
  ],
  templateUrl: './tool-details-dialog.component.html',
  styleUrls: ['./tool-details-dialog.component.scss'],
})
export class ToolDetailsDialogComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  tool: Tool | null = null;
  isLoading = true;
  error: string | null = null;

  constructor(
    private toolService: ToolAdminService,
    private dialogRef: MatDialogRef<ToolDetailsDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { toolId: string }
  ) {}

  ngOnInit(): void {
    this.loadTool();
  }

  loadTool(): void {
    this.isLoading = true;
    this.error = null;

    this.toolService.getTool(this.data.toolId).subscribe({
      next: (tool) => {
        this.tool = tool;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = 'Failed to load tool details';
        this.isLoading = false;
        this.cdr.detectChanges();
        console.error('Error loading tool:', err);
      },
    });
  }

  onClose(): void {
    this.dialogRef.close();
  }

  onEdit(): void {
    this.dialogRef.close({ edit: true });
  }

  getCapabilitiesJson(): string {
    if (!this.tool?.capabilities) return '{}';
    return JSON.stringify(this.tool.capabilities, null, 2);
  }

  getParametersJson(): string {
    if (!this.tool?.parameters_schema) return '{}';
    return JSON.stringify(this.tool.parameters_schema, null, 2);
  }

  // ==========================================================================
  // Security Classification Helpers (ADR-057)
  // ==========================================================================

  getDataSourceLabel(type: string | undefined): string {
    const labels: Record<string, string> = {
      internal: 'Internal Sources',
      external: 'External Sources',
      none: 'No Data Access',
      mixed: 'Mixed Sources',
    };
    return labels[type || 'internal'] || type || 'Unknown';
  }

  getDataSourceClass(type: string | undefined): string {
    const classes: Record<string, string> = {
      internal: 'security-internal',
      external: 'security-external',
      none: 'security-none',
      mixed: 'security-mixed',
    };
    return classes[type || 'internal'] || '';
  }

  getDataFlowLabel(direction: string | undefined): string {
    const labels: Record<string, string> = {
      ingress: 'Ingress Only',
      egress: 'Egress Only',
      bidirectional: 'Bidirectional',
      none: 'No Data Flow',
    };
    return labels[direction || 'ingress'] || direction || 'Unknown';
  }

  getDataFlowClass(direction: string | undefined): string {
    const classes: Record<string, string> = {
      ingress: 'flow-ingress',
      egress: 'flow-egress',
      bidirectional: 'flow-bidirectional',
      none: 'flow-none',
    };
    return classes[direction || 'ingress'] || '';
  }

  getNetworkAccessLabel(level: string | undefined): string {
    const labels: Record<string, string> = {
      isolated: 'Isolated (No Network)',
      internal: 'Internal Network Only',
      external: 'External Internet Access',
    };
    return labels[level || 'internal'] || level || 'Unknown';
  }

  getNetworkAccessClass(level: string | undefined): string {
    const classes: Record<string, string> = {
      isolated: 'network-isolated',
      internal: 'network-internal',
      external: 'network-external',
    };
    return classes[level || 'internal'] || '';
  }

  getSensitivityLabel(sensitivity: string | undefined): string {
    const labels: Record<string, string> = {
      public: 'Public Data',
      internal: 'Internal Data',
      confidential: 'Confidential',
      restricted: 'Restricted (PII/PHI)',
    };
    return labels[sensitivity || 'internal'] || sensitivity || 'Unknown';
  }

  getSensitivityClass(sensitivity: string | undefined): string {
    const classes: Record<string, string> = {
      public: 'sensitivity-public',
      internal: 'sensitivity-internal',
      confidential: 'sensitivity-confidential',
      restricted: 'sensitivity-restricted',
    };
    return classes[sensitivity || 'internal'] || '';
  }
}
