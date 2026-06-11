import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Observable, Subject, takeUntil } from 'rxjs';
import { debounceTime, distinctUntilChanged, startWith } from 'rxjs/operators';

// Angular Material imports
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatOptionModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';

import { LucideAngularModule } from 'lucide-angular';
import { UseCase } from '../../api/models/use-case.models';
import { UseCaseService } from '../../api/services/use-case.service';

@Component({
  selector: 'app-use-case-menu',
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatOptionModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatPaginatorModule,
    MatTooltipModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatListModule,
  ],
  templateUrl: './use-case-menu.component.html',
  styleUrls: ['./use-case-menu.component.scss'],
})
export class UseCaseMenuComponent implements OnInit, OnDestroy {
  // Angular 22 zone-CD workaround: HTTP responses don't auto-tick CD; repaint manually.
  private readonly cdr = inject(ChangeDetectorRef);
  // Form controls
  searchForm: FormGroup;

  // Data streams
  useCases$ = new Observable<UseCase[]>();
  categories$ = new Observable<string[]>();

  // Component state
  isLoading = false;
  error: string | null = null;
  selectedCategory = 'all';
  searchQuery = '';

  // Filtered data
  filteredUseCases: UseCase[] = [];
  availableCategories: string[] = [];

  // UI state
  viewMode: 'grid' | 'list' = 'grid';
  sortBy: 'name' | 'category' | 'created_at' = 'name';
  sortOrder: 'asc' | 'desc' = 'asc';

  // Pagination
  currentPage = 1;
  itemsPerPage = 12;
  totalItems = 0;
  paginatedUseCases: UseCase[] = [];

  private destroy$ = new Subject<void>();

  constructor(
    private useCaseService: UseCaseService,
    private router: Router,
    private fb: FormBuilder
  ) {
    this.searchForm = this.fb.group({
      search: [''],
      category: ['all'],
      sortBy: ['name'],
      sortOrder: ['asc'],
    });
  }

