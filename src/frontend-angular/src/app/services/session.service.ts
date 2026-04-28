import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, interval, Observable, Subscription } from 'rxjs';
import { ConversationMessage, ConversationSession } from './export.service';

/**
 * Session warning event
 */
export interface SessionWarning {
  type: 'expiring' | 'expired';
  timeLeftMs: number;
  session: ConversationSession;
}

/**
 * Session configuration
 */
export interface SessionConfig {
  ttl_ms?: number;
  warning_threshold_ms?: number;
  enable_local_storage?: boolean;
  enable_encryption?: boolean;
}

/**
 * Session service for client-side session management
 *
 * Implements ADR-030 (No Transcripts; Run Manifests Only) and
 * ADR-031 (Client-Owned Exports) by managing conversation sessions
 * entirely on the client side with TTL-based expiration.
 *
 * Features:
 * - TTL monitoring with configurable timeout (default: 1 hour)
 * - Expiration warnings at 5min and 1min remaining
 * - localStorage backup (optional)
 * - Session encryption (optional, future enhancement)
 * - Auto-export prompts before expiration
 *
 * Usage:
 * ```typescript
 * constructor(private sessionService: SessionService) {
 *   sessionService.getWarnings().subscribe(warning => {
 *     if (warning.type === 'expiring') {
 *       // Show warning banner
 *     }
 *   });
 * }
 * ```
 */
@Injectable({ providedIn: 'root' })
export class SessionService implements OnDestroy {
  private readonly DEFAULT_TTL_MS = 3600000; // 1 hour
  private readonly WARNING_THRESHOLD_MS = 300000; // 5 minutes
  private readonly CRITICAL_THRESHOLD_MS = 60000; // 1 minute
  private readonly MONITOR_INTERVAL_MS = 60000; // Check every minute
  private readonly STORAGE_KEY = 'aiop_session';

  private session$ = new BehaviorSubject<ConversationSession | null>(null);
  private warnings$ = new BehaviorSubject<SessionWarning | null>(null);
  private config: SessionConfig = {
    ttl_ms: this.DEFAULT_TTL_MS,
    warning_threshold_ms: this.WARNING_THRESHOLD_MS,
    enable_local_storage: false,
    enable_encryption: false,
  };

  private monitorSubscription: Subscription | null = null;
  private lastWarningType: 'normal' | 'critical' | null = null;

  constructor() {
    this.startTTLMonitor();
    this.loadSessionFromStorage();
  }

  ngOnDestroy(): void {
    this.stopTTLMonitor();
  }

  /**
   * Configure session behavior
   *
   * @param config - Session configuration options
   */
  configure(config: Partial<SessionConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Create a new session
   *
   * @param use_case_id - Optional use case ID
   * @param use_case_name - Optional use case name
   * @returns The created session
   */
  createSession(
    use_case_id?: string,
    use_case_name?: string
  ): ConversationSession {
    const now = new Date();
    const ttl = this.config.ttl_ms || this.DEFAULT_TTL_MS;

    const session: ConversationSession = {
      id: this.generateSessionId(),
      use_case_id,
      use_case_name,
      messages: [],
      createdAt: now,
      updatedAt: now,
      metadata: {
        ttl_ms: ttl,
        expires_at: new Date(now.getTime() + ttl).toISOString(),
      },
    };

    this.session$.next(session);
    this.lastWarningType = null;
    this.saveSessionToStorage();

    return session;
  }

  /**
   * Get current session
   *
   * @returns Current session or null
   */
  getSession(): ConversationSession | null {
    return this.session$.value;
  }

  /**
   * Get session as observable
   *
   * @returns Observable of session
   */
  getSessionObservable(): Observable<ConversationSession | null> {
    return this.session$.asObservable();
  }

  /**
   * Get session warnings as observable
   *
   * @returns Observable of warnings
   */
  getWarnings(): Observable<SessionWarning | null> {
    return this.warnings$.asObservable();
  }

  /**
   * Add message to current session
   *
   * @param message - Message to add
   * @returns true if added, false if no active session
   */
  addMessage(message: ConversationMessage): boolean {
    const session = this.session$.value;
    if (!session) {
      return false;
    }

    session.messages.push(message);
    session.updatedAt = new Date();
    this.session$.next(session);
    this.saveSessionToStorage();

    return true;
  }

  /**
   * Get all messages in current session
   *
   * @returns Array of messages (empty if no session)
   */
  getMessages(): ConversationMessage[] {
    return this.session$.value?.messages || [];
  }

  /**
   * Clear current session
   */
  clearSession(): void {
    this.session$.next(null);
    this.warnings$.next(null);
    this.lastWarningType = null;
    this.removeSessionFromStorage();
  }

  /**
   * Extend session TTL
   *
   * @param extension_ms - Additional milliseconds to add (default: 1 hour)
   * @returns true if extended, false if no active session
   */
  extendSession(extension_ms: number = this.DEFAULT_TTL_MS): boolean {
    const session = this.session$.value;
    if (!session || !session.metadata) {
      return false;
    }

    const currentExpiry = new Date(session.metadata.expires_at as string);
    const newExpiry = new Date(currentExpiry.getTime() + extension_ms);

    session.metadata.expires_at = newExpiry.toISOString();
    session.updatedAt = new Date();
    this.session$.next(session);
    this.lastWarningType = null;
    this.saveSessionToStorage();

    return true;
  }

  /**
   * Check if session is expired
   *
   * @returns true if expired or no session, false otherwise
   */
  isExpired(): boolean {
    const session = this.session$.value;
    if (!session || !session.metadata?.expires_at) {
      return true;
    }

    const expiresAt = new Date(session.metadata.expires_at as string);
    return new Date() >= expiresAt;
  }

  /**
   * Get time left until expiration
   *
   * @returns Milliseconds until expiration (0 if expired or no session)
   */
  getTimeLeft(): number {
    const session = this.session$.value;
    if (!session || !session.metadata?.expires_at) {
      return 0;
    }

    const expiresAt = new Date(session.metadata.expires_at as string);
    const timeLeft = expiresAt.getTime() - new Date().getTime();

    return Math.max(0, timeLeft);
  }

  /**
   * Format time left as human-readable string
   *
   * @returns Formatted time string (e.g., "5 minutes", "30 seconds")
   */
  getTimeLeftFormatted(): string {
    const ms = this.getTimeLeft();

    if (ms === 0) {
      return 'Expired';
    }

    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);

    if (minutes > 0) {
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    } else {
      return `${seconds} second${seconds !== 1 ? 's' : ''}`;
    }
  }

