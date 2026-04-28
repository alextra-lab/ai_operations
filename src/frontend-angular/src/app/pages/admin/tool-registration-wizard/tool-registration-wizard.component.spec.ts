import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatStepper } from '@angular/material/stepper';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import {
  ToolRegistrationPhase,
  ToolRegistrationService,
} from '../../../api/services/tool-registration.service';
import { AuthService } from '../../../core/auth/auth.service';
import { DraftStorageService } from '../../../services/draft-storage.service';
import { ToolRegistrationWizardComponent } from './tool-registration-wizard.component';

describe('ToolRegistrationWizardComponent', () => {
  let component: ToolRegistrationWizardComponent;
  let fixture: ComponentFixture<ToolRegistrationWizardComponent>;
  let registrationService: jest.Mocked<ToolRegistrationService>;
  let draftStorage: jest.Mocked<DraftStorageService>;
  let router: jest.Mocked<Router>;
  let snackBar: jest.Mocked<MatSnackBar>;

  beforeEach(async () => {
    const registrationServiceSpy = {
      processPhase: jest.fn(),
      getSession: jest.fn(),
      cancelRegistration: jest.fn(),
    };

    const draftStorageSpy = {
      saveDraft: jest.fn(),
      loadDraft: jest.fn(),
      clearDraft: jest.fn(),
      hasDraft: jest.fn(),
    };

    const routerSpy = {
      navigate: jest.fn(),
    };

    const snackBarSpy = {
      open: jest.fn(),
    };

    const mockAuthService = {
      getCurrentUser: jest.fn().mockReturnValue(of(null)),
      isAuthenticated: jest.fn().mockReturnValue(true),
      getAccessToken: jest.fn().mockReturnValue('mock-token'),
    };

    await TestBed.configureTestingModule({
      imports: [
        ToolRegistrationWizardComponent,
        ReactiveFormsModule,
        NoopAnimationsModule,
      ],
      providers: [
        FormBuilder,
        { provide: ToolRegistrationService, useValue: registrationServiceSpy },
        { provide: DraftStorageService, useValue: draftStorageSpy },
        { provide: Router, useValue: routerSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        { provide: AuthService, useValue: mockAuthService },
        { provide: 'API_BASE_URL', useValue: 'http://test-api' },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolRegistrationWizardComponent);
    component = fixture.componentInstance;
    registrationService = TestBed.inject(
      ToolRegistrationService
    ) as jest.Mocked<ToolRegistrationService>;
    draftStorage = TestBed.inject(
      DraftStorageService
    ) as jest.Mocked<DraftStorageService>;
    router = TestBed.inject(Router) as jest.Mocked<Router>;
    snackBar = TestBed.inject(MatSnackBar) as jest.Mocked<MatSnackBar>;

    // Mock stepper and ensure component uses our snackBar mock
    component.stepper = {
      selectedIndex: 0,
      next: jest.fn(),
      previous: jest.fn(),
    } as unknown as MatStepper;
    (component as unknown as { snackBar: typeof snackBar }).snackBar = snackBar;
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit', () => {
    it('should initialize forms', () => {
      fixture.detectChanges();
      expect(component.basicInfoForm).toBeTruthy();
      expect(component.mcpConfigForm).toBeTruthy();
      expect(component.securityForm).toBeTruthy();
      expect(component.permissionsForm).toBeTruthy();
    });

    it('should load draft if exists', () => {
      const draft = {
        sessionId: 'test_session_123',
        currentStep: 1,
        formData: {
          basicInfo: { tool_id: 'test_tool', name: 'Test Tool' },
          mcpConfig: { mcp_server_type: 'stdio' },
        },
        timestamp: Date.now(),
      };

      draftStorage.hasDraft.mockReturnValue(true);
      draftStorage.loadDraft.mockReturnValue(draft as any);
      fixture.detectChanges();

      expect(component.sessionId).toBe('test_session_123');
      expect(component.basicInfo['tool_id']).toBe('test_tool');
    });

    it('should setup draft save debounce', fakeAsync(() => {
      fixture.detectChanges();
      component.triggerDraftSave();
      tick(500);
      expect(draftStorage.saveDraft).toHaveBeenCalled();
    }));
  });

  describe('onBasicInfoSubmit', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.stepper = {
        selectedIndex: 0,
        next: jest.fn(),
        previous: jest.fn(),
      } as unknown as MatStepper;
      (component as unknown as { snackBar: typeof snackBar }).snackBar =
        snackBar;
      component.basicInfoForm.patchValue({
        tool_id: 'test_tool',
        name: 'Test Tool',
        description: 'Test description',
        category: 'database',
        tool_purpose: 'orchestrator',
        service_location: 'orchestrator',
      });
    });

    it('should submit basic info successfully', async () => {
      registrationService.processPhase.mockReturnValue(
        of({
          session_id: 'test_session_123',
          current_phase: ToolRegistrationPhase.BASIC_INFO,
          next_phase: ToolRegistrationPhase.MCP_CONFIG,
          validation_errors: {},
          can_proceed: true,
          message: 'Success',
        })
      );

      component.onBasicInfoSubmit();
      await fixture.whenStable();

      expect(registrationService.processPhase).toHaveBeenCalled();
      expect(component.sessionId).toBe('test_session_123');
      expect(component.stepper.next).toHaveBeenCalled();
    });

    it('should handle validation errors', async () => {
      registrationService.processPhase.mockReturnValue(
        of({
          session_id: 'test_session_123',
          current_phase: ToolRegistrationPhase.BASIC_INFO,
          next_phase: null,
          validation_errors: {
            tool_id: ['Invalid format'],
          },
          can_proceed: false,
          message: 'Validation failed',
        })
      );

      component.onBasicInfoSubmit();
      await fixture.whenStable();

      expect(component.validationErrors).toHaveProperty('tool_id');
      expect(component.validationErrors['tool_id']).toEqual([
        'Invalid format',
      ]);
      expect(component.stepper.next).not.toHaveBeenCalled();
    });

    it('should handle errors', async () => {
      registrationService.processPhase.mockReturnValue(
        throwError(() => ({ error: { detail: 'Server error' } }))
      );

      component.onBasicInfoSubmit();
      await fixture.whenStable();

      expect(snackBar.open).toHaveBeenCalledWith('Server error', 'Close', {
        duration: 5000,
      });
    });
  });

  describe('onMcpConfigSubmit', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.stepper = {
        selectedIndex: 0,
        next: jest.fn(),
        previous: jest.fn(),
      } as unknown as MatStepper;
      component.sessionId = 'test_session_123';
      component.mcpConfigForm.patchValue({
        mcp_server_type: 'stdio',
        mcp_command: 'node server.js',
      });
    });

    it('should submit MCP config successfully', async () => {
      registrationService.processPhase.mockReturnValue(
        of({
          session_id: 'test_session_123',
          current_phase: ToolRegistrationPhase.MCP_CONFIG,
          next_phase: ToolRegistrationPhase.CONNECTION_TEST,
          validation_errors: {},
          can_proceed: true,
          message: 'Success',
        })
      );

      component.onMcpConfigSubmit();
      await fixture.whenStable();

      expect(registrationService.processPhase).toHaveBeenCalled();
      expect(component.stepper.next).toHaveBeenCalled();
    });

    it('should send mcp_command in payload', async () => {
      component.mcpConfigForm.patchValue({
        mcp_server_type: 'stdio',
        mcp_command: '["node", "server.js"]',
      });

      registrationService.processPhase.mockReturnValue(
        of({
          session_id: 'test_session_123',
          current_phase: ToolRegistrationPhase.MCP_CONFIG,
          next_phase: ToolRegistrationPhase.CONNECTION_TEST,
          validation_errors: {},
          can_proceed: true,
          message: 'Success',
        })
      );

      component.onMcpConfigSubmit();
      await fixture.whenStable();

      const callArgs = registrationService.processPhase.mock.calls[0][0];
      expect(callArgs.data.mcp_command).toBeDefined();
      expect(
        Array.isArray(callArgs.data.mcp_command) ||
        typeof callArgs.data.mcp_command === 'string'
      ).toBe(true);
    });
  });

  describe('testConnection', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.sessionId = 'test_session_123';
    });

    it('should test connection successfully', async () => {
      registrationService.processPhase.mockReturnValue(
        of({
          session_id: 'test_session_123',
          current_phase: ToolRegistrationPhase.CONNECTION_TEST,
          next_phase: ToolRegistrationPhase.SECURITY_CONFIG,
          validation_errors: {},
          can_proceed: true,
          message: 'Connection successful',
        })
      );

      await component.testConnection();

      expect(component.loading).toBe(false);
      expect(component.connectionResult).toBeTruthy();
      expect(component.connectionResult!['success']).toBe(true);
    });

    it('should handle connection failure', async () => {
      registrationService.processPhase.mockReturnValue(
        throwError(() => ({ error: { detail: 'Connection failed' } }))
      );

      await component.testConnection();

      expect(component.connectionResult).toBeTruthy();
      expect(component.connectionResult!['success']).toBe(false);
    });
  });

  describe('onSecuritySubmit', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.stepper = {
        selectedIndex: 0,
        next: jest.fn(),
        previous: jest.fn(),
      } as unknown as MatStepper;
      component.sessionId = 'test_session_123';
      component.securityForm.patchValue({
        requires_authentication: true,
        authentication_type: 'api_key',
        secret_name: 'test_secret',
        secret_value: 'secret_value',
      });
    });

    it('should submit security config successfully', async () => {
      registrationService.processPhase.mockReturnValue(
        of({
          session_id: 'test_session_123',
          current_phase: ToolRegistrationPhase.SECURITY_CONFIG,
          next_phase: ToolRegistrationPhase.PERMISSIONS,
          validation_errors: {},
          can_proceed: true,
          message: 'Success',
        })
      );

      component.onSecuritySubmit();
      await fixture.whenStable();

      expect(registrationService.processPhase).toHaveBeenCalled();
      expect(component.stepper.next).toHaveBeenCalled();
    });
  });

  describe('onPermissionsSubmit', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.stepper = {
        selectedIndex: 0,
        next: jest.fn(),
        previous: jest.fn(),
      } as unknown as MatStepper;
      component.sessionId = 'test_session_123';
      component.permissionsForm.patchValue({
        rate_limit_per_minute: 60,
        max_concurrent_calls: 5,
      });
    });

    it('should submit permissions successfully', async () => {
      registrationService.processPhase.mockReturnValue(
        of({
          session_id: 'test_session_123',
          current_phase: ToolRegistrationPhase.PERMISSIONS,
          next_phase: ToolRegistrationPhase.REVIEW,
          validation_errors: {},
          can_proceed: true,
          message: 'Success',
        })
      );

      component.onPermissionsSubmit();
      await fixture.whenStable();

      expect(registrationService.processPhase).toHaveBeenCalled();
      expect(component.stepper.next).toHaveBeenCalled();
    });
  });

  describe('onReviewConfirm', () => {
    beforeEach(() => {
      fixture.detectChanges();
      (component as unknown as { snackBar: typeof snackBar }).snackBar =
        snackBar;
      component.sessionId = 'test_session_123';
      component.basicInfo = { name: 'Test Tool' };
    });

    it('should commit registration successfully', async () => {
      registrationService.processPhase
        .mockReturnValueOnce(
          of({
            session_id: 'test_session_123',
            current_phase: ToolRegistrationPhase.REVIEW,
            validation_errors: {},
            can_proceed: true,
            message: 'OK',
          })
        )
        .mockReturnValueOnce(
          of({
            session_id: 'test_session_123',
            current_phase: ToolRegistrationPhase.COMMIT,
            next_phase: null,
            validation_errors: {},
            can_proceed: true,
            tool_id: 'test-tool-id',
            message: 'Tool registered successfully',
          })
        );

      await component.onReviewConfirm();

      expect(registrationService.processPhase).toHaveBeenCalled();
      expect(draftStorage.clearDraft).toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['/admin/tools']);
    });
  });

  describe('onCancel', () => {
    beforeEach(() => {
      global.confirm = jest.fn().mockReturnValue(true);
      fixture.detectChanges();
      component.sessionId = 'test_session_123';
    });

    it('should cancel registration and cleanup', () => {
      registrationService.cancelRegistration.mockReturnValue(of(undefined));

      component.onCancel();

      expect(registrationService.cancelRegistration).toHaveBeenCalledWith(
        'test_session_123'
      );
      expect(router.navigate).toHaveBeenCalledWith(['/admin/tools']);
    });

    it('should navigate even if cancel fails', () => {
      registrationService.cancelRegistration.mockReturnValue(
        throwError(() => new Error('Cancel failed'))
      );

      component.onCancel();

      expect(router.navigate).toHaveBeenCalledWith(['/admin/tools']);
    });
  });

  describe('draft management', () => {
    it('should save draft on trigger', () => {
      fixture.detectChanges();
      component.sessionId = 'test_session_123';
      component.basicInfo = { tool_id: 'test_tool' };

      component.triggerDraftSave();

      // Wait for debounce
      setTimeout(() => {
        expect(draftStorage.saveDraft).toHaveBeenCalled();
      }, 500);
    });

    it('should load draft on init', () => {
      const draft = {
        sessionId: 'test_session_123',
        currentStep: 2,
        formData: {
          basicInfo: { tool_id: 'test_tool' },
        },
        timestamp: Date.now(),
      };

      draftStorage.hasDraft.mockReturnValue(true);
      draftStorage.loadDraft.mockReturnValue(draft as any);
      fixture.detectChanges();

      expect(component.sessionId).toBe('test_session_123');
    });
  });

  describe('ngOnDestroy', () => {
    it('should cleanup subscriptions', () => {
      fixture.detectChanges();
      const destroySpy = jest.spyOn(component['destroy$'], 'next');

      component.ngOnDestroy();

      expect(destroySpy).toHaveBeenCalled();
    });
  });
});
