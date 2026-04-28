/**
 * Export service for stateless architecture (ADR-031).
 *
 * Handles conversation export and summary generation from client-side data.
 */

import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { SessionStorageService } from './session-storage.service';

/**
 * Conversation message interface for export formatting
 */
export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date | string;
  metadata?: Record<string, any>;
}

/**
 * Conversation session interface for export formatting
 */
export interface ConversationSession {
  id: string;
  use_case_id?: string;
  use_case_name?: string;
  messages: ConversationMessage[];
  createdAt?: Date | string;
  updatedAt?: Date | string;
  metadata?: Record<string, any>;
}

interface ExportRequest {
  conversation_id: string;
  export_timestamp: string;
  use_case: {
    id: string;
    name: string;
    version?: string;
  };
  messages: any[];
  session_metadata: Record<string, any>;
  format: 'json' | 'markdown';
}

interface ExportResponse {
  export_id: string;
  format: string;
  content: string;
  download_url?: string;
}

export interface SummaryRequest {
  use_case_id?: string;
  messages: ConversationMessage[];
  export_format?: 'markdown' | 'json';
  redaction?: {
    pii?: boolean;
    secrets?: boolean;
  };
  use_case_context?: Record<string, any>;
  summary_type?: 'executive' | 'technical' | 'brief';
}

export interface SummaryResponse {
  summary: string;
  redacted_fields?: string[];
  token_count?: number;
  key_points?: string[];
  recommendations?: string[];
  metadata?: Record<string, any>;
}

@Injectable({
  providedIn: 'root',
})
export class ExportService {
  private readonly apiUrl = `${environment.apiBaseUrl}/stateless`;

  constructor(
    private http: HttpClient,
    private sessionStorage: SessionStorageService
  ) {}

  /**
   * Export conversation in JSON format.
   */
  exportAsJson(sessionId: string): Observable<ExportResponse> {
    return new Observable((observer) => {
      this.sessionStorage
        .exportSession(sessionId)
        .then((data) => {
          const request: ExportRequest = {
            ...data,
            format: 'json',
          };

          this.http
            .post<ExportResponse>(`${this.apiUrl}/export`, request)
            .subscribe({
              next: (response) => observer.next(response),
              error: (error) => observer.error(error),
              complete: () => observer.complete(),
            });
        })
        .catch((error) => observer.error(error));
    });
  }

  /**
   * Export conversation in Markdown format.
   */
  exportAsMarkdown(sessionId: string): Observable<ExportResponse> {
    return new Observable((observer) => {
      this.sessionStorage
        .exportSession(sessionId)
        .then((data) => {
          const request: ExportRequest = {
            ...data,
            format: 'markdown',
          };

          this.http
            .post<ExportResponse>(`${this.apiUrl}/export`, request)
            .subscribe({
              next: (response) => observer.next(response),
              error: (error) => observer.error(error),
              complete: () => observer.complete(),
            });
        })
        .catch((error) => observer.error(error));
    });
  }

  /**
   * Generate summary from conversation.
   * Overloaded: can take sessionId string or SummaryRequest object.
   */
  generateSummary(
    sessionIdOrRequest: string | SummaryRequest,
    summaryType?: 'executive' | 'technical' | 'brief'
  ): Observable<SummaryResponse> {
    // If first parameter is a string, it's a sessionId
    if (typeof sessionIdOrRequest === 'string') {
      const sessionId = sessionIdOrRequest;
      const type = summaryType || 'executive';
      return new Observable((observer) => {
        this.sessionStorage
          .exportSession(sessionId)
          .then((data) => {
            const request: SummaryRequest = {
              messages: data.messages,
              use_case_context: data.use_case,
              summary_type: type,
            };

            this.http
              .post<SummaryResponse>(`${this.apiUrl}/summary`, request)
              .subscribe({
                next: (response) => observer.next(response),
                error: (error) => observer.error(error),
                complete: () => observer.complete(),
              });
          })
          .catch((error) => observer.error(error));
      });
    } else {
      // Otherwise it's a SummaryRequest object
      const request = sessionIdOrRequest;
      return this.http.post<SummaryResponse>('/api/v1/summaries', request);
    }
  }

  /**
   * Download export content as file.
   */
  downloadExport(
    content: string,
    filename: string,
    format: 'json' | 'markdown'
  ): void {
    const mimeType = format === 'json' ? 'application/json' : 'text/markdown';
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.URL.revokeObjectURL(url);
  }

