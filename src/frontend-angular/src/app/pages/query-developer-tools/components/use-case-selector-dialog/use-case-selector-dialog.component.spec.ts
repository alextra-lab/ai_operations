/**
 * Unit tests for UseCaseSelectorDialogComponent
 *
 * Tests parameter injection workflows:
 * - Update existing draft Use Cases
 * - Clone and apply to published Use Cases
 * - Permission validation
 * - Parameter merging logic
 *
 * Related: P4-TOOLS-05, ADR-045
 */

import { HttpClientTestingModule } from '@angular/common/http/testing';
import {
  ComponentFixture,
  fakeAsync,
  TestBed,
  tick,
} from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';

import {
  QueryConfig,
  SamplingPreset,
} from '../../../../api/models/query-config.models';
import { UseCaseResponse } from '../../../../api/models/use-case-management.models';
import { UseCaseManagementService } from '../../../../api/services/use-case-management.service';
import { AuthService } from '../../../../core/auth/auth.service';
import {
  UseCaseSelectorDialogComponent,
  UseCaseSelectorDialogData,
} from './use-case-selector-dialog.component';

describe('UseCaseSelectorDialogComponent', () => {
  let component: UseCaseSelectorDialogComponent;
  let fixture: ComponentFixture<UseCaseSelectorDialogComponent>;
  let mockDialogRef: Partial<MatDialogRef<UseCaseSelectorDialogComponent>>;
  let mockUseCaseService: Partial<UseCaseManagementService>;
  let mockAuthService: Partial<AuthService>;
  let mockRouter: Partial<Router>;
  let mockSnackBar: Partial<MatSnackBar>;

  const mockDialogData: UseCaseSelectorDialogData = {
    mode: 'update',
    discoveredParams: {
      llm_model: 'gpt-4o-mini',
      sampling: {
        preset: SamplingPreset.BALANCED,
        temperature: 0.65,
        max_tokens: 2000,
      },
      rag: {
        enabled: true,
        vector_collections: ['documents'],
        top_k: 10,
        similarity_threshold: 0.7,
      },
    } as Partial<QueryConfig>,
  };

  const mockCurrentUser = {
    id: 'user-123',
    username: 'testuser',
    full_name: 'Test User',
    roles: ['corpus_admin'] as const,
    expires_at: undefined,
  };

  const mockDraftUseCase: UseCaseResponse = {
    id: 'uc-draft-123',
    use_case_id: 'test_uc_draft',
    name: 'Test Draft UC',
    description: 'Test description',
    category: 'security',
    intent_type: 'QUERY',
    version: 1,
    lifecycle_state: 'draft',
    is_active: true,
    config_json: {
      models: { llm: 'gpt-4o-mini' },
      rag: {
        enabled: true,
        top_k: 5,
        similarity_threshold: 0.6,
        vector_collections: [],
      },
      generation_params: { temperature: 0.5, max_tokens: 1024 },
      output_contract: { format: 'text', validation_mode: 'best_effort' },
      policy: {
        streaming_enabled: true,
        streaming_default: true,
        history_persistence: false,
      },
    },
    metadata_json: {},
    created_at: '2025-10-31T12:00:00Z',
    updated_at: '2025-10-31T12:00:00Z',
    created_by_user_id: 'user-123',
  };

  const mockPublishedUseCase: UseCaseResponse = {
    ...mockDraftUseCase,
    id: 'uc-pub-456',
    use_case_id: 'test_uc_published',
    name: 'Test Published UC',
    lifecycle_state: 'published',
    published_at: '2025-10-30T12:00:00Z',
    published_by_user_id: 'admin-789',
  };

  beforeEach(async () => {
    const afterOpenedSubject = new Subject<void>();
    const afterClosedSubject = new Subject<any>();

    mockDialogRef = {
      close: jest.fn((result?: any) => {
        afterClosedSubject.next(result);
        afterClosedSubject.complete();
      }),
      afterOpened: afterOpenedSubject.asObservable(),
      afterClosed: afterClosedSubject.asObservable(),
      componentInstance: {} as any,
      disableClose: false,
      id: 'test-dialog-id',
    };

    mockUseCaseService = {
      listUseCases: jest.fn(),
      updateUseCase: jest.fn(),
      cloneUseCase: jest.fn(),
    };

    mockAuthService = {
      getCurrentUser: jest.fn(),
      isAuthenticated: jest.fn(),
      hasRole: jest.fn(),
      hasAnyRole: jest.fn(),
      getAccessToken: jest.fn(),
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
    };

    mockRouter = {
      navigate: jest.fn(),
    };

    mockSnackBar = {
      open: jest.fn(),
    };

    // Set up default mock return values BEFORE component creation
    (mockAuthService.getCurrentUser as jest.Mock).mockReturnValue(
      of(mockCurrentUser)
    );
    (mockAuthService.isAuthenticated as jest.Mock).mockReturnValue(true);
    (mockAuthService.hasRole as jest.Mock).mockReturnValue(false);
    (mockAuthService.hasAnyRole as jest.Mock).mockReturnValue(false);
    (mockAuthService.getAccessToken as jest.Mock).mockReturnValue('mock-token');
    (mockUseCaseService.listUseCases as jest.Mock).mockReturnValue(
      of({
        use_cases: [],
        total_count: 0,
      })
    );
    (mockSnackBar.open as jest.Mock).mockReturnValue({
      onAction: () => of(undefined),
    } as any);

    await TestBed.configureTestingModule({
      imports: [
        UseCaseSelectorDialogComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: UseCaseManagementService, useValue: mockUseCaseService },
        { provide: AuthService, useValue: mockAuthService },
        { provide: Router, useValue: mockRouter },
        { provide: MatSnackBar, useValue: mockSnackBar },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UseCaseSelectorDialogComponent);
    component = fixture.componentInstance;
    (component as any).snackBar = mockSnackBar;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    // Wait for getCurrentUser subscription to complete
    expect(component.currentUser).toEqual(mockCurrentUser);
  });

  describe('ngOnInit', () => {
    it('should load Use Cases on init', () => {
      (mockUseCaseService.listUseCases as jest.Mock).mockReturnValue(
        of({
          use_cases: [mockDraftUseCase],
          total_count: 1,
        })
      );

      fixture.detectChanges();

      expect(mockUseCaseService.listUseCases).toHaveBeenCalledWith({
        lifecycle_state: 'draft',
        page_size: 100,
      });
    });
  });

  describe('filterEditableUseCases', () => {
    beforeEach(() => {
      // Ensure currentUser is set before tests
      component.currentUser = mockCurrentUser;
    });

    it('should filter drafts for update mode', () => {
      const useCases = [mockDraftUseCase, mockPublishedUseCase];
      const filtered = component.filterEditableUseCases(useCases);

      expect(filtered.length).toBe(1);
      expect(filtered[0].lifecycle_state).toBe('draft');
      expect(filtered[0].created_by_user_id).toBe('user-123');
    });

    it('should filter published for clone mode', () => {
      component.data.mode = 'clone';
      const useCases = [mockDraftUseCase, mockPublishedUseCase];
      const filtered = component.filterEditableUseCases(useCases);

      expect(filtered.length).toBe(1);
      expect(filtered[0].lifecycle_state).toBe('published');
    });

    it('should return empty array if no current user', () => {
      (mockAuthService.getCurrentUser as jest.Mock).mockReturnValue(of(null));
      component.currentUser = null;

      const filtered = component.filterEditableUseCases([mockDraftUseCase]);

      expect(filtered.length).toBe(0);
    });
  });

  describe('canApplyToUseCase', () => {
    beforeEach(() => {
      // Ensure currentUser is set before tests
      component.currentUser = mockCurrentUser;
    });

    it('should return false if not draft state', () => {
      const result = component.canApplyToUseCase(mockPublishedUseCase);
      expect(result).toBe(false);
    });

    it('should return false if not creator and not admin', () => {
      const otherUserUseCase = {
        ...mockDraftUseCase,
        created_by_user_id: 'other-user',
      };

      const result = component.canApplyToUseCase(otherUserUseCase);
      expect(result).toBe(false);
    });

    it('should return true if creator', () => {
      const result = component.canApplyToUseCase(mockDraftUseCase);
      expect(result).toBe(true);
    });

    it('should return true if admin', () => {
      const adminUser = {
        ...mockCurrentUser,
        roles: ['admin'],
      };
      (mockAuthService.getCurrentUser as jest.Mock).mockReturnValue(
        of(adminUser)
      );
      component.currentUser = adminUser;

      const otherUserUseCase = {
        ...mockDraftUseCase,
        created_by_user_id: 'other-user',
      };

      const result = component.canApplyToUseCase(otherUserUseCase);
      expect(result).toBe(true);
    });
  });

  describe('injectParameters', () => {
    beforeEach(() => {
      // Ensure currentUser is set before tests
      component.currentUser = mockCurrentUser;
    });

    it('should inject parameters into draft Use Case', (done) => {
      const updatedUseCase = { ...mockDraftUseCase };
      (mockUseCaseService.updateUseCase as jest.Mock).mockReturnValue(
        of(updatedUseCase)
      );
      component.selectedUseCase = mockDraftUseCase;
      component.data.mode = 'update'; // Ensure mode is set correctly

      component.onConfirm();

      setTimeout(() => {
        expect(mockUseCaseService.updateUseCase).toHaveBeenCalled();
        const updateCalls = (mockUseCaseService.updateUseCase as jest.Mock).mock
          .calls;
        expect(updateCalls.length).toBeGreaterThan(0);
        const updateCall = updateCalls[updateCalls.length - 1];
        const updateRequest = updateCall[1];

        expect(updateRequest.metadata_json?.parameter_source).toBe(
          'query_developer_tools'
        );
        expect(updateRequest.metadata_json?.tuned_by_user_id).toBe(
          mockCurrentUser.id
        );
        expect(mockDialogRef.close).toHaveBeenCalledWith({
          success: true,
          useCase: updatedUseCase,
        });
        done();
      }, 200);
    });

    it('should merge discovered parameters correctly', (done) => {
      const updatedUseCase = { ...mockDraftUseCase };
      (mockUseCaseService.updateUseCase as jest.Mock).mockReturnValue(
        of(updatedUseCase)
      );
      component.selectedUseCase = mockDraftUseCase;
      component.data.mode = 'update'; // Ensure mode is set correctly

      component.onConfirm();

      setTimeout(() => {
        const updateCalls = (mockUseCaseService.updateUseCase as jest.Mock).mock
          .calls;
        expect(updateCalls.length).toBeGreaterThan(0);
        const updateCall = updateCalls[updateCalls.length - 1];
        const merged = updateCall[1].config_json;

        // Check LLM model updated
        expect(merged.models.llm).toBe('gpt-4o-mini');

        // Check RAG parameters updated
        expect(merged.rag.top_k).toBe(10);
        expect(merged.rag.similarity_threshold).toBe(0.7);

        // Check generation params updated
        expect(merged.generation_params.temperature).toBe(0.65);
        expect(merged.generation_params.max_tokens).toBe(2000);

        done();
      }, 200);
    });

    it('should handle update errors gracefully', fakeAsync(() => {
      const error = { status: 403, error: { detail: 'Permission denied' } };
      (mockUseCaseService.updateUseCase as jest.Mock).mockReturnValue(
        throwError(() => error)
      );
      component.selectedUseCase = mockDraftUseCase;
      component.data.mode = 'update';
      component.currentUser = mockCurrentUser;

      component.onConfirm();
      tick(); // Flush observable error callback

      expect(mockSnackBar.open).toHaveBeenCalled();
      expect(mockDialogRef.close).toHaveBeenCalled();
      const closeCalls = (mockDialogRef.close as jest.Mock).mock.calls;
      expect(closeCalls.length).toBeGreaterThan(0);
      const lastCall = closeCalls[closeCalls.length - 1];
      expect(lastCall[0].success).toBe(false);
      expect(lastCall[0].error).toBeDefined();
    }));
  });

  describe('cloneAndInject', () => {
    beforeEach(() => {
      // Ensure currentUser is set before tests
      component.currentUser = mockCurrentUser;
    });

    it('should clone published Use Case and inject parameters', (done) => {
      component.data.mode = 'clone';
      component.selectedUseCase = mockPublishedUseCase;

      const clonedUseCase = {
        ...mockPublishedUseCase,
        id: 'uc-cloned-789',
        use_case_id: 'test_uc_published_tuned_123456',
        lifecycle_state: 'draft',
      };

      const updatedUseCase = { ...clonedUseCase };

      // Mock cloneUseCase to return Observable that emits clonedUseCase
      (mockUseCaseService.cloneUseCase as jest.Mock).mockImplementation(
        (id: string, newUseCaseId: string, newName: string) => {
          return of(clonedUseCase);
        }
      );
      (mockUseCaseService.updateUseCase as jest.Mock).mockReturnValue(
        of(updatedUseCase)
      );

      component.onConfirm();

      // Wait for async operations to complete
      setTimeout(() => {
        expect(mockUseCaseService.cloneUseCase).toHaveBeenCalled();
        expect(mockUseCaseService.updateUseCase).toHaveBeenCalled();

        const updateCalls = (mockUseCaseService.updateUseCase as jest.Mock).mock
          .calls;
        if (updateCalls.length > 0) {
          const updateCall = updateCalls[updateCalls.length - 1];
          const updateRequest = updateCall[1];

          expect(updateRequest.metadata_json?.cloned_for_tuning).toBe(true);
          expect(updateRequest.metadata_json?.source_use_case_id).toBe(
            'test_uc_published'
          );
        }

        expect(mockDialogRef.close).toHaveBeenCalledWith({
          success: true,
          useCase: updatedUseCase,
          cloned: true,
        });

        done();
      }, 200);
    });
  });

  describe('getParameterChanges', () => {
    it('should extract all changed parameters', () => {
      const changes = component.getParameterChanges();

      expect(changes.length).toBeGreaterThan(0);
      expect(changes.find((c) => c.label === 'LLM Model')).toBeTruthy();
      expect(changes.find((c) => c.label === 'Sampling Preset')).toBeTruthy();
      expect(changes.find((c) => c.label === 'Temperature')).toBeTruthy();
      expect(changes.find((c) => c.label === 'Top K')).toBeTruthy();
    });

    it('should return empty array if no parameters', () => {
      component.data.discoveredParams = {};
      const changes = component.getParameterChanges();

      expect(changes.length).toBe(0);
    });
  });

  describe('selectUseCase', () => {
    it('should set selected Use Case', () => {
      component.selectUseCase(mockDraftUseCase);
      expect(component.selectedUseCase).toBe(mockDraftUseCase);
    });
  });

  describe('onCancel', () => {
    it('should close dialog with success false', () => {
      component.onCancel();
      expect(mockDialogRef.close).toHaveBeenCalledWith({ success: false });
    });
  });
});
