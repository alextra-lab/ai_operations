import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, firstValueFrom } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

/**
 * System capabilities response from backend
 *
 * Based on ADR-032: Capabilities & Edition Flags
 */
export interface Capabilities {
  /** Whether system is stateless (client-owned sessions) */
  stateless: boolean;

  /** Whether system supports stateful features (server-side history) */
  stateful: boolean;

  /** History provider: 'none' | 'governed' */
  history: string;

  /** Evidence sink: 'none' | 'worm' */
  evidence: string;

  /** Crypto provider: 'none' | 'kms' */
  crypto?: string;

  /** Available export formats */
  exports: string[];

  /** Edition: 'core' | 'plus' */
  edition?: string;

  /** Feature flags */
  features?: {
    run_manifests?: boolean;
    preflight_analysis?: boolean;
    test_suites?: boolean;
    exemplar_selection?: boolean;
    ephemeral_collections?: boolean;
    [key: string]: boolean | undefined;
  };
}

/**
 * Capabilities service for feature detection and UI adaptation
 *
 * Fetches system capabilities from backend on initialization and provides
 * methods to check feature availability. The frontend UI adapts based on
 * available capabilities.
 *
 * Follows ADR-032: Capabilities & Edition Flags
 *
 * Usage:
 * ```typescript
 * constructor(private capabilities: CapabilitiesService) {
 *   capabilities.getCapabilities().subscribe(caps => {
 *     if (caps?.stateless) {
 *       // Show client-side session management UI
 *     }
 *   });
 * }
 * ```
 */
@Injectable({ providedIn: 'root' })
export class CapabilitiesService {
  private readonly API_BASE = '/api/v1';
  private capabilities$ = new BehaviorSubject<Capabilities | null>(null);
  private loading$ = new BehaviorSubject<boolean>(false);
  private error$ = new BehaviorSubject<Error | null>(null);

  constructor(private http: HttpClient) { }

  /**
   * Fetch capabilities from backend
   *
   * Should be called on app initialization. Caches result in memory.
   *
   * @returns Promise that resolves when capabilities are loaded
   */
  async fetchCapabilities(): Promise<void> {
    if (this.loading$.value) {
      return; // Already fetching
    }

    this.loading$.next(true);
    this.error$.next(null);

    try {
      const caps = await firstValueFrom(
        this.http
          .get<Capabilities>(`${this.API_BASE}/capabilities/system/simple`)
          .pipe(
            tap((capabilities) => {
              this.capabilities$.next(capabilities);
            }),
            catchError((error) => {
              console.error('[Capabilities] Failed to fetch:', error);
              this.error$.next(error);

              // Fallback to safe defaults
              const fallback: Capabilities = {
                stateless: false,
                stateful: true,
                history: 'none',
                evidence: 'none',
                exports: ['md', 'json'],
                edition: 'core',
                features: {},
              };
              this.capabilities$.next(fallback);

              throw error;
            })
          )
      );
    } finally {
      this.loading$.next(false);
    }
  }

  /**
   * Get capabilities as observable
   *
   * @returns Observable of capabilities (null until loaded)
   */
  getCapabilities(): Observable<Capabilities | null> {
    return this.capabilities$.asObservable();
  }

  /**
   * Get current capabilities synchronously
   *
   * @returns Current capabilities or null if not loaded
   */
  getCurrentCapabilities(): Capabilities | null {
    return this.capabilities$.value;
  }

  /**
   * Get loading state
   *
   * @returns Observable of loading state
   */
  isLoading(): Observable<boolean> {
    return this.loading$.asObservable();
  }

  /**
   * Get error state
   *
   * @returns Observable of error (null if no error)
   */
  getError(): Observable<Error | null> {
    return this.error$.asObservable();
  }

  /**
   * Check if a specific capability is available
   *
   * @param feature - Feature name (e.g., 'stateless', 'exports', 'history')
   * @returns true if feature is available, false otherwise
   */
  hasCapability(feature: string): boolean {
    const caps = this.capabilities$.value;
    if (!caps) {
      return false;
    }

    // Check top-level boolean capabilities
    if (feature in caps && typeof (caps as any)[feature] === 'boolean') {
      return (caps as any)[feature];
    }

    // Check feature flags
    if (caps.features && feature in caps.features) {
      return caps.features[feature] === true;
    }

    return false;
  }

  /**
   * Check if a specific export format is supported
   *
   * @param format - Export format (e.g., 'md', 'json', 'pdf')
   * @returns true if format is supported, false otherwise
   */
  supportsExport(format: string): boolean {
    const caps = this.capabilities$.value;
    return caps?.exports?.includes(format) ?? false;
  }

  /**
   * Check if system is stateless (client-owned sessions)
   *
   * @returns true if stateless, false otherwise
   */
  isStateless(): boolean {
    return this.hasCapability('stateless');
  }

  /**
   * Check if system is stateful (server-side history)
   *
   * @returns true if stateful, false otherwise
   */
  isStateful(): boolean {
    return this.hasCapability('stateful');
  }

  /**
   * Get history provider type
   *
   * @returns History provider ('none', 'governed', etc.)
   */
  getHistoryProvider(): string {
    return this.capabilities$.value?.history ?? 'none';
  }

  /**
   * Get evidence sink type
   *
   * @returns Evidence sink ('none', 'worm', etc.)
   */
  getEvidenceSink(): string {
    return this.capabilities$.value?.evidence ?? 'none';
  }

  /**
   * Get system edition
   *
   * @returns Edition ('core', 'plus', etc.)
   */
  getEdition(): string {
    return this.capabilities$.value?.edition ?? 'core';
  }

  /**
   * Check if running in Core edition
   *
   * @returns true if Core edition, false otherwise
   */
  isCoreEdition(): boolean {
    return this.getEdition() === 'core';
  }

  /**
   * Check if running in Plus edition
   *
   * @returns true if Plus edition, false otherwise
   */
  isPlusEdition(): boolean {
    return this.getEdition() === 'plus';
  }

  /**
   * Check if a feature flag is enabled
   *
   * @param flag - Feature flag name
   * @returns true if enabled, false otherwise
   */
  isFeatureEnabled(flag: string): boolean {
    const caps = this.capabilities$.value;
    return caps?.features?.[flag] === true;
  }

  /**
   * Reload capabilities from backend
   *
   * Forces a fresh fetch from the server.
   *
   * @returns Promise that resolves when capabilities are reloaded
   */
  async reloadCapabilities(): Promise<void> {
    this.capabilities$.next(null);
    await this.fetchCapabilities();
  }
}
