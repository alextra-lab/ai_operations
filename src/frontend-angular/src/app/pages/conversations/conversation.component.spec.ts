import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';

import { ContextService } from '../../api/services/context.service';
import { SseStreamService } from '../../api/services/sse-stream.service';
import { SecureStorageService } from '../../core/services/secure-storage.service';
import {
  ConversationSession,
  SessionStorageService,
} from '../../services/session-storage.service';
import { ConversationComponent } from './conversation.component';

describe('ConversationComponent', () => {
  let component: ConversationComponent;
  let fixture: ComponentFixture<ConversationComponent>;
  let mockSessionStorage: Partial<SessionStorageService>;
  let mockContextService: Partial<ContextService>;
  let mockSseStreamService: Partial<SseStreamService>;
  let mockSecureStorage: Partial<SecureStorageService>;
  let mockSnackBar: Partial<MatSnackBar>;
  let mockDialog: Partial<MatDialog>;

  const buildSession = (id: string, hoursOld = 0): ConversationSession => ({
    id,
    title: `Session ${id}`,
    use_case_id: 'default',
    use_case_name: 'General',
    messages: [],
    created_at: new Date().toISOString(),
    last_activity_at: new Date(
      Date.now() - hoursOld * 60 * 60 * 1000
    ).toISOString(),
    expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    metadata: {},
  });

  beforeEach(async () => {
    // Setup mocks
    mockSessionStorage = {
      cleanExpiredSessions: jest.fn().mockResolvedValue(0),
      getAllSessions: jest.fn().mockResolvedValue([]),
      createSession: jest.fn().mockResolvedValue(buildSession('new')),
      getSession: jest.fn().mockResolvedValue(buildSession('test')),
      setCurrentSession: jest.fn().mockResolvedValue(undefined),
      deleteSession: jest.fn().mockResolvedValue(undefined),
      deleteAllSessions: jest.fn().mockResolvedValue(0),
      addMessage: jest.fn().mockResolvedValue(undefined),
      exportSession: jest.fn().mockResolvedValue({ conversation_id: 'test' }),
      runGarbageCollection: jest
        .fn()
        .mockResolvedValue({ cleaned: 0, remaining: 0 }),
      getStorageStats: jest.fn().mockResolvedValue({
        total: 0,
        active: 0,
        expired: 0,
        totalSizeMB: 0,
      }),
      getTimeRemaining: jest.fn().mockReturnValue('23h 59m'),
      isExpiringSoon: jest.fn().mockReturnValue(false),
    };

    mockContextService = {};
    mockSseStreamService = {
      streamQuery: jest
        .fn()
        .mockReturnValue(of({ response: 'test response', request_id: '123' })),
    };
    mockSecureStorage = {
      getToken: jest.fn().mockReturnValue('mock-token'),
    };
    mockSnackBar = {
      open: jest.fn().mockReturnValue({ onAction: () => of(undefined) } as any),
    };
    mockDialog = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) } as any),
    };

    await TestBed.configureTestingModule({
      imports: [
        ConversationComponent,
        ReactiveFormsModule,
        MatSnackBarModule,
        MatDialogModule,
        NoopAnimationsModule,
      ],
      providers: [
        FormBuilder,
        { provide: SessionStorageService, useValue: mockSessionStorage },
        { provide: ContextService, useValue: mockContextService },
        { provide: SseStreamService, useValue: mockSseStreamService },
        { provide: SecureStorageService, useValue: mockSecureStorage },
        { provide: MatSnackBar, useValue: mockSnackBar },
        { provide: MatDialog, useValue: mockDialog },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConversationComponent);
    component = fixture.componentInstance;
    (component as unknown as { snackBar: typeof mockSnackBar }).snackBar =
      mockSnackBar;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Initialization (ADR-059 Smart Session Init)', () => {
    it('should create component', () => {
      expect(component).toBeTruthy();
    });

    it('should create new session when none exist', async () => {
      mockSessionStorage.getAllSessions = jest.fn().mockResolvedValue([]);
      mockSessionStorage.createSession = jest
        .fn()
        .mockResolvedValue(buildSession('new'));

      await component.ngOnInit();

      expect(mockSessionStorage.cleanExpiredSessions).toHaveBeenCalled();
      expect(mockSessionStorage.createSession).toHaveBeenCalled();
      expect(component.currentSession?.id).toBe('new');
    });

    it('should auto-resume last session when single and recent', async () => {
      const recentSession = buildSession('s1', 0.5); // 30 mins ago
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([recentSession]);
      mockSessionStorage.getSession = jest
        .fn()
        .mockResolvedValue(recentSession);

      await component.ngOnInit();

      expect(mockSessionStorage.setCurrentSession).toHaveBeenCalledWith('s1');
      expect(component.currentSession?.id).toBe('s1');
      expect(component.historyOpen).toBe(false);
    });

    it('should auto-resume most recent session when multiple sessions exist', async () => {
      const sessions = [buildSession('s1'), buildSession('s2')];
      mockSessionStorage.getAllSessions = jest.fn().mockResolvedValue(sessions);
      mockSessionStorage.getSession = jest.fn().mockResolvedValue(sessions[0]);

      await component.ngOnInit();

      expect(mockSessionStorage.setCurrentSession).toHaveBeenCalledWith('s1');
      expect(component.currentSession?.id).toBe('s1');
      expect(component.historyOpen).toBe(false);
    });

    it('should auto-resume most recent session even when old', async () => {
      const oldSession = buildSession('s1', 2); // 2 hours ago
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([oldSession]);
      mockSessionStorage.getSession = jest.fn().mockResolvedValue(oldSession);

      await component.ngOnInit();

      expect(mockSessionStorage.setCurrentSession).toHaveBeenCalledWith('s1');
      expect(component.currentSession?.id).toBe('s1');
      expect(component.historyOpen).toBe(false);
    });

    it('should show TTL info banner on first visit', async () => {
      localStorage.removeItem('ttl-banner-dismissed');

      await component.ngOnInit();

      expect(component.showTtlInfoBanner).toBe(true);
    });

    it('should not show TTL info banner if previously dismissed', async () => {
      localStorage.setItem('ttl-banner-dismissed', 'true');
      localStorage.setItem('ttl-info-dismissed', 'true');

      await component.ngOnInit();

      expect(component.showTtlInfoBanner).toBe(false);

      localStorage.removeItem('ttl-banner-dismissed');
      localStorage.removeItem('ttl-info-dismissed');
    });
  });

  describe('Session Management Actions', () => {
    beforeEach(async () => {
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([buildSession('s1')]);
      mockSessionStorage.getSession = jest
        .fn()
        .mockResolvedValue(buildSession('s1'));
      await component.ngOnInit();
    });

    it('should switch session', async () => {
      const newSession = buildSession('s2');
      mockSessionStorage.getSession = jest.fn().mockResolvedValue(newSession);

      await component.onSwitchSession({ value: 's2' } as any);

      expect(mockSessionStorage.getSession).toHaveBeenCalledWith('s2');
      expect(mockSessionStorage.setCurrentSession).toHaveBeenCalledWith('s2');
      expect(component.currentSession?.id).toBe('s2');
      expect(component.historyOpen).toBe(false);
    });

    it('should create new conversation', async () => {
      const newSession = buildSession('new');
      mockSessionStorage.createSession = jest
        .fn()
        .mockResolvedValue(newSession);
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([newSession]);

      await component.onNewConversation();

      expect(mockSessionStorage.createSession).toHaveBeenCalledWith(
        'New Conversation',
        'general',
        'General Conversation'
      );
      expect(component.currentSession?.id).toBe('new');
      expect(component.historyOpen).toBe(false);
    });

    it('should clear current conversation with confirmation', async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      const remainingSession = buildSession('s2');
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([remainingSession]);
      mockSessionStorage.getSession = jest
        .fn()
        .mockResolvedValue(remainingSession);

      await component.onClearCurrent();

      expect(mockSessionStorage.deleteSession).toHaveBeenCalledWith('s1');
      expect(component.currentSession?.id).toBe('s2');
    });

    it('should not clear conversation if not confirmed', async () => {
      global.confirm = jest.fn().mockReturnValue(false);
      const currentSessionId = component.currentSession?.id;

      await component.onClearCurrent();

      expect(mockSessionStorage.deleteSession).not.toHaveBeenCalled();
      expect(component.currentSession?.id).toBe(currentSessionId);
    });

    it('should toggle history panel', () => {
      const initialState = component.historyOpen;

      component.toggleHistory();

      expect(component.historyOpen).toBe(!initialState);
    });

    it('should close history panel', () => {
      component.historyOpen = true;

      component.closeHistory();

      expect(component.historyOpen).toBe(false);
    });

    it('should dismiss TTL info banner', () => {
      component.showTtlInfoBanner = true;

      component.dismissTtlInfo();

      expect(component.showTtlInfoBanner).toBe(false);
      expect(localStorage.getItem('ttl-banner-dismissed')).toBe('true');

      localStorage.removeItem('ttl-banner-dismissed');
    });

    it('should rename current conversation', async () => {
      global.prompt = jest.fn().mockReturnValue('Updated Title');
      mockSessionStorage.updateSession = jest.fn().mockResolvedValue(undefined);
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([{ ...buildSession('s1'), title: 'Updated Title' }]);

      await component.onRenameConversation();

      expect(mockSessionStorage.updateSession).toHaveBeenCalledWith('s1', {
        title: 'Updated Title',
      });
      expect(component.currentSession?.title).toBe('Updated Title');
    });

    it('should not rename if prompt is cancelled', async () => {
      global.prompt = jest.fn().mockReturnValue(null);
      mockSessionStorage.updateSession = jest.fn();

      await component.onRenameConversation();

      expect(mockSessionStorage.updateSession).not.toHaveBeenCalled();
    });

    it('should not rename if title is empty', async () => {
      global.prompt = jest.fn().mockReturnValue('   ');
      mockSessionStorage.updateSession = jest.fn();

      await component.onRenameConversation();

      expect(mockSessionStorage.updateSession).not.toHaveBeenCalled();
    });

    it('should not rename if title is unchanged', async () => {
      global.prompt = jest.fn().mockReturnValue('Session s1');
      mockSessionStorage.updateSession = jest.fn();

      await component.onRenameConversation();

      expect(mockSessionStorage.updateSession).not.toHaveBeenCalled();
    });

    it('should rename session from history panel', async () => {
      const sessions = [buildSession('s1'), buildSession('s2')];
      component.sessions = sessions;
      global.prompt = jest.fn().mockReturnValue('Renamed Session');
      mockSessionStorage.updateSession = jest.fn().mockResolvedValue(undefined);
      mockSessionStorage.getAllSessions = jest.fn().mockResolvedValue(sessions);

      await component.onRenameSessionFromHistory('s2');

      expect(mockSessionStorage.updateSession).toHaveBeenCalledWith('s2', {
        title: 'Renamed Session',
      });
    });

    it('should update current session title when renaming from history', async () => {
      const sessions = [buildSession('s1')];
      component.sessions = sessions;
      component.currentSession = sessions[0];
      global.prompt = jest.fn().mockReturnValue('Current Renamed');
      mockSessionStorage.updateSession = jest.fn().mockResolvedValue(undefined);
      mockSessionStorage.getAllSessions = jest.fn().mockResolvedValue(sessions);

      await component.onRenameSessionFromHistory('s1');

      expect(component.currentSession?.title).toBe('Current Renamed');
    });
  });

  describe('History Panel Actions', () => {
    beforeEach(async () => {
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([buildSession('s1')]);
      mockSessionStorage.getSession = jest
        .fn()
        .mockResolvedValue(buildSession('s1'));
      await component.ngOnInit();
    });

    it('should resume session from history', async () => {
      const session = buildSession('s2');
      mockSessionStorage.getSession = jest.fn().mockResolvedValue(session);

      await component.onResumeSession('s2');

      expect(mockSessionStorage.setCurrentSession).toHaveBeenCalledWith('s2');
      expect(component.currentSession?.id).toBe('s2');
      expect(component.historyOpen).toBe(false);
    });

    it('should export session', async () => {
      const exportData = { conversation_id: 's1', messages: [] };
      mockSessionStorage.exportSession = jest
        .fn()
        .mockResolvedValue(exportData);
      global.URL.createObjectURL = jest.fn().mockReturnValue('blob:url');
      global.URL.revokeObjectURL = jest.fn();

      await component.onExportSession('s1');

      expect(mockSessionStorage.exportSession).toHaveBeenCalledWith('s1');
      expect(mockSnackBar.open).toHaveBeenCalledWith(
        'Conversation exported',
        'OK',
        { duration: 3000 }
      );
    });

    it('should delete session with confirmation', async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      mockSessionStorage.getAllSessions = jest.fn().mockResolvedValue([]);

      await component.onDeleteSession('s1');

      expect(mockSessionStorage.deleteSession).toHaveBeenCalledWith('s1');
    });

    it('should clean expired sessions', async () => {
      mockSessionStorage.runGarbageCollection = jest
        .fn()
        .mockResolvedValue({ cleaned: 5, remaining: 10 });

      await component.onCleanExpired();

      expect(mockSessionStorage.runGarbageCollection).toHaveBeenCalled();
      expect(mockSnackBar.open).toHaveBeenCalledWith(
        'Cleaned 5 expired conversations',
        'OK',
        { duration: 3000 }
      );
    });

    it('should clear all conversations with confirmation', async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      mockSessionStorage.deleteAllSessions = jest.fn().mockResolvedValue(3);
      mockSessionStorage.getAllSessions = jest.fn().mockResolvedValue([]);

      await component.onClearAll();

      expect(mockSessionStorage.deleteAllSessions).toHaveBeenCalled();
      expect(mockSnackBar.open).toHaveBeenCalledWith(
        'Deleted 3 conversations',
        'OK',
        { duration: 3000 }
      );
      expect(component.currentSession).toBeNull();
    });
  });

  describe('TTL Management', () => {
    beforeEach(async () => {
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([buildSession('s1')]);
      mockSessionStorage.getSession = jest
        .fn()
        .mockResolvedValue(buildSession('s1'));
      await component.ngOnInit();
    });

    it('should display green badge for sessions > 12h', () => {
      mockSessionStorage.getTimeRemaining = jest
        .fn()
        .mockReturnValue('20h 30m');
      component['updateTtlStatus']();

      expect(component.ttlBadgeClass).toBe('bg-green-100 text-green-800');
      expect(component.ttlStatus.color).toBe('primary');
    });

    it('should display orange badge for sessions 1-12h', () => {
      const expiringSession = {
        ...buildSession('s1'),
        expires_at: new Date(Date.now() + 5 * 60 * 60 * 1000).toISOString(), // 5 hours
      };
      component.currentSession = expiringSession;
      mockSessionStorage.getTimeRemaining = jest.fn().mockReturnValue('5h 0m');

      component['updateTtlStatus']();

      expect(component.ttlBadgeClass).toBe('bg-orange-100 text-orange-800');
      expect(component.ttlStatus.color).toBe('accent');
    });

    it('should display red badge for sessions < 1h', () => {
      const criticalSession = {
        ...buildSession('s1'),
        expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(), // 30 min
      };
      component.currentSession = criticalSession;
      mockSessionStorage.getTimeRemaining = jest.fn().mockReturnValue('30m');
      mockSessionStorage.isExpiringSoon = jest.fn().mockReturnValue(true);

      component['updateTtlStatus']();

      expect(component.ttlBadgeClass).toBe('bg-red-100 text-red-800');
      expect(component.ttlStatus.color).toBe('warn');
    });

    it('should show critical banner for sessions < 10 min', async () => {
      const criticalSession = {
        ...buildSession('s1'),
        expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(), // 5 min
      };
      component.currentSession = criticalSession;

      await component['checkExpiringSoon']();

      expect(component.showCriticalBanner).toBe(true);
    });

    it('should reset 1-hour warning flag when switching sessions', async () => {
      // Set flag to true (simulating warning was already shown)
      component['hasShownHourWarning'] = true;

      const newSession = buildSession('s2');
      mockSessionStorage.getSession = jest.fn().mockResolvedValue(newSession);

      await component.onSwitchSession({ value: 's2' } as any);

      expect(component['hasShownHourWarning']).toBe(false);
    });

    it('should reset 1-hour warning flag when creating new conversation', async () => {
      // Set flag to true (simulating warning was already shown)
      component['hasShownHourWarning'] = true;

      const newSession = buildSession('new');
      mockSessionStorage.createSession = jest
        .fn()
        .mockResolvedValue(newSession);
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([newSession]);

      await component.onNewConversation();

      expect(component['hasShownHourWarning']).toBe(false);
    });

    it('should reset 1-hour warning flag when resuming session from history', async () => {
      // Set flag to true (simulating warning was already shown)
      component['hasShownHourWarning'] = true;

      const session = buildSession('s3');
      mockSessionStorage.getSession = jest.fn().mockResolvedValue(session);

      await component.onResumeSession('s3');

      expect(component['hasShownHourWarning']).toBe(false);
    });
  });

  describe('Conversation Actions', () => {
    beforeEach(async () => {
      mockSessionStorage.getAllSessions = jest
        .fn()
        .mockResolvedValue([buildSession('s1')]);
      mockSessionStorage.getSession = jest
        .fn()
        .mockResolvedValue(buildSession('s1'));
      await component.ngOnInit();
    });

    it('should send message successfully', async () => {
      component.messageForm.patchValue({ message: 'Test message' });

      await component.sendMessage();

      expect(mockSessionStorage.addMessage).toHaveBeenCalledWith(
        's1',
        'user',
        'Test message'
      );
      expect(mockSseStreamService.streamQuery).toHaveBeenCalled();
    });

    it('should not send empty message', async () => {
      component.messageForm.patchValue({ message: '' });

      await component.sendMessage();

      expect(mockSessionStorage.addMessage).not.toHaveBeenCalled();
      expect(mockSseStreamService.streamQuery).not.toHaveBeenCalled();
    });

    it('should handle missing auth token', async () => {
      component.messageForm.patchValue({ message: 'Test' });
      mockSecureStorage.getToken = jest.fn().mockReturnValue(null);

      await component.sendMessage();

      expect(component.errorMessage).toBe('No authentication token available');
      expect(component.isSending).toBe(false);
    });

    it('should handle streaming error', async () => {
      component.messageForm.patchValue({ message: 'Test message' });
      mockSseStreamService.streamQuery = jest
        .fn()
        .mockReturnValue(
          throwError(() => ({ status: 500, message: 'Server error' }))
        );

      await component.sendMessage();

      expect(component.errorMessage).toBeTruthy();
      expect(component.isSending).toBe(false);
    });

    it('should clear error message', () => {
      component.errorMessage = 'Test error';

      component.clearError();

      expect(component.errorMessage).toBeNull();
    });
  });

  describe('Helper Methods', () => {
    it('should get time remaining from storage service', () => {
      const session = buildSession('s1');
      mockSessionStorage.getTimeRemaining = jest
        .fn()
        .mockReturnValue('10h 30m');

      const result = component.getTimeRemaining(session);

      expect(mockSessionStorage.getTimeRemaining).toHaveBeenCalledWith(session);
      expect(result).toBe('10h 30m');
    });

    it('should check if expiring soon', () => {
      const session = buildSession('s1');
      mockSessionStorage.isExpiringSoon = jest.fn().mockReturnValue(true);

      const result = component.isExpiringSoon(session);

      expect(mockSessionStorage.isExpiringSoon).toHaveBeenCalledWith(session);
      expect(result).toBe(true);
    });

    it('should return correct role icons', () => {
      expect(component.getRoleIcon('user')).toBe('user');
      expect(component.getRoleIcon('assistant')).toBe('bot');
      expect(component.getRoleIcon('system')).toBe('info');
      expect(component.getRoleIcon('unknown')).toBe('message-square');
    });

    it('should return correct role names', () => {
      expect(component.getRoleName('user')).toBe('You');
      expect(component.getRoleName('assistant')).toBe('Assistant');
      expect(component.getRoleName('system')).toBe('System');
      expect(component.getRoleName('custom')).toBe('custom');
    });
  });

  describe('Cleanup', () => {
    it('should cleanup on destroy', () => {
      const destroySpy = jest.spyOn(component['destroy$'], 'next');
      const completeSpy = jest.spyOn(component['destroy$'], 'complete');

      component.ngOnDestroy();

      expect(destroySpy).toHaveBeenCalled();
      expect(completeSpy).toHaveBeenCalled();
    });
  });
});
