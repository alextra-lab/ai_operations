/**
 * Table Visualizer Component
 *
 * Renders data as a Material table with sorting, filtering, pagination,
 * and export capabilities (CSV, JSON, Excel). Supports tabbed mode for
 * multi-table data (e.g. one tab per category).
 */

import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  ViewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  TableColumn,
  TableConfig,
} from '../../../models/output-format.model';

/** Per-tab state when in tabbed mode */
export interface TabbedTableTab {
  label: string;
  data: unknown[];
  columns: TableColumn[];
  displayedColumns: string[];
  dataSource: MatTableDataSource<unknown>;
}

@Component({
  selector: 'app-table-visualizer',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
  ],
  templateUrl: './table-visualizer.component.html',
  styleUrls: ['./table-visualizer.component.scss'],
})
export class TableVisualizerComponent implements OnInit, AfterViewInit {
  @Input() data: unknown[] = [];
  @Input() config!: TableConfig;
  @Input() title = '';

  @Output() actionClick = new EventEmitter<{
    handler: string;
    data: unknown;
  }>();

  dataSource!: MatTableDataSource<unknown>;
  displayedColumns: string[] = [];

  /** When config.tabbed is true, one entry per tab */
  tabs: TabbedTableTab[] = [];

  @ViewChild(MatPaginator) paginator?: MatPaginator;
  @ViewChild(MatSort) sort?: MatSort;

  get isTabbed(): boolean {
    return !!(
      this.config?.tabbed &&
      this.config.tab_title_field &&
      this.config.tab_data_field
    );
  }

  ngOnInit(): void {
    if (this.isTabbed && Array.isArray(this.data) && this.data.length > 0) {
      this.buildTabbedState();
      return;
    }

    // Auto-generate columns if not specified
    if (!this.config.columns || this.config.columns.length === 0) {
      this.autoGenerateColumns();
    }

    // Initialize data source
    this.dataSource = new MatTableDataSource(this.data || []);

    // Set displayed columns
    this.displayedColumns = this.config.columns.map((c) => c.field);

    // Add actions column if actions are defined
    if (this.config.actions && this.config.actions.length > 0) {
      this.displayedColumns.push('actions');
    }
  }

  /**
   * Build tabs when config is tabbed; each tab shows a table of rows.
   */
  private buildTabbedState(): void {
    const titleField = this.config.tab_title_field as string;
    const dataField = this.config.tab_data_field as string;

    this.tabs = (this.data as Record<string, unknown>[])
      .filter((item) => {
        const rows = item[dataField];
        return Array.isArray(rows) && rows.length > 0;
      })
      .map((item) => {
        const label = item[titleField];
        const rows = (item[dataField] as unknown[]) || [];
        const columns = this.deriveColumnsFromRows(rows);
        const displayedColumns = columns.map((c) => c.field);
        if (
          this.config.actions &&
          this.config.actions.length > 0
        ) {
          displayedColumns.push('actions');
        }
        const dataSource = new MatTableDataSource(rows);
        return {
          label: typeof label === 'string' ? label : String(label ?? ''),
          data: rows,
          columns,
          displayedColumns,
          dataSource,
        };
      });

    // Ensure at least one dataSource for non-tabbed code path (unused in tabbed view)
    this.dataSource = new MatTableDataSource<unknown>([]);
    this.displayedColumns = [];
  }

  /**
   * Derive table columns from first row of a row array
   */
  private deriveColumnsFromRows(rows: unknown[]): TableColumn[] {
    if (!rows || rows.length === 0) {
      return [];
    }
    const first = rows[0] as Record<string, unknown>;
    return Object.keys(first).map((key) => ({
      field: key,
      header: this.formatHeaderName(key),
      sortable: true,
    }));
  }

  ngAfterViewInit(): void {
    if (this.isTabbed) {
      return;
    }
    // Set up pagination if enabled
    if (this.config.paginated !== false && this.paginator) {
      this.dataSource.paginator = this.paginator;
    }

    // Set up sorting if enabled
    if (this.config.sortable !== false && this.sort) {
      this.dataSource.sort = this.sort;
    }
  }

