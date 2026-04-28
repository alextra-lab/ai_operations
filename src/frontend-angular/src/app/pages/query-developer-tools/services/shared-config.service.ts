/**
 * SharedConfigService
 *
 * Manages shared configuration state across Query Developer Tools tabs.
 *
 * Features:
 * - Shared QueryConfig state across tabs
 * - Query history tracking
 * - SessionStorage persistence
 * - Tab state persistence to localStorage
 *
 * Related: P4-TOOLS-04, ADR-045
 */

import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

import {
  Message,
  QueryConfig,
  SamplingPreset,
} from '../../../api/models/query-config.models';

// Default configuration
const DEFAULT_CONFIG: QueryConfig = {
  // Model configuration
  llm_model: 'gpt-4o-mini',

  // Sampling configuration
  sampling: {
    preset: SamplingPreset.BALANCED,
    temperature: 0.65,
    top_p: 0.9,
    max_tokens: 2000,
  },

  // RAG configuration
  rag: {
    enabled: true,
    vector_collections: [],
    top_k: 5,
    similarity_threshold: 0.7,
    reranking_enabled: false,
  },

  // Advanced vector DB
  vector_db: {
    ef_search: 100,
  },
};

@Injectable()
export class SharedConfigService {
  private readonly STORAGE_KEY_CONFIG = 'queryDevToolsConfig';
  private readonly STORAGE_KEY_TAB = 'queryDevToolsActiveTab';

  // Configuration state
  private configSubject = new BehaviorSubject<QueryConfig>(
    this.loadSavedConfig()
  );
  config$: Observable<QueryConfig> = this.configSubject.asObservable();

  // Query history (in-memory only)
  private queryHistorySubject = new BehaviorSubject<Message[]>([]);
  queryHistory$: Observable<Message[]> =
    this.queryHistorySubject.asObservable();

  constructor() {
    // Initialize with saved config or default
    const savedConfig = this.loadSavedConfig();
    this.configSubject.next(savedConfig);
  }

  /**
   * Get current configuration (synchronous)
   */
  getCurrentConfig(): QueryConfig {
    return this.configSubject.value;
  }

  /**
   * Update configuration (partial update supported)
   */
  updateConfig(config: Partial<QueryConfig>): void {
    const current = this.configSubject.value;
    const updated = { ...current, ...config };
    this.configSubject.next(updated);

    // Persist to sessionStorage
    this.saveConfig(updated);
  }

  /**
   * Reset configuration to defaults
   */
  resetConfig(): void {
    this.configSubject.next({ ...DEFAULT_CONFIG });
    this.clearSavedConfig();
  }

  /**
   * Add a message to query history
   */
  addToHistory(message: Message): void {
    const history = this.queryHistorySubject.value;
    this.queryHistorySubject.next([...history, message]);
  }

  /**
   * Clear query history
   */
  clearHistory(): void {
    this.queryHistorySubject.next([]);
  }

  /**
   * Get query history (synchronous)
   */
  getHistory(): Message[] {
    return this.queryHistorySubject.value;
  }

  /**
   * Save active tab index
   */
  saveActiveTab(tabIndex: number): void {
    localStorage.setItem(this.STORAGE_KEY_TAB, String(tabIndex));
  }

  /**
   * Load saved active tab index
   */
  loadActiveTab(): number {
    try {
      const saved = localStorage.getItem(this.STORAGE_KEY_TAB);
      if (saved === null) {
        return 0;
      }
      const parsed = parseInt(saved, 10);
      return isNaN(parsed) ? 0 : parsed;
    } catch (error) {
      return 0;
    }
  }

  /**
   * Load saved configuration from sessionStorage
   */
  private loadSavedConfig(): QueryConfig {
    try {
      const saved = sessionStorage.getItem(this.STORAGE_KEY_CONFIG);
      if (saved) {
        const parsed = JSON.parse(saved) as QueryConfig;
        // Merge with defaults to handle missing fields
        return { ...DEFAULT_CONFIG, ...parsed };
      }
    } catch (error) {
      console.error('Failed to load saved config:', error);
    }
    return { ...DEFAULT_CONFIG };
  }

  /**
   * Save configuration to sessionStorage
   */
  private saveConfig(config: QueryConfig): void {
    try {
      sessionStorage.setItem(this.STORAGE_KEY_CONFIG, JSON.stringify(config));
    } catch (error) {
      console.error('Failed to save config:', error);
    }
  }

  /**
   * Clear saved configuration
   */
  private clearSavedConfig(): void {
    sessionStorage.removeItem(this.STORAGE_KEY_CONFIG);
  }
}
