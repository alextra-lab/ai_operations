import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { from, Observable } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { SessionStorageService } from '../../services/session-storage.service';
import {
  ContextThread,
  ThreadCreate,
  ThreadListResponse,
  ThreadMessage,
  ThreadUpdate,
} from '../models/context.models';
import { FormattedResponse } from '../models/orchestrator.models';

/**
 * Service for managing conversation threads (STATELESS ARCHITECTURE).
 *
 * Updated for ADR-030: Stateless architecture with client-side storage.
 * - Conversations stored in browser IndexedDB (via SessionStorageService)
 * - No server-side conversation storage
 * - Backward compatible API for existing components
 *
 * Provides methods for:
 * - Creating and managing conversation threads (client-side)
 * - Listing threads from local storage
 * - Retrieving thread messages from IndexedDB
 * - Sending messages (stores locally + sends to backend)
 * - Updating and archiving threads (client-side)
 */
@Injectable({
  providedIn: 'root',
})
export class ContextService {
  private readonly processUrl = `${environment.apiBaseUrl}/process`;
  private readonly MAX_CONTEXT_TOKENS = 8000; // Default context window

  constructor(
    private http: HttpClient,
    private sessionStorage: SessionStorageService
  ) {}

  /**
   * List all threads from client-side storage with optional filtering.
   */
  listThreads(
    limit = 50,
    offset = 0,
    discussionId?: string,
    useCaseId?: string,
    isActive?: boolean
  ): Observable<ThreadListResponse> {
    return from(this.sessionStorage.getAllSessions()).pipe(
      map((sessions) => {
        // Filter sessions
        let filtered = sessions;

        if (useCaseId) {
          filtered = filtered.filter((s) => s.use_case_id === useCaseId);
        }

        // Sort by last activity (newest first)
        filtered.sort(
          (a, b) =>
            new Date(b.last_activity_at).getTime() -
            new Date(a.last_activity_at).getTime()
        );

        // Paginate
        const paginatedSessions = filtered.slice(offset, offset + limit);

        // Convert to ContextThread format
        const threads: ContextThread[] = paginatedSessions.map((session) =>
          this.mapSessionToThread(session)
        );

        return {
          items: threads,
          total: filtered.length,
          limit,
          offset,
          has_more: offset + limit < filtered.length,
        };
      })
    );
  }

  /**
   * Get a single thread by ID from client-side storage.
   */
  getThread(threadId: string): Observable<ContextThread> {
    return from(this.sessionStorage.getSession(threadId)).pipe(
      map((session) => {
        if (!session) {
          throw new Error(`Thread not found: ${threadId}`);
        }
        return this.mapSessionToThread(session);
      })
    );
  }

  /**
   * Get all messages in a thread from client-side storage.
   */
  getThreadMessages(threadId: string): Observable<ThreadMessage[]> {
    return from(this.sessionStorage.getMessages(threadId)).pipe(
      map((messages) =>
        messages.map((msg, index) => ({
          id: `msg_${threadId}_${index}`,
          thread_id: threadId,
          query_id: undefined,
          sequence_number: index + 1,
          role: msg.role,
          content: msg.content,
          token_count: msg.metadata?.tokens || 0,
          model_used: msg.metadata?.model,
          is_summary: false,
          original_message_count: undefined,
          created_at: msg.timestamp,
        }))
      )
    );
  }

  /**
   * Create a new conversation thread (client-side).
   */
  createThread(data: ThreadCreate): Observable<ContextThread> {
    const title = data.title || 'New Conversation';
    const useCaseId = data.use_case_id || 'general';
    const useCaseName = data.use_case_name || 'General Query';

    return from(
      this.sessionStorage.createSession(title, useCaseId, useCaseName, 24)
    ).pipe(map((session) => this.mapSessionToThread(session)));
  }

  /**
   * Update an existing thread (client-side).
   */
  updateThread(
    threadId: string,
    data: ThreadUpdate
  ): Observable<ContextThread> {
    return from(
      this.sessionStorage.updateSession(threadId, {
        title: data.title,
        metadata: data.metadata,
      })
    ).pipe(switchMap(() => this.getThread(threadId)));
  }

  /**
   * Delete or archive a thread (client-side).
   */
  deleteThread(
    threadId: string,
    archive = true
  ): Observable<{ status: string }> {
    return from(this.sessionStorage.deleteSession(threadId)).pipe(
      map(() => ({ status: archive ? 'archived' : 'deleted' }))
    );
  }

  /**
   * Send a message in a conversation thread.
   * Stores message locally and sends to backend for processing.
   *
   * Note: In stateless architecture, thread_id is NOT sent to backend.
   * Conversation history is managed client-side only.
   */
  sendMessage(
    threadId: string,
    query: string,
    useCaseId?: string
  ): Observable<FormattedResponse> {
    // Add user message to local storage immediately
    return from(this.sessionStorage.addMessage(threadId, 'user', query)).pipe(
      switchMap(() => {
        // Send query to backend for processing
        // NOTE: Do NOT send thread_id - stateless architecture
        return this.http.post<FormattedResponse>(this.processUrl, {
          query,
          stream: false,
          // Removed: thread_id (stateless - no server-side history)
          // Removed: use_case_id (not required for basic query)
        });
      }),
      switchMap((response) => {
        // Store assistant response locally
        return from(
          this.sessionStorage.addMessage(
            threadId,
            'assistant',
            response.response || '',
            {
              confidence: response.confidence,
              request_id: response.request_id,
              source_count: response.sources?.length || 0,
            }
          )
        ).pipe(map(() => response));
      })
    );
  }

  /**
   * Calculate context utilization percentage.
   */
  getContextUtilization(thread: ContextThread): number {
    if (!thread.max_context_tokens) return 0;
    return Math.floor(
      (thread.context_size_tokens / thread.max_context_tokens) * 100
    );
  }

  /**
   * Check if thread is approaching token limit (>70%).
   */
  isApproachingLimit(thread: ContextThread): boolean {
    return this.getContextUtilization(thread) > 70;
  }

  /**
   * Map SessionStorage ConversationSession to ContextThread.
   */
  private mapSessionToThread(session: any): ContextThread {
    const messageCount = session.messages?.length || 0;
    const tokenUsage =
      session.messages?.reduce(
        (total: number, msg: any) => total + (msg.metadata?.tokens || 0),
        0
      ) || 0;

    return {
      id: session.id,
      thread_id: session.id,
      title: session.title,
      description: undefined,
      user_id: 'local-user',
      center_id: undefined,
      discussion_id: undefined,
      use_case_id: session.use_case_id,
      use_case_name: session.use_case_name,
      source: 'ui',
      is_active: true,
      message_count: messageCount,
      context_size_tokens: tokenUsage,
      max_context_tokens: this.MAX_CONTEXT_TOKENS,
      first_query_id: undefined,
      last_query_id: undefined,
      created_at: session.created_at,
      updated_at: session.last_activity_at,
      last_activity_at: session.last_activity_at,
      archived_at: undefined,
      metadata_json: session.metadata || {},
    };
  }
}
