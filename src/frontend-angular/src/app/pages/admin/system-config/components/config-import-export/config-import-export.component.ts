/**
 * Configuration Import/Export Dialog Component
 *
 * Dialog for importing and exporting configuration as YAML.
 * Supports validation before import.
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Inject, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';

import { LucideAngularModule } from 'lucide-angular';
import { SystemConfigService } from '../../services/system-config.service';

export interface ConfigImportExportDialogData {
  mode: 'import' | 'export';
}

@Component({
  selector: 'app-config-import-export',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTabsModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './config-import-export.component.html',
  styleUrls: ['./config-import-export.component.scss'],
})
export class ConfigImportExportComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  configYaml = '';
  isLoading = false;
  validationErrors: string[] = [];
  isValid = false;

  constructor(
    public dialogRef: MatDialogRef<ConfigImportExportComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfigImportExportDialogData,
    private configService: SystemConfigService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    if (this.data.mode === 'export') {
      this.exportConfig();
    }
  }

  /**
   * Export configuration
   */
  exportConfig(): void {
    this.isLoading = true;

    this.configService.exportConfig().subscribe({
      next: (response) => {
        this.configYaml = response.config_yaml;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.snackBar.open('Failed to export configuration', 'Close', {
          duration: 5000,
        });
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  /**
   * Validate YAML before import
   */
  validateYaml(): void {
    if (!this.configYaml.trim()) {
      this.snackBar.open('Please enter YAML configuration', 'Close', {
        duration: 3000,
      });
      return;
    }

    this.isLoading = true;
    this.validationErrors = [];

    this.configService.validateConfigYaml(this.configYaml).subscribe({
      next: (response) => {
        if (response.success) {
          this.isValid = true;
          this.validationErrors = [];
          this.snackBar.open('Configuration is valid', 'Close', {
            duration: 3000,
          });
        } else {
          this.isValid = false;
          this.validationErrors = response.validation_errors || [];
        }
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isValid = false;
        this.validationErrors = [err.error?.detail || 'Validation failed'];
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  /**
   * Import configuration
   */
  importConfig(): void {
    if (!this.configYaml.trim()) {
      this.snackBar.open('Please enter YAML configuration', 'Close', {
        duration: 3000,
      });
      return;
    }

    this.isLoading = true;

    this.configService
      .importConfig({
        config_yaml: this.configYaml,
        validate_only: false,
      })
      .subscribe({
        next: (response) => {
          this.dialogRef.close({ success: true, response });
          this.snackBar.open('Configuration imported successfully', 'Close', {
            duration: 5000,
          });
        },
        error: (err) => {
          this.validationErrors = [err.error?.detail || 'Import failed'];
          this.isLoading = false;
          this.cdr.detectChanges();
          this.snackBar.open('Failed to import configuration', 'Close', {
            duration: 5000,
          });
        },
      });
  }

  /**
   * Copy YAML to clipboard
   */
  copyToClipboard(): void {
    navigator.clipboard.writeText(this.configYaml).then(() => {
      this.snackBar.open('Copied to clipboard', 'Close', {
        duration: 2000,
      });
    });
  }

  /**
   * Download YAML file
   */
  downloadYaml(): void {
    const blob = new Blob([this.configYaml], {
      type: 'application/x-yaml',
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `system-config-${new Date().toISOString()}.yaml`;
    a.click();
    window.URL.revokeObjectURL(url);

    this.snackBar.open('Configuration downloaded', 'Close', {
      duration: 2000,
    });
  }

  /**
   * Close dialog
   */
  close(): void {
    this.dialogRef.close();
  }
}
