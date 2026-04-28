import { Injectable, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, timer } from 'rxjs';

import { TokenType } from '../auth/auth.models';
import { SecureStorageService } from './secure-storage.service';

@Injectable({ providedIn: 'root' })
export class SessionTimeoutService {
  private readonly storage = inject(SecureStorageService);
  private readonly router = inject(Router);

  private readonly sessionTimeout$ = new BehaviorSubject<number | null>(null);
  private readonly warningThreshold = 5 * 60 * 1000; // 5 minutes before expiry
  private readonly checkInterval = 60 * 1000; // Check every minute

  private timeoutTimer: ReturnType<typeof setTimeout> | null = null;
  private warningTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.startSessionMonitoring();
  }

  getSessionTimeout(): Observable<number | null> {
    return this.sessionTimeout$.asObservable();
  }

  private startSessionMonitoring(): void {
    // Check token expiry every minute
    timer(0, this.checkInterval)
      .pipe(takeUntilDestroyed())
      .subscribe(() => {
        this.checkTokenExpiry();
      });
  }

  private checkTokenExpiry(): void {
    const accessTokenExpiry = this.storage.getTokenExpiration(TokenType.Access);

    if (!accessTokenExpiry) {
      this.clearTimers();
      this.sessionTimeout$.next(null);
      return;
    }

    const now = Date.now();
    const timeUntilExpiry = accessTokenExpiry - now;

    if (timeUntilExpiry <= 0) {
      // Token has expired
      this.handleSessionExpired();
      return;
    }

    // Update session timeout
    this.sessionTimeout$.next(timeUntilExpiry);

    // Set warning timer if we're within warning threshold
    if (timeUntilExpiry <= this.warningThreshold && !this.warningTimer) {
      this.setWarningTimer(timeUntilExpiry);
    }

    // Set logout timer
    this.setLogoutTimer(timeUntilExpiry);
  }

  private setWarningTimer(timeUntilExpiry: number): void {
    this.clearWarningTimer();

    this.warningTimer = setTimeout(() => {
      this.showSessionWarning();
    }, timeUntilExpiry - this.warningThreshold);
  }

  private setLogoutTimer(timeUntilExpiry: number): void {
    this.clearTimeoutTimer();

    this.timeoutTimer = setTimeout(() => {
      this.handleSessionExpired();
    }, timeUntilExpiry);
  }

  private showSessionWarning(): void {
    // In a real app, you'd show a modal or notification
    console.warn('Session will expire in 5 minutes. Please save your work.');

    // For now, we'll just log it. In P1-F3, we'll add proper UI notifications
    // This could trigger a modal or toast notification
  }

  private handleSessionExpired(): void {
    this.clearTimers();
    this.sessionTimeout$.next(0);

    // Clear storage and redirect to login
    this.storage.clearAll();
    void this.router.navigate(['/login']);
  }

  private clearTimers(): void {
    this.clearTimeoutTimer();
    this.clearWarningTimer();
  }

  private clearTimeoutTimer(): void {
    if (this.timeoutTimer) {
      clearTimeout(this.timeoutTimer);
      this.timeoutTimer = null;
    }
  }

  private clearWarningTimer(): void {
    if (this.warningTimer) {
      clearTimeout(this.warningTimer);
      this.warningTimer = null;
    }
  }

  // Method to refresh session (called when user is active)
  refreshSession(): void {
    // For now, just re-check expiry times
    // In a real implementation, this would call the backend to refresh tokens
    this.checkTokenExpiry();
  }

  // Method to manually extend session
  extendSession(): void {
    this.refreshSession();
  }
}
