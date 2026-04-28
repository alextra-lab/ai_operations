import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { TestQueryResult } from '../../models/test-query-result.model';
import { UseCaseValidationService } from '../../services/use-case-validation.service';
import { UseCaseTestPanelComponent } from './use-case-test-panel.component';

describe('UseCaseTestPanelComponent', () => {
  let component: UseCaseTestPanelComponent;
  let fixture: ComponentFixture<UseCaseTestPanelComponent>;
  let validationService: any;
  let snackBar: any;

  beforeEach(async () => {
    const validationServiceSpy = {
      testQuery: jest.fn(),
    };
    const snackBarSpy = {
      open: jest.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [UseCaseTestPanelComponent, NoopAnimationsModule],
      providers: [
        { provide: UseCaseValidationService, useValue: validationServiceSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UseCaseTestPanelComponent);
    component = fixture.componentInstance;
    validationService = TestBed.inject(UseCaseValidationService);
    snackBar = TestBed.inject(MatSnackBar);
    // Ensure component uses the same snackBar mock (standalone component injector)
    (component as any).snackBar = snackBar;

    component.useCaseId = 'test-001';
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should execute test query successfully', async () => {
    const mockResult: TestQueryResult = {
      success: true,
      query: 'test query',
      response: { answer: 'test answer' },
      execution_time_ms: 1000,
      timestamp: new Date().toISOString(),
    };

    validationService.testQuery.mockReturnValue(of(mockResult));
    component.testQuery = 'test query';

    await component.executeTest();

    expect(validationService.testQuery).toHaveBeenCalledWith(
      'test-001',
      'test query',
      undefined
    );
    expect(component.testResult).toEqual(mockResult);
    expect(snackBar.open).toHaveBeenCalled();
  });

  it('should not execute test without query', async () => {
    component.testQuery = '';

    await component.executeTest();

    expect(validationService.testQuery).not.toHaveBeenCalled();
  });

  it('should handle invalid expected output JSON', async () => {
    component.testQuery = 'test query';
    component.expectedOutputJson = 'invalid json';

    await component.executeTest();

    expect(snackBar.open).toHaveBeenCalledWith(
      'Invalid expected output JSON',
      'Close',
      { duration: 3000 }
    );
    expect(validationService.testQuery).not.toHaveBeenCalled();
  });

  it('should include expected output when valid JSON provided', async () => {
    const mockResult: TestQueryResult = {
      success: true,
      query: 'test query',
      response: { answer: 'test answer' },
      execution_time_ms: 1000,
      validation_passed: true,
      timestamp: new Date().toISOString(),
    };

    validationService.testQuery.mockReturnValue(of(mockResult));
    component.testQuery = 'test query';
    component.expectedOutputJson = '{"format": "json"}';

    await component.executeTest();

    expect(validationService.testQuery).toHaveBeenCalledWith(
      'test-001',
      'test query',
      { format: 'json' }
    );
  });

  it('should handle test execution errors', async () => {
    validationService.testQuery.mockReturnValue(
      throwError(() => new Error('Test error'))
    );
    component.testQuery = 'test query';

    await component.executeTest();

    expect(snackBar.open).toHaveBeenCalledWith(
      expect.stringContaining('Test error'),
      'Close',
      { duration: 5000 }
    );
  });

  it('should show failure notification for failed test', async () => {
    const mockResult: TestQueryResult = {
      success: false,
      query: 'test query',
      error: 'Test failed',
      execution_time_ms: 1000,
      timestamp: new Date().toISOString(),
    };

    validationService.testQuery.mockReturnValue(of(mockResult));
    component.testQuery = 'test query';

    await component.executeTest();

    expect(snackBar.open).toHaveBeenCalledWith('Test failed', 'Close', {
      duration: 3000,
    });
  });
});
