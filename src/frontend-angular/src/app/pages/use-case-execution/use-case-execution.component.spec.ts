/**
 * Use Case Execution Component Tests
 *
 * Tests P4-TOOLS-06 refactored component with Layered Layout,
 * QueryResultsPanel integration, and structured output rendering.
 */

import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { MatSnackBar } from '@angular/material/snack-bar';
import { UseCaseExecutionService } from '../../api/services/use-case-execution.service';
import { UseCaseService } from '../../api/services/use-case.service';
import { OutputFormattingService } from '../../services/output-formatting.service';
import { SessionStorageService } from '../../services/session-storage.service';
import { UseCaseExecutionComponent } from './use-case-execution.component';

import {
  ExecutionResponse,
  UseCase,
  UseCaseConfig,
} from '../../api/models/use-case.models';

describe('UseCaseExecutionComponent', () => {
  let component: UseCaseExecutionComponent;
  let fixture: ComponentFixture<UseCaseExecutionComponent>;
  let mockUseCaseService: Partial<UseCaseService>;
  let mockExecutionService: Partial<UseCaseExecutionService>;
  let mockOutputFormattingService: Partial<OutputFormattingService>;
  let mockSessionStorage: Partial<SessionStorageService>;
  let mockSnackBar: Partial<MatSnackBar>;
  let mockRouter: Partial<Router>;
  let mockActivatedRoute: any;

  const mockUseCase: UseCase = {
    id: 'uc-123',
    name: 'Test Use Case',
    description: 'Test description',
    category: 'threat_analysis',
    intent_type: 'QUERY',
    lifecycle_state: 'published',
    created_at: '2025-10-31T10:00:00Z',
    updated_at: '2025-10-31T10:00:00Z',
    created_by_user_id: 'user-123',
    updated_by_user_id: 'user-123',
  };

  const mockConfig: UseCaseConfig = {
    template_config: {
      input_fields: [
        {
          name: 'query',
          label: 'Query',
          type: 'text',
          required: true,
          placeholder: 'Enter query',
          description: 'Search query',
        },
      ],
    },
    execution_config: {
      default_temperature: 0.7,
      default_top_k: 10,
      default_similarity_threshold: 0.6,
      default_model: 'gpt-4',
      supports_streaming: true,
    },
    output_contract: {},
  };

  const mockExecutionResult: ExecutionResponse = {
    response: 'Test response',
    sources: [],
    metrics: {
      total_duration_ms: 1500,
      total_tokens: 250,
      input_tokens: 100,
      output_tokens: 150,
      chunks_retrieved: 5,
      cost_usd: 0.0025,
    },
  };

  beforeEach(async () => {
    mockUseCaseService = {
      getUseCase: jest.fn(),
      getUseCaseConfig: jest.fn(),
    } as any;

    mockExecutionService = {
      executeUseCase: jest.fn(),
      executeUseCaseStreaming: jest.fn(),
      disconnectWebSocket: jest.fn(),
    } as any;

    mockOutputFormattingService = {
      formatResponse: jest.fn(),
    } as any;

    mockSessionStorage = {
      createSession: jest.fn(),
      addMessage: jest.fn(),
    } as any;

    mockSnackBar = {
      open: jest.fn(),
    } as any;

    mockRouter = {
      navigate: jest.fn(),
    } as any;

    mockActivatedRoute = {
      params: of({ id: 'uc-123' }),
    };

    (mockUseCaseService.getUseCase as jest.Mock).mockReturnValue(
      of(mockUseCase)
    );
    (mockUseCaseService.getUseCaseConfig as jest.Mock).mockReturnValue(
      of(mockConfig)
    );
    (mockSessionStorage.createSession as jest.Mock).mockResolvedValue({
      id: 'session-123',
      title: 'Test Session',
      use_case_id: 'uc-123',
      created_at: new Date().toISOString(),
      ttl_hours: 24,
      messages: [],
    });
    (mockSessionStorage.addMessage as jest.Mock).mockResolvedValue(undefined);

    await TestBed.configureTestingModule({
      imports: [
        UseCaseExecutionComponent,
        ReactiveFormsModule,
        NoopAnimationsModule,
        HttpClientTestingModule,
      ],
      providers: [
        { provide: UseCaseService, useValue: mockUseCaseService },
        { provide: UseCaseExecutionService, useValue: mockExecutionService },
        {
          provide: OutputFormattingService,
          useValue: mockOutputFormattingService,
        },
        { provide: SessionStorageService, useValue: mockSessionStorage },
        { provide: MatSnackBar, useValue: mockSnackBar },
        { provide: Router, useValue: mockRouter },
        { provide: ActivatedRoute, useValue: mockActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UseCaseExecutionComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Initialization', () => {
    it('should load use case on init', () => {
      fixture.detectChanges();

      expect(mockUseCaseService.getUseCase).toHaveBeenCalledWith('uc-123');
      expect(mockUseCaseService.getUseCaseConfig).toHaveBeenCalledWith(
        'uc-123'
      );
      expect(component.useCase).toEqual(mockUseCase);
      expect(component.useCaseConfig).toEqual(mockConfig);
    });

    it('should setup execution form from config', () => {
      fixture.detectChanges();

      expect(component.executionForm.get('query')).toBeTruthy();
      expect(component.executionForm.get('query')?.hasError('required')).toBe(
        true
      );
    });

    it('should setup overrides form from config', () => {
      fixture.detectChanges();

      expect(component.overridesForm.get('temperature')).toBeTruthy();
      expect(component.overridesForm.get('temperature')?.value).toBe(0.7);
    });

    it('should create conversation session', async () => {
      fixture.detectChanges();
      await fixture.whenStable();

      expect(mockSessionStorage.createSession).toHaveBeenCalled();
      expect(component.currentSessionId).toBe('session-123');
    });

    it('should handle use case load error', () => {
      mockUseCaseService.getUseCase.mockReturnValue(
        throwError(() => new Error('Load failed'))
      );

      fixture.detectChanges();

      expect(component.error).toBe('Failed to load use case details.');
      expect(component.isLoading).toBe(false);
    });

    it('should handle config load error', () => {
      mockUseCaseService.getUseCaseConfig.mockReturnValue(
        throwError(() => new Error('Config load failed'))
      );

      fixture.detectChanges();

      expect(component.error).toBe('Failed to load use case configuration.');
      expect(component.isLoading).toBe(false);
    });
  });

  describe('Form Validation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should validate required fields', () => {
      expect(component.canExecute).toBe(false);

      component.executionForm.patchValue({ query: 'test query' });
      expect(component.canExecute).toBe(true);
    });

    it('should return validation message for required field', () => {
      const queryControl = component.executionForm.get('query');
      queryControl?.markAsTouched();

      expect(component.getFieldValidationMessage('query')).toBe(
        'This field is required'
      );
    });

    it('should not execute with invalid form', () => {
      component.executionForm.patchValue({ query: '' });
      component.execute();

      expect(mockExecutionService.executeUseCase).not.toHaveBeenCalled();
    });
  });

  describe('Standard Execution', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.executionForm.patchValue({ query: 'test query' });
      mockExecutionService.executeUseCase.mockReturnValue(
        of(mockExecutionResult)
      );
    });

    it('should execute use case successfully', async () => {
      component.execute();
      await fixture.whenStable();

      expect(mockExecutionService.executeUseCase).toHaveBeenCalled();
      expect(component.executionResult).toEqual(mockExecutionResult);
      expect(component.isExecuting).toBe(false);
      expect(component.executionProgress).toBe(100);
    });

    it('should add messages to conversation', async () => {
      component.execute();
      await fixture.whenStable();

      expect(component.conversationMessages.length).toBe(2); // User + assistant
      expect(component.conversationMessages[0].role).toBe('user');
      expect(component.conversationMessages[1].role).toBe('assistant');
    });

    it('should collapse input panel on execute', () => {
      component.inputPanelExpanded = true;
      component.execute();

      expect(component.inputPanelExpanded).toBe(false);
    });

    it('should handle execution error', async () => {
      mockExecutionService.executeUseCase.mockReturnValue(
        throwError(() => new Error('Execution failed'))
      );

      component.execute();
      await fixture.whenStable();

      expect(component.executionError).toBe('Execution failed');
      expect(component.isExecuting).toBe(false);
      expect(component.executionProgress).toBe(0);
    });

    it('should include overrides when enabled', () => {
      component.showOverrides = true;
      component.overridesForm.patchValue({ temperature: 0.9 });

      component.execute();

      expect(mockExecutionService.executeUseCase).toHaveBeenCalledWith(
        expect.objectContaining({
          overrides: expect.objectContaining({ temperature: 0.9 }),
        })
      );
    });
  });

  describe('Streaming Execution', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.executionForm.patchValue({ query: 'test query' });
      component.overridesForm.patchValue({ streaming: true });
    });

    it('should handle streaming chunks', () => {
      mockExecutionService.executeUseCaseStreaming.mockReturnValue(
        of(
          { type: 'chunk', data: 'Hello ' },
          { type: 'chunk', data: 'World' },
          {
            type: 'complete',
            data: mockExecutionResult,
          }
        )
      );

      component.execute();

      expect(component.streamingResponse).toBe('Hello World');
      expect(component.isStreaming).toBe(false);
      expect(component.executionResult).toEqual(mockExecutionResult);
    });

    it('should handle streaming error', () => {
      mockExecutionService.executeUseCaseStreaming.mockReturnValue(
        of({ type: 'error', data: { message: 'Stream failed' } })
      );

      component.execute();

      expect(component.executionError).toBe('Stream failed');
      expect(component.isStreaming).toBe(false);
    });
  });

  describe('Structured Output', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.executionForm.patchValue({ query: 'test query' });
    });

    it.skip('should format structured output when available', async () => {
      const resultWithStructuredData = {
        ...mockExecutionResult,
        structured_data: { iocs: [{ type: 'ip', value: '192.0.2.1' }] },
      };

      mockExecutionService.executeUseCase.mockReturnValue(
        of(resultWithStructuredData)
      );

      const formattedOutput = {
        raw_content: 'Test',
        structured_data: {},
        template: {} as any,
        rendered_sections: [],
      };

      mockOutputFormattingService.formatResponse.mockReturnValue(
        Promise.resolve(formattedOutput)
      );

      component.outputTemplate = {} as any;
      component.execute();
      await fixture.whenStable();

      expect(mockOutputFormattingService.formatResponse).toHaveBeenCalled();
      expect(component.formattedOutput).toEqual(formattedOutput);
    });

    it('should not format when no template configured', async () => {
      mockExecutionService.executeUseCase.mockReturnValue(
        of(mockExecutionResult)
      );

      component.outputTemplate = null;
      component.execute();
      await fixture.whenStable();

      expect(mockOutputFormattingService.formatResponse).not.toHaveBeenCalled();
    });
  });

  describe('UI Actions', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should toggle overrides', () => {
      expect(component.showOverrides).toBe(false);
      component.toggleOverrides();
      expect(component.showOverrides).toBe(true);
    });

    it('should reset execution state', () => {
      component.executionResult = mockExecutionResult;
      component.executionError = 'Error';
      component.conversationMessages = [
        { id: '1', role: 'user', content: 'test', timestamp: '' },
      ];

      component.resetExecution();

      expect(component.executionResult).toBeNull();
      expect(component.executionError).toBeNull();
      expect(component.conversationMessages).toEqual([]);
      expect(component.inputPanelExpanded).toBe(true);
    });

    it('should navigate to use cases list', () => {
      component.navigateToUseCases();
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/use-cases']);
    });

    it('should cancel execution', () => {
      component.isExecuting = true;
      component.cancelExecution();

      expect(mockExecutionService.disconnectWebSocket).toHaveBeenCalled();
      expect(component.isExecuting).toBe(false);
    });
  });

  describe('Template Helpers', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should check if has input fields', () => {
      expect(component.hasInputFields).toBe(true);
    });

    it('should check if can execute', () => {
      expect(component.canExecute).toBe(false);
      component.executionForm.patchValue({ query: 'test' });
      expect(component.canExecute).toBe(true);
    });

    it('should check if has results', () => {
      expect(component.hasResults).toBe(false);
      component.conversationMessages = [
        { id: '1', role: 'user', content: 'test', timestamp: '' },
        { id: '2', role: 'assistant', content: 'response', timestamp: '' },
      ];
      expect(component.hasResults).toBe(true);
    });

    it('should check if has error', () => {
      expect(component.hasError).toBe(false);
      component.executionError = 'Error';
      expect(component.hasError).toBe(true);
    });

    it('should check if supports streaming', () => {
      expect(component.supportsStreaming).toBe(true);
    });

    it('should check if has structured output', () => {
      expect(component.hasStructuredOutput).toBe(false);
      component.formattedOutput = {
        raw_content: '',
        structured_data: {},
        template: {} as any,
        rendered_sections: [
          {
            section_id: '1',
            title: 'Test',
            component_type: 'table',
            data: [],
            config: {},
            width: 'full',
          },
        ],
      };
      expect(component.hasStructuredOutput).toBe(true);
    });
  });

  describe('Formatting Helpers', () => {
    it('should format tokens', () => {
      expect(component.formatTokens(500)).toBe('500');
      expect(component.formatTokens(1500)).toBe('1.5K');
      expect(component.formatTokens(1500000)).toBe('1.5M');
    });

    it('should format duration', () => {
      expect(component.formatDuration(500)).toBe('500ms');
      expect(component.formatDuration(1500)).toBe('1.5s');
      expect(component.formatDuration(125000)).toBe('2m 5s');
    });

    it('should get category display name', () => {
      expect(component.getCategoryDisplayName('threat_analysis')).toBe(
        'Threat Analysis'
      );
    });
  });

  describe('Export Events', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it.skip('should handle export complete', () => {
      component.onExportComplete({ format: 'json', filename: 'export.json' });
      expect(mockSnackBar.open).toHaveBeenCalledWith(
        'Exported as JSON',
        'Close',
        expect.any(Object)
      );
    });

    it.skip('should handle summary generated', () => {
      component.onSummaryGenerated({ summary: 'Test summary', type: 'brief' });
      expect(mockSnackBar.open).toHaveBeenCalledWith(
        'Brief summary generated',
        'Close',
        expect.any(Object)
      );
    });
  });
});