  /**
   * Auto-generate columns from data structure
   */
  private autoGenerateColumns(): void {
    if (!this.data || this.data.length === 0) {
      this.config.columns = [];
      return;
    }

    const firstRow = this.data[0] as Record<string, unknown>;
    this.config.columns = Object.keys(firstRow).map((key) => ({
      field: key,
      header: this.formatHeaderName(key),
      sortable: true,
    }));
  }

  /**
   * Format field name as header (camelCase → Title Case)
   */
  private formatHeaderName(field: string): string {
    return field
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, (str) => str.toUpperCase())
      .trim();
  }

  /**
   * Apply filter to table
   */
  applyFilter(event: Event): void {
    const filterValue = (event.target as HTMLInputElement).value;
    this.dataSource.filter = filterValue.trim().toLowerCase();

    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }
  }

  /**
   * Apply filter to a specific tab's data source
   */
  applyFilterTab(event: Event, tab: TabbedTableTab): void {
    const filterValue = (event.target as HTMLInputElement).value
      .trim()
      .toLowerCase();
    tab.dataSource.filter = filterValue;
    if (tab.dataSource.paginator) {
      tab.dataSource.paginator.firstPage();
    }
  }

  /**
   * Copy value to clipboard
   */
  async copyToClipboard(value: unknown): Promise<void> {
    try {
      const text = String(value);
      await navigator.clipboard.writeText(text);
      // TODO: Show snackbar notification
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  }

  /**
   * Handle action click
   */
  handleAction(handler: string, row: unknown): void {
    this.actionClick.emit({ handler, data: row });
  }

  /**
   * Export data to specified format
   */
  exportData(format: string): void {
    switch (format) {
      case 'csv':
        this.exportCSV();
        break;
      case 'json':
        this.exportJSON();
        break;
      case 'excel':
        this.exportExcel();
        break;
      default:
        console.error('Unsupported export format:', format);
    }
  }

  /**
   * Export data as CSV
   */
  private exportCSV(): void {
    const csv = this.convertToCSV(this.data);
    this.downloadFile(csv, 'data.csv', 'text/csv');
  }

  /**
   * Export data as JSON
   */
  private exportJSON(): void {
    const json = JSON.stringify(this.data, null, 2);
    this.downloadFile(json, 'data.json', 'application/json');
  }

  /**
   * Export data as Excel (CSV with .xlsx extension)
   * Note: For true Excel format, would need xlsx library
   */
  private exportExcel(): void {
    const csv = this.convertToCSV(this.data);
    this.downloadFile(csv, 'data.xlsx', 'text/csv');
  }

  /**
   * Convert data to CSV format
   */
  private convertToCSV(data: unknown[]): string {
    if (!data || data.length === 0) {
      return '';
    }

    const headers = this.config.columns.map((c) => c.header).join(',');

    const rows = data.map((row) => {
      const record = row as Record<string, unknown>;
      return this.config.columns
        .map((c) => {
          const value = record[c.field];
          const stringValue =
            value === null || value === undefined ? '' : String(value);
          // Escape quotes and wrap in quotes if contains comma
          return stringValue.includes(',')
            ? `"${stringValue.replace(/"/g, '""')}"`
            : stringValue;
        })
        .join(',');
    });

    return [headers, ...rows].join('\n');
  }

  /**
   * Trigger file download
   */
  private downloadFile(
    content: string,
    filename: string,
    mimeType: string
  ): void {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  /**
   * Get cell value for display. Objects/arrays are stringified so they never render as [object Object].
   */
  getCellValue(row: unknown, field: string): unknown {
    const record = row as Record<string, unknown>;
    return record[field];
  }

  /**
   * Format cell value for template display (avoids [object Object] for objects/arrays)
   */
  formatCellDisplay(value: unknown): string {
    if (value === null || value === undefined) {
      return '';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  }
}
