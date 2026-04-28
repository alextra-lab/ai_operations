import { CommonModule } from '@angular/common';
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectChange, MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, Subscription, interval } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { ContextService } from '../../api/services/context.service';
import { SseStreamService } from '../../api/services/sse-stream.service';
import { LLMContentRendererComponent } from '../../components/llm-content-renderer/llm-content-renderer.component';
import { TokenType } from '../../core/auth/auth.models';
import { SecureStorageService } from '../../core/services/secure-storage.service';
import {
  ConversationSession,
  SessionStorageService,
} from '../../services/session-storage.service';

interface TtlStatus {
  label: string;
  color: 'primary' | 'accent' | 'warn';
}

/**
 * Conversation Component (ADR-059)
 *
 * Unified multi-turn conversation interface with integrated session management:
 * - Direct navigation (no thread list intermediary)
 * - Session switcher, New/Clear/History controls
 * - TTL visibility (badge, warnings, banners)
 * - Inline history panel with resume/export/delete
 * - Full conversation functionality (LLMContentRenderer, streaming, composer)
 */
@Component({
  selector: 'app-conversation',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatChipsModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatSelectModule,
    MatSnackBarModule,
    MatDialogModule,
    LLMContentRendererComponent,
  ],
  template: `
    <div class="flex flex-col overflow-hidden h-[calc(100vh-150px)]">
      <!-- ADR-059: Session Management Header -->
      <div
        class="flex-none z-[100] bg-white border-b px-4 py-3
          flex flex-wrap gap-3 items-center"
      >
        <div class="flex items-center gap-2">
          <mat-select
            [value]="currentSession?.id || null"
            (selectionChange)="onSwitchSession($event)"
            aria-label="Select conversation"
            class="min-w-[220px]"
            placeholder="Select conversation..."
          >
            <mat-option *ngFor="let session of sessions" [value]="session.id">
              {{ session.title || 'Untitled' }}
              • {{ session.messages.length }} msgs
            </mat-option>
          </mat-select>
          <button
            mat-icon-button
            (click)="onRenameConversation()"
            matTooltip="Rename conversation"
            aria-label="Rename current conversation"
            [disabled]="!currentSession"
          >
            <mat-icon>edit</mat-icon>
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button
            mat-stroked-button
            color="primary"
            (click)="onNewConversation()"
            aria-label="Start new conversation"
          >
            <mat-icon>add</mat-icon>
            New
          </button>
          <button
            mat-flat-button
            color="warn"
            (click)="onClearCurrent()"
            aria-label="Clear current conversation"
            [disabled]="!currentSession"
          >
            <mat-icon>delete</mat-icon>
            Clear
          </button>
          <button
            mat-stroked-button
            (click)="toggleHistory()"
            aria-label="Open conversation history"
          >
            <mat-icon>folder_open</mat-icon>
            History
          </button>
        </div>

        <div class="flex items-center gap-2 ml-auto">
          <span
            class="inline-flex items-center gap-1 px-2 py-1 rounded text-sm"
            [ngClass]="ttlBadgeClass"
            aria-live="polite"
          >
            <mat-icon
              [color]="ttlStatus.color"
              aria-hidden="true"
              class="!text-base"
            >
              timer
            </mat-icon>
            {{ ttlStatus.label }}
          </span>
          <span class="text-sm text-gray-500">
            {{ currentSession?.messages?.length ?? 0 }} messages
          </span>
        </div>
      </div>

      <!-- ADR-059: TTL Info Banner (First Visit) -->
      <div
        *ngIf="showTtlInfoBanner"
        class="flex-none bg-blue-50 border-b border-blue-200
          text-blue-900 px-4 py-3 flex items-start gap-3"
        role="status"
        aria-live="polite"
      >
        <mat-icon color="primary">info</mat-icon>
        <div class="flex-1 text-sm">
          Conversations stored locally for 24 hours.
        </div>
        <button
          mat-button
          color="primary"
          (click)="dismissTtlInfo()"
          aria-label="Dismiss TTL information banner"
        >
          Dismiss
        </button>
      </div>

      <!-- ADR-059: Critical TTL Warning Banner (< 10 min) -->
      <div
        *ngIf="showCriticalBanner"
        class="flex-none bg-red-50 border-b border-red-200 text-red-900
          px-4 py-3 flex items-start gap-3"
        role="alert"
        aria-live="assertive"
      >
        <mat-icon color="warn">warning</mat-icon>
        <div class="flex-1 text-sm">
          Current conversation expires in {{ criticalTtlLabel }}. Export before
          it is removed.
        </div>
        <button
          mat-button
          color="warn"
          (click)="onExportCurrent()"
          aria-label="Export current conversation"
        >
          Export
        </button>
      </div>

      <!-- Messages Container (Existing Thread Detail Functionality) -->
      <div
        class="flex-1 overflow-y-auto min-h-0 bg-gray-50 p-4"
        #messagesContainer
      >
        <div *ngIf="!currentSession" class="text-center text-gray-500 py-12">
          <mat-icon class="!text-6xl mb-4">forum</mat-icon>
          <p>Select a conversation or create a new one to get started.</p>
        </div>

        <div *ngIf="currentSession">
          <div
            *ngFor="let message of currentSession.messages"
            class="message-wrapper mb-4"
            [class.user-message]="message.role === 'user'"
            [class.assistant-message]="message.role === 'assistant'"
            [class.system-message]="message.role === 'system'"
          >
            <div
              class="message-bubble"
              [attr.aria-label]="
                message.role + ' message, ' + message.timestamp
              "
            >
              <div class="message-header">
                <mat-icon class="role-icon">{{
                  getRoleIcon(message.role)
                }}</mat-icon>
                <span class="role-name">{{ getRoleName(message.role) }}</span>
                <span class="timestamp">{{
                  message.timestamp | date: 'short'
                }}</span>
              </div>
              <div class="message-content">
                <app-llm-content-renderer
                  *ngIf="message.content && message.content.trim() !== ''"
                  [content]="message.content"
                >
                </app-llm-content-renderer>
              </div>
              <div class="message-footer" *ngIf="message.metadata?.tokens">
                <span class="token-count">
                  {{ message.metadata?.tokens }} tokens
                </span>
                <span *ngIf="message.metadata?.model" class="model-used">
                  {{ message.metadata?.model }}
                </span>
              </div>
            </div>
          </div>

          <!-- Streaming Indicator -->
          <div *ngIf="isSending" class="loading-indicator" role="status">
            <mat-spinner diameter="32"></mat-spinner>
            <span>Processing...</span>
          </div>
        </div>
      </div>

      <!-- Error Message -->
      <mat-card *ngIf="errorMessage" class="error-card mx-4">
        <div class="error-content">
          <mat-icon class="error-icon">error</mat-icon>
          <div class="error-text">
            <strong>Error:</strong> {{ errorMessage }}
          </div>
          <button
            mat-icon-button
            (click)="clearError()"
            class="error-dismiss"
            aria-label="Dismiss error message"
          >
            <mat-icon>close</mat-icon>
          </button>
        </div>
      </mat-card>

      <!-- Message Composer -->
      <div class="flex-none bg-white border-t px-4 py-3" *ngIf="currentSession">
        <form [formGroup]="messageForm" (ngSubmit)="sendMessage()">
          <mat-form-field appearance="outline" class="w-full">
            <mat-label>Type your message...</mat-label>
            <textarea
              matInput
              formControlName="message"
              rows="3"
              placeholder="Ask a question or continue the conversation..."
              [attr.aria-label]="
                'Message input, session: ' + currentSession.title
              "
            ></textarea>
            <mat-error *ngIf="messageForm.get('message')?.hasError('required')">
              Message is required
            </mat-error>
          </mat-form-field>
          <div class="flex justify-end gap-2 mt-2">
            <button
              mat-raised-button
              color="primary"
              type="submit"
              [disabled]="!messageForm.valid || isSending"
              aria-label="Send message"
            >
              <mat-icon>send</mat-icon>
              Send
            </button>
          </div>
        </form>
      </div>

      <!-- ADR-059: History Panel (Overlay) -->
      <div
        *ngIf="historyOpen"
        class="absolute inset-0 bg-black/30 backdrop-blur-sm flex justify-end z-[200]"
        (click)="closeHistory()"
      >
        <div
          class="w-full md:w-[480px] h-full bg-white shadow-xl border-l
            flex flex-col"
          (click)="$event.stopPropagation()"
        >
          <div class="flex items-center justify-between px-4 py-3 border-b">
            <div class="text-base font-semibold">
              Conversation History ({{ sessions.length }})
            </div>
            <button
              mat-icon-button
              (click)="closeHistory()"
              aria-label="Close history panel"
            >
              <mat-icon>close</mat-icon>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-4">
            <div
              *ngFor="let session of sessions"
              class="mb-3 p-3 border rounded hover:bg-gray-50"
            >
              <div class="flex items-start justify-between mb-2">
                <div class="flex-1">
                  <div class="font-medium">
                    {{ session.title || 'Untitled' }}
                  </div>
                  <div class="text-xs text-gray-500 mt-1">
                    {{ session.messages.length }} msgs •
                    {{ getTimeRemaining(session) }}
                  </div>
                </div>
                <span
                  class="px-2 py-1 text-xs rounded"
                  [ngClass]="{
                    'bg-green-100 text-green-800': !isExpiringSoon(session),
                    'bg-orange-100 text-orange-800': isExpiringSoon(session),
                  }"
                >
                  {{ isExpiringSoon(session) ? 'Expiring' : 'Active' }}
                </span>
              </div>
              <div class="flex gap-2 flex-wrap">
                <button
                  mat-button
                  color="primary"
                  (click)="onResumeSession(session.id)"
                  aria-label="Resume conversation"
                >
                  <mat-icon>play_arrow</mat-icon>
                  Resume
                </button>
                <button
                  mat-button
                  (click)="onRenameSessionFromHistory(session.id)"
                  aria-label="Rename conversation"
                >
                  <mat-icon>edit</mat-icon>
                  Rename
                </button>
                <button
                  mat-button
                  (click)="onExportSession(session.id)"
                  aria-label="Export conversation"
                >
                  <mat-icon>download</mat-icon>
                  Export
                </button>
                <button
                  mat-button
                  color="warn"
                  (click)="onDeleteSession(session.id)"
                  aria-label="Delete conversation"
                >
                  <mat-icon>delete</mat-icon>
                  Delete
                </button>
              </div>
            </div>
          </div>

          <div class="border-t px-4 py-3 bg-gray-50">
            <div class="text-sm text-gray-600 mb-3" *ngIf="storageStats">
              💾 {{ storageStats.totalSizeMB }} MB •
              {{ storageStats.expired }} expired
            </div>
            <div class="flex gap-2">
              <button
                mat-stroked-button
                (click)="onCleanExpired()"
                aria-label="Clean expired conversations"
              >
                <mat-icon>cleaning_services</mat-icon>
                Clean Expired
              </button>
              <button
                mat-flat-button
                color="warn"
                (click)="onClearAll()"
                aria-label="Clear all conversations"
              >
                <mat-icon>delete_sweep</mat-icon>
                Clear All
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .message-wrapper {
        display: flex;
      }

      .message-wrapper.user-message {
        justify-content: flex-end;
      }

      .message-wrapper.assistant-message,
      .message-wrapper.system-message {
        justify-content: flex-start;
      }

      .message-bubble {
        max-width: 85%;
        min-width: 200px;
        padding: 12px 16px;
        border-radius: 12px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      }

      .user-message .message-bubble {
        background: #1976d2;
        color: white;
      }

      .assistant-message .message-bubble {
        background: white;
        color: #333;
      }

      .system-message .message-bubble {
        background: #e3f2fd;
        color: #1565c0;
        font-style: italic;
      }

      .message-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 14px;
        opacity: 0.9;
      }

      .role-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }

      .role-name {
        font-weight: 500;
      }

      .timestamp {
        margin-left: auto;
        font-size: 12px;
      }

      .message-content {
        white-space: pre-wrap;
        line-height: 1.6;
        word-wrap: break-word;
        overflow-wrap: break-word;
        min-height: 20px;
        font-size: 15px;
      }

      .message-footer {
        display: flex;
        justify-content: space-between;
        margin-top: 8px;
        font-size: 11px;
        opacity: 0.7;
      }

      .loading-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 24px;
        color: #666;
      }

      .error-card {
        margin: 16px 0;
        border-left: 4px solid #f44336;
        background-color: #ffebee;
      }

      .error-content {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0;
      }

      .error-icon {
        color: #f44336;
        flex-shrink: 0;
      }

      .error-text {
        flex: 1;
        color: #d32f2f;
        font-size: 14px;
        line-height: 1.4;
      }

      .error-dismiss {
        flex-shrink: 0;
        color: #666;
      }

      .error-dismiss:hover {
        color: #f44336;
      }
    `,
  ],
})
export class ConversationComponent implements OnInit, OnDestroy {
  // ADR-059: Session Management State
  sessions: ConversationSession[] = [];
  currentSession: ConversationSession | null = null;
  historyOpen = false;
  storageStats: {
    total: number;
    active: number;
    expired: number;
    totalSizeMB: number;
  } | null = null;

