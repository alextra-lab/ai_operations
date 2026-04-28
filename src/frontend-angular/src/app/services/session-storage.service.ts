/**
 * Session storage service for stateless architecture (ADR-030).
 *
 * Manages client-side conversation history using IndexedDB with TTL-based expiration.
 * No conversation data is stored server-side.
 */

import { Injectable } from '@angular/core';
import { DBSchema, IDBPDatabase, openDB } from 'idb';
import { BehaviorSubject, Observable } from 'rxjs';

export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    model?: string;
    tokens?: number;
    latency_ms?: number;
  };
}

export interface ConversationSession {
  id: string;
  title: string;
  use_case_id: string;
  use_case_name: string;
  messages: ConversationMessage[];
  created_at: string;
  last_activity_at: string;
  expires_at: string;
  metadata: Record<string, any>;
}

interface SessionDB extends DBSchema {
  conversations: {
    key: string;
    value: ConversationSession;
    indexes: {
      'by-expiry': string;
      'by-activity': string;
    };
  };
}

@Injectable({
  providedIn: 'root',
})
export class SessionStorageService {
  private readonly DB_NAME = 'aio-sessions';
  private readonly DB_VERSION = 1;
  private readonly DEFAULT_TTL_HOURS = 24;
  private readonly CLEANUP_INTERVAL_MS = 60 * 60 * 1000;

  private db!: IDBPDatabase<SessionDB>;
  private initialized = false;
  private cleanupIntervalId: number | null = null;

  private currentSessionSubject =
    new BehaviorSubject<ConversationSession | null>(null);
  public currentSession$ = this.currentSessionSubject.asObservable();

  constructor() {
    this.initDB();
  }

  /**
   * Initialize IndexedDB database.
   */
  private async initDB(): Promise<void> {
    if (this.initialized) return;

    try {
      this.db = await openDB<SessionDB>(this.DB_NAME, this.DB_VERSION, {
        upgrade(db) {
          // Create conversations object store
          const store = db.createObjectStore('conversations', {
            keyPath: 'id',
          });

          // Create indexes for efficient queries
          store.createIndex('by-expiry', 'expires_at');
          store.createIndex('by-activity', 'last_activity_at');
        },
      });

      this.initialized = true;

      // Clean up expired sessions on startup
      await this.cleanExpiredSessionsInternal();
      this.setupPeriodicCleanup();
    } catch (error) {
      console.error('[SessionStorage] Failed to initialize IndexedDB:', error);
    }
  }

  /**
   * Create a new conversation session.
   */
  async createSession(
    title: string,
    useCaseId: string,
    useCaseName: string,
    ttlHours: number = this.DEFAULT_TTL_HOURS
  ): Promise<ConversationSession> {
    await this.initDB();

    const now = new Date().toISOString();
    const expiresAt = new Date(
      Date.now() + ttlHours * 60 * 60 * 1000
    ).toISOString();

    const session: ConversationSession = {
      id: this.generateSessionId(),
      title,
      use_case_id: useCaseId,
      use_case_name: useCaseName,
      messages: [],
      created_at: now,
      last_activity_at: now,
      expires_at: expiresAt,
      metadata: {},
    };

    await this.db.put('conversations', session);
    this.currentSessionSubject.next(session);

    return session;
  }

