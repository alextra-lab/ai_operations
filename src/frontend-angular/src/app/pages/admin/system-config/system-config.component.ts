/**
 * System Configuration Component
 *
 * Main page for system configuration management.
 * Follows ADR-012 Layered Page Layout Pattern.
 */

import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { ModelRegistryService } from '../../../api/services/model-registry.service';
import { ConfigImportExportComponent } from './components/config-import-export/config-import-export.component';
import { ConfigSectionComponent } from './components/config-section/config-section.component';
import {
  CONFIG_SECTIONS,
  ConfigSection,
  ConfigSectionMetadata,
  SystemConfigFull,
} from './models/system-config.models';
import { SystemConfigService } from './services/system-config.service';

/**
 * System Configuration Component
 *
 * Admin interface for managing system configuration.
 * Supports section-based editing, export/import, and validation.
 */
@Component({
  selector: 'app-system-config',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    MatButtonModule,
    MatExpansionModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatDialogModule,
    ConfigSectionComponent,
  ],
  templateUrl: './system-config.component.html',
  styleUrls: ['./system-config.component.scss'],
})
export class SystemConfigComponent implements OnInit {
  config: SystemConfigFull | null = null;
  sections = CONFIG_SECTIONS;
  isLoading = false;
  error: string | null = null;
  modifiedSections = new Set<ConfigSection>();
  restartRequired = false;

  configHealth: {
    isHealthy: boolean;
    issues: string[];
  } = { isHealthy: true, issues: [] };

  constructor(
    private configService: SystemConfigService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private modelRegistryService: ModelRegistryService
  ) {}

  ngOnInit(): void {
    this.loadConfig();
  }

  /**
   * Check configuration health
   */
  checkConfigHealth(): void {
    this.modelRegistryService.getEmbeddingModels().subscribe({
      next: (models: { model_id: string; is_available: boolean }[]) => {
        if (this.config?.corpus) {
          const configuredModel = this.config.corpus.default_embedding_model;
          const modelExists = models.some(
            (m) => m.model_id === configuredModel && m.is_available
          );

          if (!modelExists) {
            this.configHealth.isHealthy = false;
            this.configHealth.issues = [
              `Default embedding model '${configuredModel}' is not available. New collections cannot be created.`,
            ];
          } else {
            this.configHealth.isHealthy = true;
            this.configHealth.issues = [];
          }
        }
      },
      error: (err: Error) => {
        console.error('Error checking config health', err);
      },
    });
  }

  /**
   * Load all configuration
   */
  loadConfig(): void {
    this.isLoading = true;
    this.error = null;

    this.configService.getConfig().subscribe({
      next: (config) => {
        this.config = config;
        this.isLoading = false;
        this.checkConfigHealth();
      },
      error: (err) => {
        this.error = 'Failed to load configuration';
        this.isLoading = false;
        this.snackBar.open('Failed to load configuration', 'Close', {
          duration: 5000,
        });
      },
    });
  }

  /**
   * Get configuration for specific section
   */
  getSectionConfig(section: ConfigSection): Record<string, unknown> | null {
    return this.config
      ? (this.config[section] as unknown as Record<string, unknown>)
      : null;
  }

  /**
   * Get section metadata
   */
  getSectionMetadata(section: ConfigSection): ConfigSectionMetadata {
    return this.sections.find((s) => s.section === section)!;
  }

  /**
   * Handle section configuration change
   */
  onSectionChange(
    section: ConfigSection,
    config: Record<string, unknown>
  ): void {
    if (this.config) {
      this.config[section] = config as never;
      this.modifiedSections.add(section);
    }
  }

  /**
   * Save all modified sections
   */
  saveAll(): void {
    if (this.modifiedSections.size === 0) {
      this.snackBar.open('No changes to save', 'Close', {
        duration: 3000,
      });
      return;
    }

    this.isLoading = true;
    let savedCount = 0;
    let errorCount = 0;
    let requiresRestart = false;

    this.modifiedSections.forEach((section) => {
      const config = this.getSectionConfig(section);
      if (config) {
        this.configService.updateConfigSection(section, config).subscribe({
          next: (response) => {
            savedCount++;
            if (response.restart_required) {
              requiresRestart = true;
            }
            this.checkSaveComplete(savedCount, errorCount, requiresRestart);
          },
          error: () => {
            errorCount++;
            this.checkSaveComplete(savedCount, errorCount, requiresRestart);
          },
        });
      }
    });
  }

  /**
   * Check if all sections have been saved
   */
  private checkSaveComplete(
    savedCount: number,
    errorCount: number,
    requiresRestart: boolean
  ): void {
    const total = this.modifiedSections.size;
    if (savedCount + errorCount === total) {
      this.isLoading = false;
      this.modifiedSections.clear();
      this.restartRequired = requiresRestart;

      if (errorCount > 0) {
        this.snackBar.open(
          `Saved ${savedCount}/${total} sections (${errorCount} errors)`,
          'Close',
          { duration: 5000 }
        );
      } else {
        const message = requiresRestart
          ? 'Configuration saved. Restart required.'
          : 'Configuration saved successfully';
        this.snackBar.open(message, 'Close', { duration: 5000 });
      }
    }
  }

  /**
   * Reset all sections to current saved values
   */
  resetAll(): void {
    this.modifiedSections.clear();
    this.loadConfig();
    this.snackBar.open('Configuration reset', 'Close', { duration: 3000 });
  }

  /**
   * Open export dialog
   */
  openExportDialog(): void {
    const dialogRef = this.dialog.open(ConfigImportExportComponent, {
      width: '800px',
      data: { mode: 'export' },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result?.success) {
        this.snackBar.open('Configuration exported', 'Close', {
          duration: 3000,
        });
      }
    });
  }

  /**
   * Open import dialog
   */
  openImportDialog(): void {
    const dialogRef = this.dialog.open(ConfigImportExportComponent, {
      width: '800px',
      data: { mode: 'import' },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result?.success) {
        this.loadConfig();
        this.snackBar.open('Configuration imported', 'Close', {
          duration: 3000,
        });
      }
    });
  }

  /**
   * Check if any sections are modified
   */
  hasChanges(): boolean {
    return this.modifiedSections.size > 0;
  }
}
