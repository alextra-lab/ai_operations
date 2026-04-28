import { Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

export interface CacheEntry<T = any> {
  data: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
  key: string;
}

export interface CacheConfig {
  defaultTtl: number; // Default TTL in milliseconds
  maxSize: number; // Maximum number of cache entries
  storageType: 'memory' | 'localStorage' | 'sessionStorage';
}

@Injectable({
  providedIn: 'root',
})
export class ApiCacheService {
  private memoryCache = new Map<string, CacheEntry>();
  private readonly config: CacheConfig = {
    defaultTtl: 5 * 60 * 1000, // 5 minutes
    maxSize: 100,
    storageType: 'localStorage',
  };

  constructor() {
    this.loadFromStorage();
  }

  /**
   * Get data from cache
   */
  get<T>(key: string): Observable<T> | null {
    const entry = this.getCacheEntry<T>(key);

    if (!entry) {
      return null;
    }

    if (this.isExpired(entry)) {
      this.delete(key);
      return null;
    }

    return of(entry.data);
  }

  /**
   * Set data in cache
   */
  set<T>(key: string, data: T, ttl?: number): void {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.config.defaultTtl,
      key,
    };

    this.memoryCache.set(key, entry);
    this.enforceMaxSize();
    this.saveToStorage();
  }

  /**
   * Delete entry from cache
   */
  delete(key: string): void {
    this.memoryCache.delete(key);
    this.saveToStorage();
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.memoryCache.clear();
    this.saveToStorage();
  }

  /**
   * Check if key exists in cache and is not expired
   */
  has(key: string): boolean {
    const entry = this.getCacheEntry(key);
    return entry !== null && !this.isExpired(entry);
  }

  /**
   * Get cache statistics
   */
  getStats(): { size: number; keys: string[]; expiredCount: number } {
    const keys = Array.from(this.memoryCache.keys());
    const expiredCount = keys.filter((key) => {
      const entry = this.getCacheEntry(key);
      return entry && this.isExpired(entry);
    }).length;

    return {
      size: this.memoryCache.size,
      keys,
      expiredCount,
    };
  }

  /**
   * Clean up expired entries
   */
  cleanup(): void {
    const now = Date.now();
    const expiredKeys: string[] = [];

    this.memoryCache.forEach((entry, key) => {
      if (this.isExpired(entry)) {
        expiredKeys.push(key);
      }
    });

    expiredKeys.forEach((key) => this.memoryCache.delete(key));

    if (expiredKeys.length > 0) {
      this.saveToStorage();
    }
  }

  /**
   * Cache HTTP request with automatic cache management
   */
  cacheRequest<T>(
    key: string,
    requestFn: () => Observable<T>,
    ttl?: number
  ): Observable<T> {
    // Try to get from cache first
    const cachedData = this.get<T>(key);
    if (cachedData) {
      return cachedData;
    }

    // If not in cache, make request and cache result
    return requestFn().pipe(
      tap((data) => this.set(key, data, ttl)),
      catchError((error) => {
        // Don't cache errors
        return throwError(() => error);
      })
    );
  }

  /**
   * Generate cache key from URL and parameters
   */
  generateCacheKey(url: string, params?: any): string {
    const paramString = params ? JSON.stringify(params) : '';
    return btoa(url + paramString).replace(/[^a-zA-Z0-9]/g, '');
  }

  private getCacheEntry<T>(key: string): CacheEntry<T> | null {
    return this.memoryCache.get(key) || null;
  }

  private isExpired(entry: CacheEntry): boolean {
    return Date.now() - entry.timestamp > entry.ttl;
  }

  private enforceMaxSize(): void {
    if (this.memoryCache.size > this.config.maxSize) {
      // Remove oldest entries
      const entries = Array.from(this.memoryCache.entries()).sort(
        ([, a], [, b]) => a.timestamp - b.timestamp
      );

      const toRemove = entries.slice(0, entries.length - this.config.maxSize);
      toRemove.forEach(([key]) => this.memoryCache.delete(key));
    }
  }

  private loadFromStorage(): void {
    if (this.config.storageType === 'memory') {
      return;
    }

    try {
      const storage = this.getStorage();
      const cachedData = storage.getItem('api_cache');

      if (cachedData) {
        const parsed = JSON.parse(cachedData);
        this.memoryCache = new Map(parsed);
      }
    } catch (error) {
      console.warn('Failed to load cache from storage:', error);
    }
  }

  private saveToStorage(): void {
    if (this.config.storageType === 'memory') {
      return;
    }

    try {
      const storage = this.getStorage();
      const serialized = JSON.stringify(Array.from(this.memoryCache.entries()));
      storage.setItem('api_cache', serialized);
    } catch (error) {
      console.warn('Failed to save cache to storage:', error);
    }
  }

  private getStorage(): Storage {
    switch (this.config.storageType) {
      case 'localStorage':
        return localStorage;
      case 'sessionStorage':
        return sessionStorage;
      default:
        throw new Error(`Unsupported storage type: ${this.config.storageType}`);
    }
  }
}
