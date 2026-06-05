/**
 * Collection List Component
 *
 * Displays a Material table of all document collections with filtering, search,
 * and admin actions (create, edit, delete, toggle active).
 *
 * Collections organize documents with specific embedding models for RAG queries.
 * Only admin and corpus_admin roles can access this page.
 *
 * Reference: P2-F3-ENHANCED-Collection-Management.md - Task 2.2
 */

import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, takeUntil } from 'rxjs/operators';

import {
  Collection,
  EMBEDDING_MODELS,
} from '../../api/models/collection.models';
import { CollectionService } from '../../api/services/collection.service';
import { CollectionCreateDialogComponent } from './collection-create-dialog.component';
import { CollectionEditDialogComponent } from './collection-edit-dialog.component';
import { LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-collection-list',
  templateUrl: './collection-list.component.html',
  styleUrls: ['./collection-list.component.scss'],
  standalone: true,
  imports: [
    LucideAngularModule,
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatDialogModule,
    MatDividerModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatTableModule,
    MatTooltipModule,
  ],
})
export class CollectionListComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  // Data
  collections: Collection[] = [];
  filteredCollections: Collection[] = [];
  totalCount = 0;
  isLoading = false;

  // Table columns
  displayedColumns: string[] = [
    'name',
    'embedding_model',
    'document_count',
    'is_active',
    'is_default',
    'updated_at',
    'actions',
  ];

  // Filters
  filterForm: FormGroup;
  embeddingModels = Object.values(EMBEDDING_MODELS);

  // Search
  searchQuery = '';

  constructor(
    private collectionService: CollectionService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
    private router: Router,
    private fb: FormBuilder
  ) {
    this.filterForm = this.fb.group({
      activeOnly: [true],
      embeddingModel: [''],
      status: [''],
    });
  }

  ngOnInit(): void {
    this.loadCollections();
    this.setupFilterListeners();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Setup reactive listeners for filter changes
   */
  private setupFilterListeners(): void {
    this.filterForm.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe(() => {
        this.loadCollections();
      });
  }

  /**
   * Load collections from API with current filters
   */
  loadCollections(): void {
    this.isLoading = true;
    const filters = this.filterForm.value;

    // Map status filter to activeOnly boolean
    let activeOnly: boolean;
    if (filters.status === 'active') {
      activeOnly = true;
    } else if (filters.status === 'inactive') {
      activeOnly = false;
    } else {
      // All status or no filter - use the activeOnly checkbox
      activeOnly = filters.activeOnly;
    }

    this.collectionService
      .listCollections(activeOnly, filters.embeddingModel || undefined, 0, 100)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.collections = response.collections;
          this.filteredCollections = this.collections;
          this.totalCount = response.total;
          this.applySearchFilter();
          this.isLoading = false;
        },
        error: (error) => {
          this.snackBar.open(
            `Failed to load collections: ${error.message}`,
            'Close',
            { duration: 5000 }
          );
          this.isLoading = false;
        },
      });
  }

  /**
   * Apply search filter to loaded collections
   */
  applySearchFilter(): void {
    if (!this.searchQuery) {
      this.filteredCollections = this.collections;
      return;
    }

    const query = this.searchQuery.toLowerCase();
    this.filteredCollections = this.collections.filter(
      (col) =>
        col.name.toLowerCase().includes(query) ||
        col.description?.toLowerCase().includes(query) ||
        col.embedding_model.toLowerCase().includes(query)
    );
  }

  /**
   * Handle search input changes
   */
  onSearchChange(value: string): void {
    this.searchQuery = value;
    this.applySearchFilter();
  }

  /**
   * Open dialog to create a new collection
   */
  openCreateDialog(): void {
    const dialogRef = this.dialog.open(CollectionCreateDialogComponent, {
      width: '600px',
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe((result) => {
        if (result) {
          this.loadCollections();
          this.snackBar.open('Collection created successfully', 'Close', {
            duration: 3000,
          });
        }
      });
  }

  /**
   * Open dialog to edit a collection
   */
  openEditDialog(collection: Collection): void {
    const dialogRef = this.dialog.open(CollectionEditDialogComponent, {
      width: '600px',
      data: collection,
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe((result) => {
        if (result) {
          this.loadCollections();
          this.snackBar.open('Collection updated successfully', 'Close', {
            duration: 3000,
          });
        }
      });
  }

  /**
   * Toggle collection active status
   */
  toggleActive(collection: Collection): void {
    this.collectionService
      .updateCollection(collection.id, {
        is_active: !collection.is_active,
      })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          collection.is_active = !collection.is_active;
          this.snackBar.open(
            `Collection ${collection.is_active ? 'activated' : 'deactivated'}`,
            'Close',
            { duration: 2000 }
          );
        },
        error: (error) => {
          this.snackBar.open(
            `Failed to update collection: ${error.message}`,
            'Close',
            { duration: 5000 }
          );
        },
      });
  }

  /**
   * Delete a collection with confirmation
   */
  confirmDelete(collection: Collection): void {
    if (collection.is_system_managed) {
      this.snackBar.open('Cannot delete system-managed collection', 'Close', {
        duration: 3000,
      });
      return;
    }

    if (collection.document_count > 0) {
      this.snackBar.open(
        `Cannot delete collection with ${collection.document_count} documents`,
        'Close',
        { duration: 5000 }
      );
      return;
    }

    const confirmed = confirm(
      `Are you sure you want to delete collection "${collection.name}"?`
    );

    if (confirmed) {
      this.deleteCollection(collection.id);
    }
  }

  /**
   * Delete a collection
   */
  private deleteCollection(id: string): void {
    this.collectionService
      .deleteCollection(id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.loadCollections();
          this.snackBar.open('Collection deleted successfully', 'Close', {
            duration: 3000,
          });
        },
        error: (error) => {
          this.snackBar.open(
            `Failed to delete collection: ${error.message}`,
            'Close',
            { duration: 5000 }
          );
        },
      });
  }

  /**
   * View collection statistics
   */
  viewStats(collection: Collection): void {
    this.collectionService
      .getCollectionStats(collection.id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (stats) => {
          alert(JSON.stringify(stats, null, 2)); // TODO: Create stats dialog
        },
        error: (error) => {
          this.snackBar.open(
            `Failed to load statistics: ${error.message}`,
            'Close',
            { duration: 5000 }
          );
        },
      });
  }

  /**
   * Clear all filters
   */
  clearFilters(): void {
    this.filterForm.patchValue({
      activeOnly: true,
      embeddingModel: '',
      status: '',
    });
    this.searchQuery = '';
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  /**
   * Get chip color for embedding provider
   */
  getProviderColor(provider: string): string {
    return provider === 'openai' ? 'primary' : 'accent';
  }
}
