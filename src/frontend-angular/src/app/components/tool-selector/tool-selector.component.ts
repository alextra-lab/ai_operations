import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import {
  ToolCategory,
  ToolListItem,
  ToolStatus,
} from '../../api/models/tool.models';
import { ToolDeveloperService } from '../../api/services/tool-developer.service';

@Component({
  selector: 'app-tool-selector',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './tool-selector.component.html',
  styleUrls: ['./tool-selector.component.scss'],
})
export class ToolSelectorComponent implements OnInit {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  @Input() selectedToolIds: string[] = [];
  @Output() selectionChange = new EventEmitter<string[]>();

  tools: ToolListItem[] = [];
  filteredTools: ToolListItem[] = [];
  isLoading = false;
  error: string | null = null;

  // Filters
  searchTerm = '';
  selectedCategory: string | null = null;

  // Enum access for template
  ToolStatus = ToolStatus;

  // Categories derived from loaded tools
  availableCategories: string[] = [];

  constructor(private toolService: ToolDeveloperService) {}

  ngOnInit(): void {
    this.loadTools();
  }

  loadTools(): void {
    this.isLoading = true;
    this.toolService.listAvailableTools().subscribe({
      next: (tools) => {
        this.tools = tools;
        this.extractCategories();
        this.filterTools();
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
      error: (err) => {
        console.error('Error loading tools:', err);
        this.error = 'Failed to load available tools';
        this.isLoading = false;
        queueMicrotask(() => this.cdr.detectChanges());
      },
    });
  }

  extractCategories(): void {
    const cats = new Set(this.tools.map((t) => t.category));
    this.availableCategories = Array.from(cats).sort();
  }

  filterTools(): void {
    this.filteredTools = this.tools.filter((tool) => {
      const matchesSearch =
        !this.searchTerm ||
        tool.name.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        (tool.description &&
          tool.description
            .toLowerCase()
            .includes(this.searchTerm.toLowerCase()));

      const matchesCategory =
        !this.selectedCategory || tool.category === this.selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }

  toggleTool(toolId: string): void {
    const index = this.selectedToolIds.indexOf(toolId);
    if (index > -1) {
      this.selectedToolIds = this.selectedToolIds.filter((id) => id !== toolId);
    } else {
      this.selectedToolIds = [...this.selectedToolIds, toolId];
    }
    this.selectionChange.emit(this.selectedToolIds);
  }

  isSelected(toolId: string): boolean {
    return this.selectedToolIds.includes(toolId);
  }

  getCategoryIcon(category: string): string {
    switch (category) {
      case ToolCategory.DATABASE:
        return 'server';
      case ToolCategory.VECTOR_DB:
        return 'database';
      case ToolCategory.WEB_SCRAPING:
        return 'globe';
      case ToolCategory.REASONING:
        return 'brain-circuit';
      case ToolCategory.DOCUMENTATION:
        return 'file-text';
      case ToolCategory.CODE_ANALYSIS:
        return 'code';
      case ToolCategory.THREAT_INTEL:
        return 'shield';
      case ToolCategory.CUSTOM:
        return 'blocks';
      default:
        return 'wrench';
    }
  }

  getCategoryLabel(category: string): string {
    return category
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }
}
