/**
 * Tool Management Component
 *
 * Admin interface for managing Tools Track MCP tools.
 * Follows ADR-012 Layered Page Layout Pattern.
 */

import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';

import { ToolDeleteDialogComponent } from './components/tool-delete-dialog/tool-delete-dialog.component';
import { ToolDetailsDialogComponent } from './components/tool-details-dialog/tool-details-dialog.component';
import { ToolEditDialogComponent } from './components/tool-edit-dialog/tool-edit-dialog.component';
import {
  ToolCategory,
  ToolFilters,
  ToolListItem,
} from './models/tool-management.models';
import { ToolAdminService } from './services/tool-admin.service';

@Component({
  selector: 'app-tool-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatTableModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatChipsModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
  ],
  templateUrl: './tool-management.component.html',
  styleUrls: ['./tool-management.component.scss'],
})
export class ToolManagementComponent implements OnInit {
  tools: ToolListItem[] = [];
  filteredTools: ToolListItem[] = [];
  isLoading = false;
  error: string | null = null;

  filters: ToolFilters = {
    enabled_only: false,
    healthy_only: false,
  };

  searchTerm = '';
  private searchSubject = new Subject<string>();

  categories: ToolCategory[] = [
    'database',
    'vector_db',
    'web_scraping',
    'reasoning',
    'documentation',
    'code_analysis',
    'threat_intel',
    'custom',
  ];

  displayedColumns: string[] = [
    'tool_id',
    'name',
    'category',
    'provider',
    'status',
    'health',
    'actions',
  ];

  constructor(
    private toolService: ToolAdminService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadTools();

    // Debounce search input
    this.searchSubject
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe((searchTerm) => {
        this.filters.search = searchTerm || undefined;
        this.applyFilters();
      });
  }

  loadTools(): void {
    this.isLoading = true;
    this.error = null;

    this.toolService.listTools(this.filters).subscribe({
      next: (tools) => {
        this.tools = tools;
        this.applyFilters();
        this.isLoading = false;
      },
      error: (err) => {
        this.error = 'Failed to load tools';
        this.isLoading = false;
        console.error('Error loading tools:', err);
        this.snackBar.open('Failed to load tools', 'Close', {
          duration: 5000,
        });
      },
    });
  }

  onSearchChange(): void {
    this.searchSubject.next(this.searchTerm);
  }

  onFilterChange(): void {
    this.loadTools();
  }

  applyFilters(): void {
    let filtered = [...this.tools];

    // Client-side search filter
    if (this.filters.search) {
      const searchLower = this.filters.search.toLowerCase();
      filtered = filtered.filter(
        (tool) =>
          tool.name.toLowerCase().includes(searchLower) ||
          tool.tool_id.toLowerCase().includes(searchLower)
      );
    }

    this.filteredTools = filtered;
  }

  openDetailsDialog(tool: ToolListItem): void {
    const dialogRef = this.dialog.open(ToolDetailsDialogComponent, {
      width: '800px',
      data: { toolId: tool.id },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result?.edit) {
        this.openEditDialog(tool);
      }
    });
  }

  openEditDialog(tool: ToolListItem): void {
    const dialogRef = this.dialog.open(ToolEditDialogComponent, {
      width: '600px',
      data: { toolId: tool.id },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.snackBar.open('Tool updated successfully', 'Close', {
          duration: 3000,
        });
        this.loadTools();
      }
    });
  }

  openDeleteDialog(tool: ToolListItem): void {
    const dialogRef = this.dialog.open(ToolDeleteDialogComponent, {
      width: '400px',
      data: { tool },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.snackBar.open('Tool deleted successfully', 'Close', {
          duration: 3000,
        });
        this.loadTools();
      }
    });
  }

  toggleTool(tool: ToolListItem): void {
    const action = tool.is_enabled
      ? this.toolService.disableTool(tool.id)
      : this.toolService.enableTool(tool.id);

    action.subscribe({
      next: () => {
        tool.is_enabled = !tool.is_enabled;
        this.snackBar.open(
          `Tool ${tool.is_enabled ? 'enabled' : 'disabled'}`,
          'Close',
          { duration: 2000 }
        );
      },
      error: (err) => {
        console.error('Error toggling tool:', err);
        this.snackBar.open('Failed to update tool', 'Close', {
          duration: 3000,
        });
      },
    });
  }

  triggerHealthCheck(tool: ToolListItem): void {
    this.snackBar.open('Checking tool health...', '', { duration: 1000 });

    this.toolService.triggerHealthCheck(tool.id).subscribe({
      next: () => {
        this.snackBar.open('Health check completed', 'Close', {
          duration: 3000,
        });
        this.loadTools();
      },
      error: (err) => {
        console.error('Error checking tool health:', err);
        this.snackBar.open('Failed to check tool health', 'Close', {
          duration: 3000,
        });
      },
    });
  }

  navigateToRegistration(): void {
    this.router.navigate(['/admin/tools/register']);
  }

  refreshTools(): void {
    this.loadTools();
  }

  getHealthIcon(tool: ToolListItem): string {
    if (!tool.is_healthy) return 'error';
    return 'check_circle';
  }

  getHealthClass(tool: ToolListItem): string {
    if (!tool.is_healthy) return 'health-error';
    return 'health-ok';
  }

  getCategoryClass(category: ToolCategory): string {
    return `category-${category}`;
  }
}