  /**
   * Start TTL monitoring
   *
   * Checks session expiration every minute and emits warnings
   */
  private startTTLMonitor(): void {
    if (this.monitorSubscription) {
      return; // Already monitoring
    }

    this.monitorSubscription = interval(this.MONITOR_INTERVAL_MS).subscribe(
      () => {
        this.checkSessionExpiration();
      }
    );
  }

  /**
   * Stop TTL monitoring
   */
  private stopTTLMonitor(): void {
    if (this.monitorSubscription) {
      this.monitorSubscription.unsubscribe();
      this.monitorSubscription = null;
    }
  }

  /**
   * Check session expiration and emit warnings
   */
  private checkSessionExpiration(): void {
    const session = this.session$.value;
    if (!session) {
      return;
    }

    const timeLeft = this.getTimeLeft();

    // Session expired
    if (timeLeft === 0) {
      this.warnings$.next({
        type: 'expired',
        timeLeftMs: 0,
        session,
      });
      this.expireSession();
      return;
    }

    // Critical warning (1 minute)
    if (
      timeLeft <= this.CRITICAL_THRESHOLD_MS &&
      this.lastWarningType !== 'critical'
    ) {
      this.lastWarningType = 'critical';
      this.warnings$.next({
        type: 'expiring',
        timeLeftMs: timeLeft,
        session,
      });
      return;
    }

    // Normal warning (5 minutes)
    const threshold =
      this.config.warning_threshold_ms || this.WARNING_THRESHOLD_MS;
    if (timeLeft <= threshold && this.lastWarningType === null) {
      this.lastWarningType = 'normal';
      this.warnings$.next({
        type: 'expiring',
        timeLeftMs: timeLeft,
        session,
      });
    }
  }

  /**
   * Expire session
   */
  private expireSession(): void {
    this.clearSession();
  }

  /**
   * Generate unique session ID
   *
   * @returns UUID v4 session ID
   */
  private generateSessionId(): string {
    return crypto.randomUUID();
  }

  /**
   * Save session to localStorage
   */
  private saveSessionToStorage(): void {
    if (!this.config.enable_local_storage) {
      return;
    }

    const session = this.session$.value;
    if (!session) {
      return;
    }

    try {
      const data = JSON.stringify(session);
      // TODO: Implement encryption if enabled
      localStorage.setItem(this.STORAGE_KEY, data);
    } catch (error) {
      console.error('[Session] Failed to save to localStorage:', error);
    }
  }

  /**
   * Load session from localStorage
   */
  private loadSessionFromStorage(): void {
    if (!this.config.enable_local_storage) {
      return;
    }

    try {
      const data = localStorage.getItem(this.STORAGE_KEY);
      if (!data) {
        return;
      }

      // TODO: Implement decryption if enabled
      const session = JSON.parse(data) as ConversationSession;

      // Convert date strings back to Date objects
      session.createdAt = new Date(session.createdAt);
      if (session.updatedAt) {
        session.updatedAt = new Date(session.updatedAt);
      }
      session.messages = session.messages.map((msg) => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      }));

      // Check if expired
      if (session.metadata?.expires_at) {
        const expiresAt = new Date(session.metadata.expires_at as string);
        if (new Date() >= expiresAt) {
          this.removeSessionFromStorage();
          return;
        }
      }

      this.session$.next(session);
    } catch (error) {
      console.error('[Session] Failed to load from localStorage:', error);
      this.removeSessionFromStorage();
    }
  }

  /**
   * Remove session from localStorage
   */
  private removeSessionFromStorage(): void {
    try {
      localStorage.removeItem(this.STORAGE_KEY);
    } catch (error) {
      console.error('[Session] Failed to remove from localStorage:', error);
    }
  }
}