  // ADR-059: TTL Management State
  ttlStatus: TtlStatus = { label: 'No session', color: 'primary' };
  ttlBadgeClass = 'bg-gray-100 text-gray-700';
  showTtlInfoBanner = false;
  showCriticalBanner = false;
  criticalTtlLabel = '';

  // Conversation State
  messageForm!: FormGroup;
  isSending = false;
  errorMessage: string | null = null;

  private destroy$ = new Subject<void>();
  private ttlCheckSubscription?: Subscription;

  @ViewChild('messagesContainer') messagesContainer?: ElementRef;

  constructor(
    private sessionStorage: SessionStorageService,
    private contextService: ContextService,
    private sseStreamService: SseStreamService,
    private secureStorage: SecureStorageService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private cdr: ChangeDetectorRef
  ) {}

  async ngOnInit(): Promise<void> {
    this.messageForm = this.fb.group({
      message: ['', [Validators.required, Validators.minLength(1)]],
    });

    // ADR-059: Smart Session Initialization
    await this.initializeSession();

    // ADR-059: Setup TTL Monitoring
    this.setupTtlMonitoring();

    // ADR-059: Show TTL Info Banner (First Visit)
    const hasSeenBanner = localStorage.getItem('ttl-banner-dismissed');
    if (!hasSeenBanner) {
      this.showTtlInfoBanner = true;
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.ttlCheckSubscription?.unsubscribe();
  }

  // ADR-059: Smart Session Initialization
  private async initializeSession(): Promise<void> {
    await this.sessionStorage.cleanExpiredSessions();
    await this.loadSessions();

    if (this.sessions.length === 0) {
      // No sessions - create new
      await this.createNewSession();
      this.showTtlInfoBanner = !localStorage.getItem('ttl-info-dismissed');
      return;
    }

    // Always auto-resume the most recent session
    // User can click "History" button to switch sessions
    const lastSession = this.sessions[0];
    await this.resumeSession(lastSession.id);

    this.showTtlInfoBanner = !localStorage.getItem('ttl-info-dismissed');
  }

  private async loadSessions(): Promise<void> {
    this.sessions = await this.sessionStorage.getAllSessions();
    this.storageStats = await this.sessionStorage.getStorageStats();
  }

  private async resumeSession(sessionId: string): Promise<void> {
    const session = await this.sessionStorage.getSession(sessionId);
    if (session) {
      this.currentSession = session;
      await this.sessionStorage.setCurrentSession(sessionId);
      this.hasShownHourWarning = false; // Reset TTL warning flag for new session
      this.updateTtlStatus();
      this.cdr.detectChanges(); // Trigger change detection for async updates
      this.scrollToBottom();
    }
  }

  private async createNewSession(): Promise<void> {
    const session = await this.sessionStorage.createSession(
      'New Conversation',
      'general',
      'General Conversation'
    );
    this.currentSession = session;
    await this.loadSessions();
    this.hasShownHourWarning = false; // Reset TTL warning flag for new session
    this.updateTtlStatus();
    this.cdr.detectChanges(); // Trigger change detection for async updates
  }

  // ADR-059: TTL Monitoring
  private setupTtlMonitoring(): void {
    this.ttlCheckSubscription = interval(60000) // Check every minute
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.updateTtlStatus();
        this.checkExpiringSoon();
      });
  }

  private updateTtlStatus(): void {
    if (!this.currentSession) {
      this.ttlStatus = { label: 'No session', color: 'primary' };
      this.ttlBadgeClass = 'bg-gray-100 text-gray-700';
      return;
    }

    const timeRemaining = this.sessionStorage.getTimeRemaining(
      this.currentSession
    );
    const expiringSoon = this.sessionStorage.isExpiringSoon(
      this.currentSession
    );

    const remainingMs =
      new Date(this.currentSession.expires_at).getTime() - Date.now();
    const hoursRemaining = remainingMs / (60 * 60 * 1000);

    if (hoursRemaining > 12) {
      this.ttlStatus = {
        label: `Expires in ${timeRemaining}`,
        color: 'primary',
      };
      this.ttlBadgeClass = 'bg-green-100 text-green-800';
    } else if (hoursRemaining > 1) {
      this.ttlStatus = {
        label: `Expires in ${timeRemaining}`,
        color: 'accent',
      };
      this.ttlBadgeClass = 'bg-orange-100 text-orange-800';
    } else if (remainingMs > 0) {
      this.ttlStatus = { label: `Expires in ${timeRemaining}`, color: 'warn' };
      this.ttlBadgeClass = 'bg-red-100 text-red-800';
    } else {
      this.ttlStatus = { label: 'Expired', color: 'warn' };
      this.ttlBadgeClass = 'bg-red-100 text-red-800';
    }
  }

  private async checkExpiringSoon(): Promise<void> {
    if (!this.currentSession) return;

    const remainingMs =
      new Date(this.currentSession.expires_at).getTime() - Date.now();

    // Critical warning at 10 minutes
    if (remainingMs > 0 && remainingMs <= 10 * 60 * 1000) {
      this.showCriticalBanner = true;
      this.criticalTtlLabel = this.sessionStorage.getTimeRemaining(
        this.currentSession
      );
    } else {
      this.showCriticalBanner = false;
    }

    // Toast warning at 1 hour
    if (
      remainingMs > 59 * 60 * 1000 &&
      remainingMs <= 60 * 60 * 1000 &&
      !this.hasShownHourWarning
    ) {
      this.snackBar.open(
        'Conversation expires in 1 hour. Export to save.',
        'Export',
        { duration: 10000 }
      );
      this.hasShownHourWarning = true;
    }
  }

  private hasShownHourWarning = false;

  // Session Management Actions
  async onSwitchSession(event: MatSelectChange): Promise<void> {
    await this.resumeSession(event.value);
    this.historyOpen = false;
  }

  async onNewConversation(): Promise<void> {
    await this.createNewSession();
    this.historyOpen = false;
  }

  async onClearCurrent(): Promise<void> {
    if (!this.currentSession) return;

    const confirmed = confirm(
      `Clear conversation "${this.currentSession.title}"?\n\nThis will permanently delete this conversation from your browser.`
    );

    if (confirmed) {
      await this.sessionStorage.deleteSession(this.currentSession.id);
      this.currentSession = null;
      await this.loadSessions();

      if (this.sessions.length > 0) {
        await this.resumeSession(this.sessions[0].id);
      }
    }
  }

  async onRenameConversation(): Promise<void> {
    if (!this.currentSession) return;

    const newTitle = prompt('Rename conversation:', this.currentSession.title);

    if (
      newTitle &&
      newTitle.trim() !== '' &&
      newTitle !== this.currentSession.title
    ) {
      await this.sessionStorage.updateSession(this.currentSession.id, {
        title: newTitle.trim(),
      });

      this.currentSession.title = newTitle.trim();
      await this.loadSessions();
      this.cdr.detectChanges();

      this.snackBar.open('Conversation renamed', 'OK', { duration: 2000 });
    }
  }

  toggleHistory(): void {
    this.historyOpen = !this.historyOpen;
  }

  closeHistory(): void {
    this.historyOpen = false;
  }

  dismissTtlInfo(): void {
    this.showTtlInfoBanner = false;
    localStorage.setItem('ttl-banner-dismissed', 'true');
  }

  // History Panel Actions
  async onResumeSession(sessionId: string): Promise<void> {
    await this.resumeSession(sessionId);
    this.historyOpen = false;
  }

  async onRenameSessionFromHistory(sessionId: string): Promise<void> {
    const session = this.sessions.find((s) => s.id === sessionId);
    if (!session) return;

    const newTitle = prompt('Rename conversation:', session.title);

    if (newTitle && newTitle.trim() !== '' && newTitle !== session.title) {
      await this.sessionStorage.updateSession(sessionId, {
        title: newTitle.trim(),
      });

      // Update current session if it's the one being renamed
      if (this.currentSession?.id === sessionId) {
        this.currentSession.title = newTitle.trim();
      }

      await this.loadSessions();
      this.cdr.detectChanges();

      this.snackBar.open('Conversation renamed', 'OK', { duration: 2000 });
    }
  }

  async onExportSession(sessionId: string): Promise<void> {
    const exportData = await this.sessionStorage.exportSession(sessionId);
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${sessionId}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);

    this.snackBar.open('Conversation exported', 'OK', { duration: 3000 });
  }

  async onExportCurrent(): Promise<void> {
    if (this.currentSession) {
      await this.onExportSession(this.currentSession.id);
    }
  }

  async onDeleteSession(sessionId: string): Promise<void> {
    const confirmed = confirm('Delete this conversation permanently?');
    if (confirmed) {
      await this.sessionStorage.deleteSession(sessionId);
      await this.loadSessions();

      if (this.currentSession?.id === sessionId) {
        this.currentSession = null;
        if (this.sessions.length > 0) {
          await this.resumeSession(this.sessions[0].id);
        }
      }
    }
  }

  async onCleanExpired(): Promise<void> {
    const result = await this.sessionStorage.runGarbageCollection();
    await this.loadSessions();
    this.snackBar.open(
      `Cleaned ${result.cleaned} expired conversations`,
      'OK',
      { duration: 3000 }
    );
  }

  async onClearAll(): Promise<void> {
    const confirmed = confirm(
      'Clear ALL conversations?\n\nThis will delete all conversations from your browser. This action cannot be undone.'
    );
    if (confirmed) {
      const count = await this.sessionStorage.deleteAllSessions();
      this.currentSession = null;
      await this.loadSessions();
      this.snackBar.open(`Deleted ${count} conversations`, 'OK', {
        duration: 3000,
      });
    }
  }

  // Conversation Actions
  async sendMessage(): Promise<void> {
    if (!this.messageForm.valid || this.isSending || !this.currentSession) {
      return;
    }

    const message = this.messageForm.get('message')?.value;
    this.isSending = true;

    // Save user message immediately
    await this.sessionStorage.addMessage(
      this.currentSession.id,
      'user',
      message
    );

    // Refresh current session to show user message
    this.currentSession = (await this.sessionStorage.getSession(
      this.currentSession.id
    ))!;
    this.scrollToBottom();

    // Get auth token
    const token = this.secureStorage.getToken(TokenType.Access);
    if (!token) {
      this.errorMessage = 'No authentication token available';
      this.isSending = false;
      return;
    }

    // Stream response
    let streamingMessage = '';
    this.sseStreamService
      .streamQuery(
        {
          query: message,
          sessionId: this.currentSession.id,
          requestType: 'QUERY', // Use QUERY intent for conversations
        },
        token
      )
      .subscribe({
        next: (chunk) => {
          streamingMessage += chunk.response || '';
          this.cdr.detectChanges();
        },
        complete: async () => {
          // Save assistant response
          if (streamingMessage && this.currentSession) {
            await this.sessionStorage.addMessage(
              this.currentSession.id,
              'assistant',
              streamingMessage
            );
            this.currentSession = (await this.sessionStorage.getSession(
              this.currentSession.id
            ))!;
          }

          this.messageForm.reset();
          this.isSending = false;
          this.scrollToBottom();
        },
        error: (error) => {
          console.error('Streaming error:', error);
          this.errorMessage = this.getErrorMessage(error);
          this.isSending = false;
        },
      });
  }

  clearError(): void {
    this.errorMessage = null;
  }

  // Helper Methods
  getTimeRemaining(session: ConversationSession): string {
    return this.sessionStorage.getTimeRemaining(session);
  }

  isExpiringSoon(session: ConversationSession): boolean {
    return this.sessionStorage.isExpiringSoon(session);
  }

  getRoleIcon(role: string): string {
    switch (role) {
      case 'user':
        return 'person';
      case 'assistant':
        return 'smart_toy';
      case 'system':
        return 'info';
      default:
        return 'chat';
    }
  }

  getRoleName(role: string): string {
    switch (role) {
      case 'user':
        return 'You';
      case 'assistant':
        return 'Assistant';
      case 'system':
        return 'System';
      default:
        return role;
    }
  }

  private getErrorMessage(error: any): string {
    if (error?.message?.includes('ERR_INCOMPLETE_CHUNKED_ENCODING')) {
      return 'Connection interrupted. Please try again.';
    }
    if (error?.status === 504) {
      return 'Request timed out. Please try again.';
    }
    if (error?.status === 503) {
      return 'Service temporarily unavailable.';
    }
    if (error?.status >= 500) {
      return `Server error (${error.status}). Please try again later.`;
    }
    if (error?.status >= 400) {
      return `Request error (${error.status}). Please check your input.`;
    }
    return 'An unexpected error occurred. Please try again.';
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.messagesContainer) {
        const element = this.messagesContainer.nativeElement;
        element.scrollTop = element.scrollHeight;
      }
    }, 100);
  }
}