  ngOnInit(): void {
    this.useCases$ = this.useCaseService.getUseCasesStream();
    this.categories$ = this.useCaseService.getCategoriesStream();
    this.loadUseCases();
    this.setupFormListeners();
    this.subscribeToDataStreams();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ============================================================================
  // Data Loading
  // ============================================================================

  private loadUseCases(): void {
    this.isLoading = true;
    this.error = null;

    this.useCaseService
      .getAvailableUseCases()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (useCases) => {
          this.filteredUseCases = useCases;
          this.totalItems = useCases.length;
          this.applyFilters();
          this.isLoading = false;
          queueMicrotask(() => this.cdr.detectChanges());
        },
        error: (error) => {
          this.error = 'Failed to load use cases. Please try again.';
          this.isLoading = false;
          queueMicrotask(() => this.cdr.detectChanges());
          console.error('Error loading use cases:', error);
        },
      });
  }

  private subscribeToDataStreams(): void {
    // Subscribe to categories
    this.categories$.pipe(takeUntil(this.destroy$)).subscribe((categories) => {
      this.availableCategories = categories;
    });
  }

  // ============================================================================
  // Form Handling
  // ============================================================================

  private setupFormListeners(): void {
    // Search input with debounce
    this.searchForm
      .get('search')
      ?.valueChanges.pipe(
        startWith(''),
        debounceTime(300),
        distinctUntilChanged(),
        takeUntil(this.destroy$)
      )
      .subscribe((query) => {
        this.searchQuery = query.toLowerCase();
        this.applyFilters();
      });

    // Category filter
    this.searchForm
      .get('category')
      ?.valueChanges.pipe(takeUntil(this.destroy$))
      .subscribe((category) => {
        this.selectedCategory = category;
        this.applyFilters();
      });

    // Sort options
    this.searchForm
      .get('sortBy')
      ?.valueChanges.pipe(takeUntil(this.destroy$))
      .subscribe((sortBy) => {
        this.sortBy = sortBy;
        this.applyFilters();
      });

    this.searchForm
      .get('sortOrder')
      ?.valueChanges.pipe(takeUntil(this.destroy$))
      .subscribe((sortOrder) => {
        this.sortOrder = sortOrder;
        this.applyFilters();
      });
  }

  // ============================================================================
  // Filtering and Sorting
  // ============================================================================

  private applyFilters(): void {
    let filtered = [...this.filteredUseCases];

    // Apply search filter
    if (this.searchQuery) {
      filtered = filtered.filter(
        (useCase) =>
          useCase.name.toLowerCase().includes(this.searchQuery) ||
          useCase.description.toLowerCase().includes(this.searchQuery) ||
          useCase.tags?.some((tag) =>
            tag.toLowerCase().includes(this.searchQuery)
          )
      );
    }

    // Apply category filter
    if (this.selectedCategory !== 'all') {
      filtered = filtered.filter(
        (useCase) => useCase.category === this.selectedCategory
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (this.sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'category':
          comparison = a.category.localeCompare(b.category);
          break;
        case 'created_at':
          comparison =
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
      }

      return this.sortOrder === 'asc' ? comparison : -comparison;
    });

    this.totalItems = filtered.length;
    this.updatePagination(filtered);
  }

  private updatePagination(filteredUseCases: UseCase[]): void {
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    this.paginatedUseCases = filteredUseCases.slice(startIndex, endIndex);
  }

  // ============================================================================
  // User Actions
  // ============================================================================

  openUseCase(useCase: UseCase): void {
    // Navigate with UUID (id), not string use_case_id
    this.router.navigate(['/use-cases', useCase.id]);
  }

  onSearch(): void {
    // Trigger search if needed
    this.applyFilters();
  }

  onCategoryChange(category: string): void {
    this.selectedCategory = category;
    this.searchForm.patchValue({ category });
  }

  onSortChange(sortBy: string, sortOrder: string): void {
    this.sortBy = sortBy as any;
    this.sortOrder = sortOrder as any;
    this.searchForm.patchValue({ sortBy, sortOrder });
  }

  onViewModeChange(mode: 'grid' | 'list'): void {
    this.viewMode = mode;
  }

  onPageChange(page: number): void {
    this.currentPage = page;
    this.applyFilters();
  }

  onItemsPerPageChange(itemsPerPage: number): void {
    this.itemsPerPage = itemsPerPage;
    this.currentPage = 1;
    this.applyFilters();
  }

  refresh(): void {
    this.useCaseService.clearCache();
    this.loadUseCases();
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  getTotalPages(): number {
    return Math.ceil(this.totalItems / this.itemsPerPage);
  }

  getPageNumbers(): number[] {
    const totalPages = this.getTotalPages();
    const pages: number[] = [];

    // Show up to 5 page numbers around current page
    const start = Math.max(1, this.currentPage - 2);
    const end = Math.min(totalPages, this.currentPage + 2);

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    return pages;
  }

  getCategoryDisplayName(category: string): string {
    return category
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  getUseCaseIcon(category: string): string {
    const iconMap: Record<string, string> = {
      threat_analysis: 'shield',
      incident_response: 'siren',
      vulnerability_assessment: 'bug',
      compliance_check: 'shield-check',
      data_analysis: 'chart-column',
      report_generation: 'file-text',
      network_monitoring: 'network',
      user_behavior: 'user-search',
      default: 'brain-circuit',
    };

    return iconMap[category] || iconMap['default'];
  }

  getUseCaseColor(category: string): string {
    // Design-system SOC category accents (tokens.css --cat-*)
    const colorMap: Record<string, string> = {
      threat_analysis: 'var(--cat-threat)',
      incident_response: 'var(--cat-incident)',
      vulnerability_assessment: 'var(--cat-vuln)',
      compliance_check: 'var(--cat-compliance)',
      data_analysis: 'var(--cat-data)',
      report_generation: 'var(--cat-report)',
      network_monitoring: 'var(--cat-network)',
      user_behavior: 'var(--cat-behavior)',
      default: 'var(--cat-default)',
    };

    return colorMap[category] || colorMap['default'];
  }

  // ============================================================================
  // Template Helpers
  // ============================================================================

  get hasUseCases(): boolean {
    return this.paginatedUseCases.length > 0;
  }

  get hasFilters(): boolean {
    return Boolean(this.searchQuery) || this.selectedCategory !== 'all';
  }

  get isEmpty(): boolean {
    return !this.isLoading && this.paginatedUseCases.length === 0;
  }

  get showPagination(): boolean {
    return this.totalItems > this.itemsPerPage;
  }
}
