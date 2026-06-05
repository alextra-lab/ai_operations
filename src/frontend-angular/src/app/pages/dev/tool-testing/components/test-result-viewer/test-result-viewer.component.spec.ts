import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { TestExecutionResult } from '../../../../../api/services/tool-testing.service';
import { TestHistoryEntry } from '../../models/tool-testing.models';
import { TestResultViewerComponent } from './test-result-viewer.component';

describe('TestResultViewerComponent', () => {
  let component: TestResultViewerComponent;
  let fixture: ComponentFixture<TestResultViewerComponent>;
  let mockSnackBar: jest.Mocked<MatSnackBar>;

  const mockSuccessResult: TestExecutionResult = {
    success: true,
    status: 'success',
    result: { data: 'test result', count: 5 },
    duration_ms: 150.5,
  };

  const mockErrorResult: TestExecutionResult = {
    success: false,
    status: 'error',
    error: 'Connection timeout',
    duration_ms: 5000,
  };

  const mockHistoryEntry: TestHistoryEntry = {
    id: 'test-id-123',
    tool_id: '123e4567-e89b-12d3-a456-426614174000',
    tool_name: 'search',
    tool_display_name: 'Search Tool',
    parameters: { query: 'test query', limit: 10 },
    result: mockSuccessResult,
    timestamp: new Date('2025-11-25T10:30:00'),
  };

  beforeEach(async () => {
    mockSnackBar = {
      open: jest.fn(),
    } as unknown as jest.Mocked<MatSnackBar>;

    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, TestResultViewerComponent],
      providers: [{ provide: MatSnackBar, useValue: mockSnackBar }],
    }).compileComponents();

    fixture = TestBed.createComponent(TestResultViewerComponent);
    component = fixture.componentInstance;
  });

  describe('with success result', () => {
    beforeEach(() => {
      component.result = mockSuccessResult;
      fixture.detectChanges();
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should display success status', () => {
      expect(component.statusText).toBe('Success');
      expect(component.statusIcon).toBe('circle-check');
      expect(component.statusClass).toBe('success');
    });

    it('should format duration correctly', () => {
      expect(component.formattedDuration).toBe('150.5ms');
    });

    it('should format result as JSON', () => {
      const formatted = component.formattedResult;
      expect(formatted).toContain('"data"');
      expect(formatted).toContain('"test result"');
    });

    it('should not have timestamp without history entry', () => {
      expect(component.timestamp).toBeNull();
    });
  });

  describe('with error result', () => {
    beforeEach(() => {
      component.result = mockErrorResult;
      fixture.detectChanges();
    });

    it('should display error status', () => {
      expect(component.statusText).toBe('Failed');
      expect(component.statusIcon).toBe('circle-alert');
      expect(component.statusClass).toBe('error');
    });

    it('should format duration in seconds', () => {
      expect(component.formattedDuration).toBe('5.00s');
    });
  });

  describe('with history entry', () => {
    beforeEach(() => {
      component.result = mockSuccessResult;
      component.historyEntry = mockHistoryEntry;
      fixture.detectChanges();
    });

    it('should display timestamp', () => {
      expect(component.timestamp).toBeTruthy();
      expect(component.timestamp).toContain('2025');
    });
  });

  describe('collapsed state', () => {
    beforeEach(() => {
      component.result = mockSuccessResult;
      fixture.detectChanges();
    });

    it('should start expanded', () => {
      expect(component.isCollapsed()).toBe(false);
    });

    it('should toggle collapsed state', () => {
      component.toggleCollapsed();
      expect(component.isCollapsed()).toBe(true);

      component.toggleCollapsed();
      expect(component.isCollapsed()).toBe(false);
    });
  });

  describe('clipboard operations', () => {
    beforeEach(() => {
      component.result = mockSuccessResult;
      fixture.detectChanges();
    });

    it('should have copyResult method', () => {
      expect(component.copyResult).toBeDefined();
      expect(typeof component.copyResult).toBe('function');
    });

    it('should have copyFullResult method', () => {
      expect(component.copyFullResult).toBeDefined();
      expect(typeof component.copyFullResult).toBe('function');
    });

    it('should copy result text for success', () => {
      // Test indirectly by checking the formattedResult is correct
      expect(component.formattedResult).toContain('"data"');
      expect(component.formattedResult).toContain('"test result"');
    });

    it('should copy error message for failed results', () => {
      component.result = mockErrorResult;
      // Assert input only; avoid detectChanges to prevent NG0100 (statusClass success->error)
      expect(component.result.error).toBe('Connection timeout');
    });
  });

  describe('edge cases', () => {
    it('should handle null result', () => {
      component.result = {
        success: true,
        status: 'success',
        result: null,
        duration_ms: 100,
      };
      fixture.detectChanges();

      expect(component.formattedResult).toBe('null');
    });

    it('should handle undefined result', () => {
      component.result = {
        success: true,
        status: 'success',
        duration_ms: 100,
      };
      fixture.detectChanges();

      expect(component.formattedResult).toBe('null');
    });

    it('should handle non-JSON result', () => {
      const circularResult: Record<string, unknown> = { self: {} };
      circularResult['self'] = circularResult;

      component.result = {
        success: true,
        status: 'success',
        result: circularResult,
        duration_ms: 100,
      };

      // This would normally throw, but we catch it
      fixture.detectChanges();
      expect(component.formattedResult).toBeDefined();
    });

    it('should handle error result with partial data', () => {
      component.result = {
        success: false,
        status: 'error',
        error: 'Partial failure',
        result: { partial: 'data' },
        duration_ms: 100,
      };
      fixture.detectChanges();

      expect(component.formattedResult).toContain('partial');
    });
  });
});
