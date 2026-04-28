import { Injectable } from '@angular/core';

import { AuthTokens, TokenType } from '../auth/auth.models';

const STORAGE_PREFIX = 'aio';
const ACCESS_TOKEN_KEY = `${STORAGE_PREFIX}:access-token`;
const REFRESH_TOKEN_KEY = `${STORAGE_PREFIX}:refresh-token`;
const USER_PROFILE_KEY = `${STORAGE_PREFIX}:user-profile`;

@Injectable({ providedIn: 'root' })
export class SecureStorageService {
  private memoryStorage: Storage | null = null;

  setTokens(tokens: AuthTokens): void {
    const { accessToken, refreshToken } = tokens;

    this.setItem(ACCESS_TOKEN_KEY, accessToken);
    this.setItem(REFRESH_TOKEN_KEY, refreshToken);

    if (tokens.accessTokenExpiresAt) {
      this.setItem(
        `${ACCESS_TOKEN_KEY}:exp`,
        tokens.accessTokenExpiresAt.toString()
      );
    }

    if (tokens.refreshTokenExpiresAt) {
      this.setItem(
        `${REFRESH_TOKEN_KEY}:exp`,
        tokens.refreshTokenExpiresAt.toString()
      );
    }
  }

  getToken(type: TokenType): string | null {
    if (type === TokenType.Access) {
      return this.getItem(ACCESS_TOKEN_KEY);
    }

    if (type === TokenType.Refresh) {
      return this.getItem(REFRESH_TOKEN_KEY);
    }

    return null;
  }

  getTokenExpiration(type: TokenType): number | null {
    const key =
      type === TokenType.Access
        ? `${ACCESS_TOKEN_KEY}:exp`
        : `${REFRESH_TOKEN_KEY}:exp`;

    const stored = this.getItem(key);

    return stored ? Number.parseInt(stored, 10) : null;
  }

  clearTokens(): void {
    this.removeItem(ACCESS_TOKEN_KEY);
    this.removeItem(`${ACCESS_TOKEN_KEY}:exp`);
    this.removeItem(REFRESH_TOKEN_KEY);
    this.removeItem(`${REFRESH_TOKEN_KEY}:exp`);
  }

  setUserProfile(profile: unknown): void {
    this.setItem(USER_PROFILE_KEY, JSON.stringify(profile));
  }

  getUserProfile<T>(): T | null {
    const data = this.getItem(USER_PROFILE_KEY);

    if (!data) {
      return null;
    }

    try {
      return JSON.parse(data) as T;
    } catch {
      return null;
    }
  }

  clearUserProfile(): void {
    this.removeItem(USER_PROFILE_KEY);
  }

  clearAll(): void {
    this.clearTokens();
    this.clearUserProfile();
  }

  private setItem(key: string, value: string): void {
    this.getStorage().setItem(key, value);
  }

  private getItem(key: string): string | null {
    return this.getStorage().getItem(key);
  }

  private removeItem(key: string): void {
    this.getStorage().removeItem(key);
  }

  private getStorage(): Storage {
    if (typeof window === 'undefined') {
      return this.getMemoryStorage();
    }

    try {
      const { sessionStorage } = window;
      const testKey = `${STORAGE_PREFIX}:test`;
      sessionStorage.setItem(testKey, '1');
      sessionStorage.removeItem(testKey);
      return sessionStorage;
    } catch {
      return this.getMemoryStorage();
    }
  }

  private getMemoryStorage(): Storage {
    if (this.memoryStorage) {
      return this.memoryStorage;
    }

    const memoryStore = new Map<string, string>();

    this.memoryStorage = {
      get length(): number {
        return memoryStore.size;
      },
      clear(): void {
        memoryStore.clear();
      },
      getItem(key: string): string | null {
        return memoryStore.get(key) ?? null;
      },
      key(index: number): string | null {
        const entries = Array.from(memoryStore.keys());
        return entries[index] ?? null;
      },
      removeItem(key: string): void {
        memoryStore.delete(key);
      },
      setItem(key: string, value: string): void {
        memoryStore.set(key, value);
      },
    } as Storage;

    return this.memoryStorage;
  }
}
