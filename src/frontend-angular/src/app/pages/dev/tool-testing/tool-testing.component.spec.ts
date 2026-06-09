import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  tick,
} from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { ToolTestingService } from '../../../api/services/tool-testing.service';
import { ToolAdminService } from '../../admin/tool-management/services/tool-admin.service';
import { ToolTestingComponent } from './tool-testing.component';

describe('ToolTestingComponent', () => {
  let component: ToolTestingComponent;
  let fixture: ComponentFixture<ToolTestingComponent>;
  let toolAdminService: jest.Mocked<ToolAdminService>;
  let toolTestingService: jest.Mocked<ToolTestingService>;

  const mockTools = [
    {
      id: '123e4567-e89b-12d3-a456-426614174000',
      tool_id: 'search_tool',
      name: 'Search Tool',
      description: 'A search tool',
      category: 'search',
      is_enabled: true,
      is_healthy: true,
      requires_authentication: false,
    },
    {
      id: '223e4567-e89b-12d3-a456-426614174001',
      tool_id: 'disabled_tool',
      name: 'Disabled Tool',
      description: 'A disabled tool',
      category: 'other',
      is_enabled: false,
      is_healthy: false,
      requires_authentication: false,
    },
  ];

  beforeEach(async () => {
    const mockToolAdminService = {
      listTools: jest.fn(),
    };

    const mockToolTestingService = {
      executeTest: jest.fn(),
      validateParameters: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ToolTestingComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ToolAdminService, useValue: mockToolAdminService },
        { provide: ToolTestingService, useValue: mockToolTestingService },
      ],
    }).compileComponents();

    toolAdminService = TestBed.inject(
      ToolAdminService
    ) as jest.Mocked<ToolAdminService>;
    toolTestingService = TestBed.inject(
      ToolTestingService
    ) as jest.Mocked<ToolTestingService>;

    // Default mock return
    toolAdminService.listTools.mockReturnValue(of(mockTools));
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ToolTestingComponent);
    component = fixture.componentInstance;
  });

  describe('initialization', () => {
    it('should create', () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it('should load tools on init', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(toolAdminService.listTools).toHaveBeenCalled();
      expect(component.tools().length).toBe(1); // Only enabled tools
      expect(component.isLoadingTools).toBe(false);
    }));

    it('should filter out disabled tools', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      const tools = component.tools();
      expect(tools.every((t) => t.is_enabled)).toBe(true);
    }));

    it('should handle tool loading error', fakeAsync(() => {
      toolAdminService.listTools.mockReturnValue(
        throwError(() => new Error('Load failed'))
      );

      fixture.detectChanges();
      tick();

      expect(component.tools().length).toBe(0);
      expect(component.isLoadingTools).toBe(false);
    }));
  });

  describe('tool selection', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should select a tool', () => {
      const tool = component.tools()[0];
      component.onToolSelect(tool);

      expect(component.selectedTool()).toBe(tool);
      expect(component.toolName).toBe(tool.tool_id);
    });

    it('should clear results on tool selection', () => {
      component.currentResult.set({
        success: true,
        status: 'success',
        duration_ms: 100,
      });

      const tool = component.tools()[0];
      component.onToolSelect(tool);

      expect(component.currentResult()).toBeNull();
      expect(component.validationMessage()).toBeNull();
    });

    it('should set default empty params when no schema', () => {
      const tool = component.tools()[0];
      component.onToolSelect(tool);

      // Without parameters_schema, params should be empty object placeholder
      expect(component.parametersJson).toContain('{');
      expect(component.parametersJson).toContain('}');
    });
  });

  describe('JSON validation', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
      component.onToolSelect(component.tools()[0]);
    }));

    it('should validate valid JSON', () => {
      component.parametersJson = '{"query": "test"}';
      component.validateJson();

      expect(component.jsonValidationStatus).toBe('valid');
      expect(component.jsonError).toBe('');
    });

    it('should detect invalid JSON', () => {
      component.parametersJson = '{"invalid": }';
      component.validateJson();

      expect(component.jsonValidationStatus).toBe('invalid');
      expect(component.jsonError).toBe('Invalid JSON syntax');
    });

    it('should detect empty JSON', () => {
      component.parametersJson = '{}';
      component.validateJson();

      expect(component.jsonValidationStatus).toBe('empty');
    });

    it('should clear parameters', () => {
      component.parametersJson = '{"query": "test"}';
      component.clearParameters();

      expect(component.parametersJson).toBe('{\n  \n}');
      expect(component.jsonValidationStatus).toBe('empty');
    });

    it('should load example parameters', () => {
      component.loadExample();
      const params = JSON.parse(component.parametersJson);

      expect(params).toBeDefined();
      expect(component.jsonValidationStatus).toBe('valid');
    });
  });

  describe('parameter validation', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
      component.onToolSelect(component.tools()[0]);
      component.parametersJson = '{"query": "test"}';
      component.validateJson();
    }));

    it('should validate parameters successfully', fakeAsync(() => {
      toolTestingService.validateParameters.mockReturnValue(
        of({ valid: true, message: 'Parameters are valid' })
      );

      component.validateParameters();
      tick();

      expect(component.isValidating).toBe(false);
      expect(component.validationSuccess()).toBe(true);
      expect(component.validationMessage()).toBe('Parameters are valid');
    }));

    it('should handle validation failure', fakeAsync(() => {
      toolTestingService.validateParameters.mockReturnValue(
        of({ valid: false, error: 'Missing required field' })
      );

      component.validateParameters();
      tick();

      expect(component.validationSuccess()).toBe(false);
      expect(component.validationMessage()).toBe('Missing required field');
    }));

    it('should handle validation API error', fakeAsync(() => {
      toolTestingService.validateParameters.mockReturnValue(
        throwError(() => ({ error: { detail: 'Tool not found' } }))
      );

      component.validateParameters();
      tick();

      expect(component.validationSuccess()).toBe(false);
    }));

    it('should not validate with invalid JSON', () => {
      component.jsonValidationStatus = 'invalid';
      component.validateParameters();

      expect(toolTestingService.validateParameters).not.toHaveBeenCalled();
    });

    it('should not validate without selected tool', () => {
      component.selectedTool.set(null);
      component.validateParameters();

      expect(toolTestingService.validateParameters).not.toHaveBeenCalled();
    });
  });

  describe('test execution', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
      component.onToolSelect(component.tools()[0]);
      component.parametersJson = '{"query": "test"}';
      component.validateJson();
    }));

    it('should execute test successfully', fakeAsync(() => {
      const mockResult = {
        success: true,
        status: 'success',
        result: { data: 'test result' },
        duration_ms: 150,
      };
      toolTestingService.executeTest.mockReturnValue(of(mockResult));

      component.executeTest();
      tick();

      expect(component.isExecuting).toBe(false);
      expect(component.currentResult()).toEqual(mockResult);
      expect(component.testHistory().length).toBe(1);
    }));

    it('should handle test execution failure', fakeAsync(() => {
      const mockResult = {
        success: false,
        status: 'error',
        error: 'Connection timeout',
        duration_ms: 5000,
      };
      toolTestingService.executeTest.mockReturnValue(of(mockResult));

      component.executeTest();
      tick();

      expect(component.currentResult()?.success).toBe(false);
      expect(component.testHistory().length).toBe(1);
    }));

    it('should handle API error', fakeAsync(() => {
      toolTestingService.executeTest.mockReturnValue(
        throwError(() => ({ error: { detail: 'Server error' } }))
      );

      component.executeTest();
      tick();

      expect(component.isExecuting).toBe(false);
      expect(component.currentResult()).toBeNull();
    }));

    it('should not execute with invalid JSON', () => {
      component.jsonValidationStatus = 'invalid';
      component.executeTest();

      expect(toolTestingService.executeTest).not.toHaveBeenCalled();
    });

    it('should not execute without selected tool', () => {
      component.selectedTool.set(null);
      component.executeTest();

      expect(toolTestingService.executeTest).not.toHaveBeenCalled();
    });

    it('should use tool name override', fakeAsync(() => {
      toolTestingService.executeTest.mockReturnValue(
        of({ success: true, status: 'success', duration_ms: 100 })
      );

      component.toolName = 'custom_tool_name';
      component.executeTest();
      tick();

      expect(toolTestingService.executeTest).toHaveBeenCalledWith(
        expect.objectContaining({ tool_name: 'custom_tool_name' })
      );
    }));
  });

  describe('test history', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
      component.onToolSelect(component.tools()[0]);
      component.parametersJson = '{"query": "test"}';
      component.validateJson();
    }));

    it('should add test to history', fakeAsync(() => {
      toolTestingService.executeTest.mockReturnValue(
        of({ success: true, status: 'success', duration_ms: 100 })
      );

      component.executeTest();
      tick();

      expect(component.testHistory().length).toBe(1);
      expect(component.testHistory()[0].tool_id).toBe(
        component.selectedTool()?.id
      );
    }));

    it('should limit history to max entries', fakeAsync(() => {
      toolTestingService.executeTest.mockReturnValue(
        of({ success: true, status: 'success', duration_ms: 100 })
      );

      for (let i = 0; i < 15; i++) {
        component.executeTest();
        tick();
      }

      expect(component.testHistory().length).toBe(component.maxHistory);
    }));

    it('should view history entry', fakeAsync(() => {
      toolTestingService.executeTest.mockReturnValue(
        of({ success: true, status: 'success', duration_ms: 100 })
      );

      component.executeTest();
      tick();

      const entry = component.testHistory()[0];
      component.viewHistoryEntry(entry);

      expect(component.selectedHistoryEntry()).toBe(entry);
      expect(component.currentResult()).toBe(entry.result);
    }));

    it('should clear history', fakeAsync(() => {
      toolTestingService.executeTest.mockReturnValue(
        of({ success: true, status: 'success', duration_ms: 100 })
      );

      component.executeTest();
      tick();

      component.clearHistory();

      expect(component.testHistory().length).toBe(0);
      expect(component.selectedHistoryEntry()).toBeNull();
    }));
  });

  describe('computed properties', () => {
    beforeEach(fakeAsync(() => {
      fixture.detectChanges();
      tick();
    }));

    it('should disable execute when no tool selected', () => {
      expect(component.isExecuteDisabled).toBe(true);
    });

    it('should disable execute when JSON invalid', () => {
      component.onToolSelect(component.tools()[0]);
      component.jsonValidationStatus = 'invalid';

      expect(component.isExecuteDisabled).toBe(true);
    });

    it('should disable execute when executing', () => {
      component.onToolSelect(component.tools()[0]);
      component.isExecuting = true;

      expect(component.isExecuteDisabled).toBe(true);
    });

    it('should enable execute when valid', () => {
      component.onToolSelect(component.tools()[0]);
      component.parametersJson = '{"query": "test"}';
      component.validateJson();

      expect(component.isExecuteDisabled).toBe(false);
    });
  });

  describe('formatting helpers', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should format duration in milliseconds', () => {
      expect(component.formatDuration(150.5)).toBe('150.5ms');
    });

    it('should format duration in seconds', () => {
      expect(component.formatDuration(1500)).toBe('1.50s');
    });

    it('should format timestamp', () => {
      const date = new Date('2025-11-25T10:30:00');
      const formatted = component.formatTimestamp(date);
      expect(formatted).toContain(':');
    });

    it('should get success status icon', () => {
      const entry = {
        id: '1',
        tool_id: 'test',
        tool_name: 'test',
        tool_display_name: 'Test',
        parameters: {},
        result: { success: true, status: 'success', duration_ms: 100 },
        timestamp: new Date(),
      };

      expect(component.getStatusIcon(entry)).toBe('circle-check');
    });

    it('should get error status icon', () => {
      const entry = {
        id: '1',
        tool_id: 'test',
        tool_name: 'test',
        tool_display_name: 'Test',
        parameters: {},
        result: { success: false, status: 'error', duration_ms: 100 },
        timestamp: new Date(),
      };

      expect(component.getStatusIcon(entry)).toBe('circle-alert');
    });
  });

  describe('schema example generation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should generate string defaults', () => {
      const schema = {
        properties: { name: { type: 'string' } },
      };
      const example = component.generateExampleFromSchema(schema);
      expect(example['name']).toBe('example_value');
    });

    it('should generate number defaults', () => {
      const schema = {
        properties: { count: { type: 'number', default: 5 } },
      };
      const example = component.generateExampleFromSchema(schema);
      expect(example['count']).toBe(5);
    });

    it('should generate boolean defaults', () => {
      const schema = {
        properties: { enabled: { type: 'boolean' } },
      };
      const example = component.generateExampleFromSchema(schema);
      expect(example['enabled']).toBe(true);
    });

    it('should handle missing properties', () => {
      const schema = {};
      const example = component.generateExampleFromSchema(schema);
      expect(Object.keys(example).length).toBe(0);
    });
  });
});
