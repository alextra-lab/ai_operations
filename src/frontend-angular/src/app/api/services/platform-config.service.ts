/**
 * Platform Configuration Service
 *
 * Loads dynamic platform configuration (categories, intent types
 * with capability profiles) from the backend API.
 *
 * ADR-067: Dynamic Categories, Intent Capability Profiles, and
 * Auto-Presets.
 *
 * These endpoints are read-only and available to any
 * authenticated user.
 */

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import {
  BehaviorSubject,
  Observable,
  catchError,
  map,
  of,
  shareReplay,
  tap,
} from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CategoriesListResponse,
  CategoryConfig,
  IntentTypeConfig,
  IntentTypesListResponse,
} from '../models/platform-config.models';

@Injectable({
  providedIn: 'root',
})
export class PlatformConfigService {
  private readonly baseUrl =
    `${environment.apiBaseUrl}/config`;

  private categoriesSubject =
    new BehaviorSubject<CategoryConfig[]>([]);
  private intentTypesSubject =
    new BehaviorSubject<IntentTypeConfig[]>([]);

  /** Observable of loaded categories. */
  readonly categories$ =
    this.categoriesSubject.asObservable();
  /** Observable of loaded intent types. */
  readonly intentTypes$ =
    this.intentTypesSubject.asObservable();

  private categoriesCache$:
    Observable<CategoryConfig[]> | null = null;
  private intentTypesCache$:
    Observable<IntentTypeConfig[]> | null = null;

  constructor(private http: HttpClient) {}

  // ================================================================
  // Public API
  // ================================================================

  /**
   * Load categories from backend (cached after first call).
   * Emits to `categories$` subject.
   */
  loadCategories(): Observable<CategoryConfig[]> {
    if (this.categoriesCache$) {
      return this.categoriesCache$;
    }
    this.categoriesCache$ = this.http
      .get<CategoriesListResponse>(
        `${this.baseUrl}/categories`
      )
      .pipe(
        map((res) => res.categories),
        tap((cats) => this.categoriesSubject.next(cats)),
        shareReplay(1),
        catchError((err) => {
          console.error(
            'Failed to load categories:',
            err
          );
          this.categoriesCache$ = null;
          return of(this.getFallbackCategories());
        })
      );
    return this.categoriesCache$;
  }

  /**
   * Load intent types with capability profiles from
   * backend (cached after first call).
   * Emits to `intentTypes$` subject.
   */
  loadIntentTypes(): Observable<IntentTypeConfig[]> {
    if (this.intentTypesCache$) {
      return this.intentTypesCache$;
    }
    this.intentTypesCache$ = this.http
      .get<IntentTypesListResponse>(
        `${this.baseUrl}/intent-types`
      )
      .pipe(
        map((res) => res.intent_types),
        tap((types) =>
          this.intentTypesSubject.next(types)
        ),
        shareReplay(1),
        catchError((err) => {
          console.error(
            'Failed to load intent types:',
            err
          );
          this.intentTypesCache$ = null;
          return of(this.getFallbackIntentTypes());
        })
      );
    return this.intentTypesCache$;
  }

  /**
   * Get an intent type config by code.
   * Returns undefined if not yet loaded or not found.
   */
  getIntentType(
    code: string
  ): IntentTypeConfig | undefined {
    return this.intentTypesSubject.value.find(
      (t) => t.intent_code === code
    );
  }

  /**
   * Invalidate the cache, forcing a reload on next
   * call.
   */
  invalidateCache(): void {
    this.categoriesCache$ = null;
    this.intentTypesCache$ = null;
  }

  // ================================================================
  // Fallbacks (graceful degradation if backend offline)
  // ================================================================

  private getFallbackCategories(): CategoryConfig[] {
    return [
      {
        category_code: 'GENERAL',
        display_name: 'General Purpose',
        description:
          'General-purpose AI assistant capabilities',
        icon: 'message-square',
        color: '#607D8B',
        sort_order: 1,
      },
      {
        category_code: 'SECURITY',
        display_name: 'Security Operations',
        description: 'Cybersecurity and SOC workflows',
        icon: 'shield',
        color: '#f44336',
        sort_order: 2,
      },
      {
        category_code: 'COMPLIANCE',
        display_name: 'Compliance & Risk',
        description:
          'Regulatory compliance and risk management',
        icon: 'shield-alert',
        color: '#3F51B5',
        sort_order: 3,
      },
    ];
  }

  private getFallbackIntentTypes(): IntentTypeConfig[] {
    return [
      {
        intent_code: 'QUERY',
        display_name: 'General Query',
        description: 'General question answering',
        category_code: 'GENERAL',
        icon: 'messages-square',
        color: '#2196F3',
        is_system: true,
        default_sampling_preset: 'balanced',
        default_output_format: 'text',
        recommended_capabilities: ['general'],
        sort_order: 1,
      },
      {
        intent_code: 'SUMMARIZATION',
        display_name: 'Content Summarization',
        description: 'Content summarization',
        category_code: 'GENERAL',
        icon: 'file-text',
        color: '#4CAF50',
        is_system: true,
        default_sampling_preset: 'balanced',
        default_output_format: 'text',
        recommended_capabilities: ['large_context'],
        sort_order: 3,
      },
      {
        intent_code: 'EXTRACTION',
        display_name: 'Data Extraction',
        description:
          'Structured data extraction from content',
        category_code: 'GENERAL',
        icon: 'file-search',
        color: '#009688',
        is_system: true,
        default_sampling_preset: 'strict',
        default_output_format: 'json',
        recommended_capabilities: ['json_mode'],
        sort_order: 6,
      },
      {
        intent_code: 'ENRICHMENT',
        display_name: 'Data Enrichment',
        description: 'Data enrichment and augmentation',
        category_code: 'GENERAL',
        icon: 'brain-circuit',
        color: '#9C27B0',
        is_system: true,
        default_sampling_preset: 'balanced',
        default_output_format: 'structured',
        recommended_capabilities: ['json_mode'],
        sort_order: 4,
      },
    ];
  }
}
