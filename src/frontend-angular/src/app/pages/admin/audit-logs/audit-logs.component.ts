import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { AuditLogDetailsDialogComponent } from './components/audit-log-details-dialog/audit-log-details-dialog.component';
import {
  AuditLogDateRange,
  AuditLogEntry,
  AuditLogFilters,
  AuditLogStatsResponse,
} from './models/audit-logs.models';
import { AuditLogsService } from './services/audit-logs.service';

/**
 * Audit Logs Component
 *
 * Admin interface for viewing and filtering audit logs.
 * Follows ADR-012 Layered Page Layout Pattern.
 *
 * **Features:**
 * - Comprehensive filtering (date range, user, action, resource type)
 * - Full-text search
 * - Pagination
 * - Statistics dashboard
 * - Detailed log viewer
 *
 * **Authorization:** Admin, Developer, or Corpus Admin
 */
@Component({
  selector: 'app-audit-logs',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatChipsModule,
    MatTooltipModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatDatepickerModule,
    MatNativeDateModule,
  ],
  templateUrl: './audit-logs.component.html',
  styleUrls: ['./audit-logs.component.scss'],
})
export class AuditLogsComponent implements OnInit {
  logs: AuditLogEntry[] = [];
  totalLogs = 0;
  isLoading = false;
  error: string | null = null;

  // Statistics
  stats: AuditLogStatsResponse | null = null;
  isLoadingStats = false;
  showStats = false;

  // Date range
  dateRange: AuditLogDateRange = {
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end: new Date(),
  };

  filters: AuditLogFilters = {
    page: 1,
    page_size: 50,
    search: '',
    action: '',
    resource_type: '',
    success: undefined,
  };

  displayedColumns: string[] = [
    'event_time',
    'actor_username',
    'action',
    'resource_type',
    'success',
    'details',
  ];

  // Filter options
  resourceTypes: string[] = [
    '',
    'http_request',
    'use_case',
    'user',
    'collection',
    'document',
    'query',
  ];

  constructor(
    private auditService: AuditLogsService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadLogs();
    this.loadStats();
  }

  loadLogs(): void {
    this.isLoading = true;
    this.error = null;

    // Convert dates to ISO strings
    const apiFilters = {
      ...this.filters,
      start_date: this.dateRange.start.toISOString(),
      end_date: this.dateRange.end.toISOString(),
    };

    this.auditService.listAuditLogs(apiFilters).subscribe({
      next: (response) => {
        this.logs = response.logs;
        this.totalLogs = response.total;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = 'Failed to load audit logs';
        this.isLoading = false;
        console.error('Error loading audit logs:', err);
      },
    });
  }

  loadStats(): void {
    this.isLoadingStats = true;

    const statsFilters = {
      start_date: this.dateRange.start.toISOString(),
      end_date: this.dateRange.end.toISOString(),
      resource_type: this.filters.resource_type || undefined,
    };

    this.auditService.getStats(statsFilters).subscribe({
      next: (response) => {
        this.stats = response;
        this.isLoadingStats = false;
      },
      error: (err) => {
        console.error('Error loading stats:', err);
        this.isLoadingStats = false;
      },
    });
  }

  onSearch(searchTerm: string): void {
    this.filters.search = searchTerm;
    this.filters.page = 1;
    this.loadLogs();
  }

  onFilterChange(): void {
    this.filters.page = 1;
    this.loadLogs();
    this.loadStats();
  }

  onDateRangeChange(): void {
    this.filters.page = 1;
    this.loadLogs();
    this.loadStats();
  }

  onPageChange(event: PageEvent): void {
    this.filters.page_size = event.pageSize;
    this.filters.page = event.pageIndex + 1;
    this.loadLogs();
  }

  clearFilters(): void {
    this.filters = {
      page: 1,
      page_size: 50,
      search: '',
      action: '',
      resource_type: '',
      success: undefined,
    };
    this.dateRange = {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      end: new Date(),
    };
    this.loadLogs();
    this.loadStats();
  }

  toggleStats(): void {
    this.showStats = !this.showStats;
    if (this.showStats && !this.stats) {
      this.loadStats();
    }
  }

  openDetailsDialog(log: AuditLogEntry): void {
    this.dialog.open(AuditLogDetailsDialogComponent, {
      width: '800px',
      data: { log },
    });
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  getStatusColor(success: boolean): string {
    return success ? 'primary' : 'warn';
  }

  getStatusIcon(success: boolean): string {
    return success ? 'circle-check' : 'circle-alert';
  }

  getSuccessRate(): number {
    if (!this.stats || this.stats.total_events === 0) {
      return 0;
    }
    return (this.stats.success_count / this.stats.total_events) * 100;
  }
}