  /**
   * Add message to current session.
   */
  async addMessage(
    sessionId: string,
    role: 'user' | 'assistant' | 'system',
    content: string,
    metadata?: Record<string, any>
  ): Promise<void> {
    await this.initDB();

    const session = await this.db.get('conversations', sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    const message: ConversationMessage = {
      role,
      content,
      timestamp: new Date().toISOString(),
      metadata,
    };

    session.messages.push(message);
    session.last_activity_at = new Date().toISOString();

    await this.db.put('conversations', session);
    this.currentSessionSubject.next(session);
  }

  /**
   * Get session by ID.
   */
  async getSession(
    sessionId: string
  ): Promise<ConversationSession | undefined> {
    await this.initDB();
    return await this.db.get('conversations', sessionId);
  }

  /**
   * Get all active sessions.
   */
  async getAllSessions(): Promise<ConversationSession[]> {
    await this.initDB();
    await this.cleanExpiredSessionsInternal();

    const now = new Date().toISOString();
    const allSessions = await this.db.getAll('conversations');

    return allSessions
      .filter((session) => session.expires_at > now)
      .sort(
        (a, b) =>
          new Date(b.last_activity_at).getTime() -
          new Date(a.last_activity_at).getTime()
      );
  }

  /**
   * Set current active session.
   */
  async setCurrentSession(sessionId: string): Promise<void> {
    const session = await this.getSession(sessionId);
    if (session) {
      this.currentSessionSubject.next(session);
    }
  }

  /**
   * Delete session.
   */
  async deleteSession(sessionId: string): Promise<void> {
    await this.initDB();
    await this.db.delete('conversations', sessionId);

    if (this.currentSessionSubject.value?.id === sessionId) {
      this.currentSessionSubject.next(null);
    }
  }

  /**
   * Clean up expired sessions.
   */
  async cleanExpiredSessions(): Promise<number> {
    await this.ensureInitialized();
    return this.cleanExpiredSessionsInternal();
  }

  /**
   * Get sessions expiring soon (within 1 hour).
   */
  async getExpiringSessions(): Promise<ConversationSession[]> {
    await this.ensureInitialized();

    const oneHourFromNow = new Date(Date.now() + 60 * 60 * 1000).toISOString();
    const now = new Date().toISOString();

    const allSessions = await this.db.getAll('conversations');

    return allSessions.filter((session) => {
      return session.expires_at > now && session.expires_at <= oneHourFromNow;
    });
  }

  /**
   * Export session data for server-side summary generation.
   */
  async exportSession(sessionId: string): Promise<any> {
    const session = await this.getSession(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    return {
      conversation_id: session.id,
      export_timestamp: new Date().toISOString(),
      use_case: {
        id: session.use_case_id,
        name: session.use_case_name,
      },
      messages: session.messages,
      session_metadata: {
        title: session.title,
        created_at: session.created_at,
        last_activity_at: session.last_activity_at,
        message_count: session.messages.length,
        ...session.metadata,
      },
    };
  }

  /**
   * Generate unique session ID.
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get current session or null.
   */
  getCurrentSession(): Observable<ConversationSession | null> {
    return this.currentSession$;
  }

  /**
   * Clear current session.
   */
  clearCurrentSession(): void {
    this.currentSessionSubject.next(null);
  }

  /**
   * Get messages from a session (for backward compatibility).
   */
  async getMessages(sessionId: string): Promise<ConversationMessage[]> {
    const session = await this.getSession(sessionId);
    return session?.messages || [];
  }

  /**
   * Update session metadata.
   */
  async updateSession(
    sessionId: string,
    updates: Partial<Pick<ConversationSession, 'title' | 'metadata'>>
  ): Promise<void> {
    await this.initDB();

    const session = await this.db.get('conversations', sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    Object.assign(session, updates);
    session.last_activity_at = new Date().toISOString();

    await this.db.put('conversations', session);

    if (this.currentSessionSubject.value?.id === sessionId) {
      this.currentSessionSubject.next(session);
    }
  }

  /**
   * Get message count for a session.
   */
  async getMessageCount(sessionId: string): Promise<number> {
    const session = await this.getSession(sessionId);
    return session?.messages.length || 0;
  }

  /**
   * Calculate token usage for a session (approximation).
   */
  async getTokenUsage(sessionId: string): Promise<number> {
    const session = await this.getSession(sessionId);
    if (!session) return 0;

    return session.messages.reduce((total, msg) => {
      return total + (msg.metadata?.tokens || 0);
    }, 0);
  }

  getTimeRemaining(session: ConversationSession): string {
    const remainingMs =
      new Date(session.expires_at).getTime() - new Date().getTime();

    if (remainingMs <= 0) {
      return 'Expired';
    }

    const hours = Math.floor(remainingMs / (60 * 60 * 1000));
    const minutes = Math.floor((remainingMs % (60 * 60 * 1000)) / 60000);

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }

    return `${minutes}m`;
  }

  isExpiringSoon(session: ConversationSession): boolean {
    const remainingMs =
      new Date(session.expires_at).getTime() - new Date().getTime();
    return remainingMs > 0 && remainingMs <= 60 * 60 * 1000;
  }

  async deleteAllSessions(): Promise<number> {
    await this.ensureInitialized();
    const total = (await this.db.getAllKeys('conversations')).length;
    await this.db.clear('conversations');
    this.currentSessionSubject.next(null);
    return total;
  }

  async runGarbageCollection(): Promise<{
    cleaned: number;
    remaining: number;
  }> {
    await this.ensureInitialized();
    const cleaned = await this.cleanExpiredSessionsInternal();
    const remaining = (await this.db.getAllKeys('conversations')).length;

    return { cleaned, remaining };
  }

  async getStorageStats(): Promise<{
    total: number;
    active: number;
    expired: number;
    totalSizeMB: number;
  }> {
    await this.ensureInitialized();

    const now = new Date().toISOString();
    const sessions = await this.db.getAll('conversations');
    const expired = sessions.filter((session) => session.expires_at <= now);
    const totalSizeMB = JSON.stringify(sessions).length / (1024 * 1024);

    return {
      total: sessions.length,
      active: sessions.length - expired.length,
      expired: expired.length,
      totalSizeMB: parseFloat(totalSizeMB.toFixed(3)),
    };
  }

  private async ensureInitialized(): Promise<void> {
    if (!this.initialized) {
      await this.initDB();
    }
  }

  private async cleanExpiredSessionsInternal(): Promise<number> {
    const now = new Date().toISOString();
    const allSessions = await this.db.getAll('conversations');
    const expiredSessions = allSessions.filter(
      (session) => session.expires_at < now
    );

    let cleanedCount = 0;
    for (const session of expiredSessions) {
      await this.db.delete('conversations', session.id);
      cleanedCount++;

      if (this.currentSessionSubject.value?.id === session.id) {
        this.currentSessionSubject.next(null);
      }
    }

    return cleanedCount;
  }

  private setupPeriodicCleanup(): void {
    if (this.cleanupIntervalId !== null) {
      return;
    }

    this.cleanupIntervalId = window.setInterval(() => {
      this.runGarbageCollection().catch((error) => {
        console.error('[SessionStorage] Periodic cleanup failed:', error);
      });
    }, this.CLEANUP_INTERVAL_MS);
  }
}
