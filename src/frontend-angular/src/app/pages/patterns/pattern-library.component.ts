/**
 * Pattern Library Component
 * Browse, search, and preview reusable prompt engineering patterns
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { debounceTime, distinctUntilChanged, Subject, takeUntil } from 'rxjs';

import {
  PATTERN_CATEGORIES,
  PromptPattern,
  PromptPatternListResponse,
} from '../../api/models/prompt-patterns.models';
import { PromptPatternsService } from '../../api/services/prompt-patterns.service';
import { PatternDetailDialogComponent } from './pattern-detail-dialog.component';

@Component({
  selector: 'app-pattern-library',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './pattern-library.component.html',
  styleUrls: ['./pattern-library.component.scss'],
})
export class PatternLibraryComponent implements OnInit, OnDestroy {
  patterns: PromptPattern[] = [];
  loading = false;
  error: string | null = null;

  // View mode and pagination
  viewMode: 'grid' | 'list' = 'grid';
  totalPatterns = 0;
  pageSize = 9;
  currentPage = 1;
  totalPages = 0;
  itemsPerPageOptions = [9, 12, 15, 18, 21];

  // Filters
  searchControl = new FormControl('');
  categoryControl = new FormControl<string | null>(null);
  sortByControl = new FormControl<
    'name' | 'category' | 'use_count' | 'created_at'
  >('use_count');
  sortOrderControl = new FormControl<'asc' | 'desc'>('desc');

  categories = PATTERN_CATEGORIES;

  private destroy$ = new Subject<void>();

  constructor(
    private patternsService: PromptPatternsService,
    private dialog: MatDialog
  ) { }

  ngOnInit(): void {
    // Load saved preferences
    this.loadViewPreferences();

    // Setup search debouncing
    this.searchControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(() => {
        this.currentPage = 1;
        this.loadPatterns();
      });

    // Setup filter change handlers
    this.categoryControl.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.currentPage = 1;
        this.loadPatterns();
      });

    this.sortByControl.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.loadPatterns();
      });

    this.sortOrderControl.valueChanges
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.loadPatterns();
      });

    // Initial load
    this.loadPatterns();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadPatterns(): void {
    this.loading = true;
    this.error = null;

    const params = {
      search: this.searchControl.value || undefined,
      category: this.categoryControl.value || undefined,
      page: this.currentPage,
      page_size: this.pageSize,
      sort_by: this.sortByControl.value || 'use_count',
      sort_order: this.sortOrderControl.value || 'desc',
    };

    this.patternsService.listPatterns(params).subscribe({
      next: (response: PromptPatternListResponse) => {
        this.patterns = response.patterns;
        this.totalPatterns = response.total;
        this.totalPages = response.total_pages;
        this.loading = false;
      },
      error: (error) => {
        console.error('Failed to load patterns:', error);
        this.error = 'Failed to load pattern library. Please try again.';
        this.loading = false;
      },
    });
  }

  onPageChange(event: PageEvent): void {
    this.currentPage = event.pageIndex + 1;
    this.pageSize = event.pageSize;
    this.loadPatterns();
  }

  clearFilters(): void {
    this.searchControl.setValue('');
    this.categoryControl.setValue(null);
    this.sortByControl.setValue('use_count');
    this.sortOrderControl.setValue('desc');
    this.currentPage = 1;
    this.loadPatterns();
  }

  viewPattern(pattern: PromptPattern): void {
    this.dialog.open(PatternDetailDialogComponent, {
      width: '800px',
      maxHeight: '90vh',
      data: { pattern },
    });
  }

  getCategoryInfo(categoryId: string) {
    return (
      this.categories.find((c) => c.id === categoryId) || {
        id: categoryId,
        label: categoryId,
        icon: 'category',
        description: '',
        color: '#757575',
      }
    );
  }

  copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text).catch(() => undefined);
  }

  // View mode and preferences
  onViewModeChange(mode: 'grid' | 'list'): void {
    this.viewMode = mode;
    this.saveViewPreferences();
  }

  onItemsPerPageChange(): void {
    this.currentPage = 1;
    this.saveViewPreferences();
    this.loadPatterns();
  }

  private loadViewPreferences(): void {
    const saved = localStorage.getItem('pattern-library-preferences');
    if (saved) {
      try {
        const preferences = JSON.parse(saved);
        this.viewMode = preferences.viewMode || 'grid';
        this.pageSize = preferences.pageSize || 9;
      } catch (e) {
        console.warn('Failed to load view preferences:', e);
      }
    }
  }

  private saveViewPreferences(): void {
    const preferences = {
      viewMode: this.viewMode,
      pageSize: this.pageSize,
    };
    localStorage.setItem(
      'pattern-library-preferences',
      JSON.stringify(preferences)
    );
  }
}
