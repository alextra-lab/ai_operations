import { TestBed } from '@angular/core/testing';
import {
  DraftStorageService,
  RegistrationDraft,
} from './draft-storage.service';

// Mock localStorage for Jest
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

describe('DraftStorageService', () => {
  let service: DraftStorageService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [DraftStorageService],
    });
    service = TestBed.inject(DraftStorageService);
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('saveDraft', () => {
    it('should save draft to localStorage', () => {
      const draft: RegistrationDraft = {
        sessionId: 'test_session_123',
        currentStep: 2,
        formData: {
          basicInfo: { tool_id: 'test_tool' },
          mcpConfig: { mcp_server_type: 'stdio' },
        },
        timestamp: Date.now(),
      };

      service.saveDraft(draft);

      const stored = localStorage.getItem('tool_registration_draft');
      expect(stored).toBeTruthy();
      const parsed = JSON.parse(stored!);
      expect(parsed.sessionId).toBe('test_session_123');
      expect(parsed.currentStep).toBe(2);
    });

    it('should update timestamp when saving', () => {
      const draft: RegistrationDraft = {
        sessionId: 'test_session_123',
        currentStep: 0,
        formData: {},
        timestamp: 1000,
      };

      service.saveDraft(draft);

      const stored = localStorage.getItem('tool_registration_draft');
      const parsed = JSON.parse(stored!);
      expect(parsed.timestamp).toBeGreaterThan(1000);
    });
  });

  describe('loadDraft', () => {
    it('should load draft from localStorage', () => {
      const draft: RegistrationDraft = {
        sessionId: 'test_session_123',
        currentStep: 1,
        formData: {
          basicInfo: { tool_id: 'test_tool' },
        },
        timestamp: Date.now(),
      };

      service.saveDraft(draft);
      const loaded = service.loadDraft();

      expect(loaded).toBeTruthy();
      expect(loaded!.sessionId).toBe('test_session_123');
      expect(loaded!.currentStep).toBe(1);
    });

    it('should return null if no draft exists', () => {
      const loaded = service.loadDraft();
      expect(loaded).toBeNull();
    });

    it('should return null if draft is expired', () => {
      const draft: RegistrationDraft = {
        sessionId: 'test_session_123',
        currentStep: 0,
        formData: {},
        timestamp: Date.now() - 2 * 60 * 60 * 1000, // 2 hours ago
      };

      localStorage.setItem('tool_registration_draft', JSON.stringify(draft));

      const loaded = service.loadDraft();
      expect(loaded).toBeNull();
      expect(localStorage.getItem('tool_registration_draft')).toBeNull();
    });

    it('should clear draft if JSON is invalid', () => {
      // Set invalid JSON directly
      localStorage.setItem('tool_registration_draft', 'invalid json');

      const loaded = service.loadDraft();
      expect(loaded).toBeNull();
      // Verify draft was cleared
      expect(localStorage.getItem('tool_registration_draft')).toBeNull();
    });
  });

  describe('clearDraft', () => {
    it('should remove draft from localStorage', () => {
      const draft: RegistrationDraft = {
        sessionId: 'test_session_123',
        currentStep: 0,
        formData: {},
        timestamp: Date.now(),
      };

      service.saveDraft(draft);
      expect(localStorage.getItem('tool_registration_draft')).toBeTruthy();

      service.clearDraft();
      expect(localStorage.getItem('tool_registration_draft')).toBeNull();
    });
  });

  describe('hasDraft', () => {
    it('should return true if draft exists', () => {
      const draft: RegistrationDraft = {
        sessionId: 'test_session_123',
        currentStep: 0,
        formData: {},
        timestamp: Date.now(),
      };

      service.saveDraft(draft);
      // Force a small delay to ensure save completes
      const hasDraft = service.hasDraft();
      expect(hasDraft).toBe(true);
    });

    it('should return false if no draft exists', () => {
      expect(service.hasDraft()).toBe(false);
    });

    it('should return false if draft is expired', () => {
      const draft: RegistrationDraft = {
        sessionId: 'test_session_123',
        currentStep: 0,
        formData: {},
        timestamp: Date.now() - 2 * 60 * 60 * 1000, // 2 hours ago
      };

      localStorage.setItem('tool_registration_draft', JSON.stringify(draft));

      expect(service.hasDraft()).toBe(false);
    });
  });
});
