/**
 * Provider Management Component
 *
 * Admin interface for managing Inference Gateway providers.
 * Follows ADR-012 Layered Page Layout Pattern.
 */

import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { ProviderCreateDialogComponent } from './components/provider-create-dialog/provider-create-dialog.component';
import { ProviderEditDialogComponent } from './components/provider-edit-dialog/provider-edit-dialog.component';
import {
  ProviderConfig,
  ProviderFilters,
} from './models/provider-management.models';
import { ProviderManagementService } from './services/provider-management.service';

@Component({
  selector: 'app-provider-management',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatDialogModule,
    MatButtonModule,
    MatSelectModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
  ],
  templateUrl: './provider-management.component.html',
  styleUrls: ['./provider-management.component.scss'],
})
export class ProviderManagementComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  providers: ProviderConfig[] = [];
  totalProviders = 0;
  isLoading = false;
  error: string | null = null;

  filters: ProviderFilters = {
    limit: 20,
    offset: 0,
    enabled_only: false,
  };

  displayedColumns: string[] = [
    'name',
    'provider_type',
    'status',
    'priority',
    'health',
    'circuit_state',
    'is_enabled',
    'actions',
  ];

  constructor(
    private providerService: ProviderManagementService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadProviders();
  }

  loadProviders(): void {
    this.isLoading = true;
    this.error = null;

    this.providerService.listProviders(this.filters).subscribe({
      next: (response) => {
        this.providers = response.items;
        this.totalProviders = response.total;
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
      error: (err) => {
        this.error = 'Failed to load providers';
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
        console.error('Error loading providers:', err);
        this.snackBar.open('Failed to load providers', 'Close', {
          duration: 5000,
        });
      },
    });
  }

  onFilterChange(): void {
    this.filters.offset = 0;
    this.loadProviders();
  }

  onPageChange(event: PageEvent): void {
    this.filters.limit = event.pageSize;
    this.filters.offset = event.pageIndex * event.pageSize;
    this.loadProviders();
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(ProviderCreateDialogComponent, {
      width: '600px',
      disableClose: false,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.snackBar.open('Provider created successfully', 'Close', {
          duration: 3000,
        });
        this.loadProviders();
      }
    });
  }

  openEditDialog(provider: ProviderConfig): void {
    const dialogRef = this.dialog.open(ProviderEditDialogComponent, {
      width: '600px',
      data: { provider },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.snackBar.open('Provider updated successfully', 'Close', {
          duration: 3000,
        });
        this.loadProviders();
      }
    });
  }

  toggleProvider(provider: ProviderConfig): void {
    if (!provider.id) return;

    const newStatus = !provider.is_enabled;

    this.providerService
      .updateProvider(provider.id, { is_enabled: newStatus })
      .subscribe({
        next: () => {
          provider.is_enabled = newStatus;
          this.snackBar.open(
            `Provider ${newStatus ? 'enabled' : 'disabled'}`,
            'Close',
            { duration: 2000 }
          );
        },
        error: (err) => {
          console.error('Error toggling provider:', err);
          this.snackBar.open('Failed to update provider', 'Close', {
            duration: 3000,
          });
        },
      });
  }

  testProvider(provider: ProviderConfig): void {
    if (!provider.id) return;

    this.snackBar.open('Testing provider...', '', { duration: 1000 });

    this.providerService.testProvider(provider.id).subscribe({
      next: (result) => {
        if (result.success) {
          this.snackBar.open(`Test successful: ${result.message}`, 'Close', {
            duration: 3000,
          });
          this.loadProviders();
        } else {
          this.snackBar.open(`Test failed: ${result.message}`, 'Close', {
            duration: 5000,
          });
        }
      },
      error: (err) => {
        console.error('Error testing provider:', err);
        this.snackBar.open('Failed to test provider connectivity', 'Close', {
          duration: 3000,
        });
      },
    });
  }

  deleteProvider(provider: ProviderConfig): void {
    if (!provider.id) return;

    if (!confirm(`Delete provider "${provider.name}"?`)) {
      return;
    }

    this.providerService.deleteProvider(provider.id).subscribe({
      next: () => {
        this.snackBar.open('Provider deleted successfully', 'Close', {
          duration: 3000,
        });
        this.loadProviders();
      },
      error: (err) => {
        console.error('Error deleting provider:', err);
        this.snackBar.open('Failed to delete provider', 'Close', {
          duration: 3000,
        });
      },
    });
  }

  getHealthStatusIcon(provider: ProviderConfig): string {
    if (!provider.last_health_check) return 'circle-help';
    return provider.last_health_status ? 'circle-check' : 'circle-alert';
  }

  getHealthStatusClass(provider: ProviderConfig): string {
    if (!provider.last_health_check) return 'health-unknown';
    return provider.last_health_status ? 'health-ok' : 'health-error';
  }

  getCircuitStateClass(state?: string): string {
    switch (state) {
      case 'CLOSED':
        return 'circuit-closed';
      case 'OPEN':
        return 'circuit-open';
      case 'HALF_OPEN':
        return 'circuit-half-open';
      default:
        return 'circuit-unknown';
    }
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'active':
        return 'status-active';
      case 'disabled':
        return 'status-disabled';
      case 'error':
        return 'status-error';
      case 'testing':
        return 'status-testing';
      default:
        return 'status-unknown';
    }
  }
}