  /**
   * Generate filename for export.
   */
  generateFilename(sessionTitle: string, format: 'json' | 'markdown'): string {
    const timestamp = new Date().toISOString().split('T')[0];
    const sanitized = sessionTitle.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const extension = format === 'json' ? 'json' : 'md';

    return `conversation_${sanitized}_${timestamp}.${extension}`;
  }

  /**
   * Synchronous markdown export from ConversationSession object.
   * Pure formatting function for client-side use.
   */
  formatAsMarkdown(session: ConversationSession): string {
    const exportTime = new Date().toISOString();
    const lines: string[] = [];

    // Header
    lines.push('# Conversation Export');
    lines.push('');
    lines.push(`**Session ID:** ${session.id}`);
    if (session.use_case_name) {
      lines.push(`**Use Case:** ${session.use_case_name}`);
    }
    lines.push(`**Exported:** ${exportTime}`);
    lines.push('');

    // Messages
    for (const message of session.messages || []) {
      const role = message.role.charAt(0).toUpperCase() + message.role.slice(1);
      lines.push(`## ${role}`);
      lines.push('');
      lines.push(message.content);
      lines.push('');

      // Timestamp
      const timestamp =
        message.timestamp instanceof Date
          ? message.timestamp.toISOString()
          : message.timestamp;
      if (timestamp) {
        lines.push(`**Timestamp:** ${timestamp}`);
        lines.push('');
      }

      // Metadata
      if (message.metadata && Object.keys(message.metadata).length > 0) {
        lines.push('**Metadata:**');
        lines.push('```json');
        lines.push(JSON.stringify(message.metadata, null, 2));
        lines.push('```');
        lines.push('');
      }

      lines.push('---');
      lines.push('');
    }

    // Add final separator if there are messages
    if (session.messages && session.messages.length > 0) {
      lines.push('---');
    }

    return lines.join('\n');
  }

  /**
   * Synchronous JSON export from ConversationSession object.
   * Pure formatting function for client-side use.
   */
  exportAsJSON(session: ConversationSession): string {
    const exportData = {
      format_version: '1.0',
      export_timestamp: new Date().toISOString(),
      session: {
        id: session.id,
        use_case_id: session.use_case_id,
        use_case_name: session.use_case_name,
        messages:
          session.messages?.map((msg) => ({
            role: msg.role,
            content: msg.content,
            timestamp:
              msg.timestamp instanceof Date
                ? msg.timestamp.toISOString()
                : msg.timestamp,
            metadata: msg.metadata,
          })) || [],
        created_at:
          session.createdAt instanceof Date
            ? session.createdAt.toISOString()
            : session.createdAt,
        updated_at:
          session.updatedAt instanceof Date
            ? session.updatedAt.toISOString()
            : session.updatedAt,
        metadata: session.metadata || {},
      },
    };

    return JSON.stringify(exportData, null, 2);
  }

  /**
   * Download file helper (for compatibility with tests)
   */
  downloadFile(content: string, filename: string, mimeType: string): void {
    this.downloadExport(
      content,
      filename,
      mimeType === 'application/json' ? 'json' : 'markdown'
    );
  }

  /**
   * Copy to clipboard helper
   */
  async copyToClipboard(content: string): Promise<void> {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(content);
    } else {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = content;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  }

  /**
   * Export and download markdown (synchronous helper)
   */
  exportAndDownloadMarkdown(
    session: ConversationSession,
    filename?: string
  ): void {
    const markdown = this.formatAsMarkdown(session);
    const defaultFilename = filename || `conversation-${Date.now()}.md`;
    this.downloadFile(markdown, defaultFilename, 'text/markdown');
  }

  /**
   * Export and download JSON (synchronous helper)
   */
  exportAndDownloadJSON(session: ConversationSession, filename?: string): void {
    const json = this.exportAsJSON(session);
    const defaultFilename = filename || `conversation-${Date.now()}.json`;
    this.downloadFile(json, defaultFilename, 'application/json');
  }

  /**
   * Copy markdown to clipboard (synchronous helper)
   */
  async copyMarkdownToClipboard(session: ConversationSession): Promise<void> {
    const markdown = this.formatAsMarkdown(session);
    await this.copyToClipboard(markdown);
  }

  /**
   * Generate and download summary (for compatibility with tests)
   */
  async generateAndDownloadSummary(
    request: SummaryRequest,
    filename: string
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      this.generateSummary(request).subscribe({
        next: (response) => {
          this.downloadFile(response.summary, filename, 'text/markdown');
          resolve();
        },
        error: (error) => reject(error),
      });
    });
  }
}
