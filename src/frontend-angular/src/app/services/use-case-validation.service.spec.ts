import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../environments/environment';
import {
  TestQueryResult,
  TestSuiteResult,
} from '../models/test-query-result.model';
import { ValidationReport } from '../models/validation-report.model';
import { UseCaseValidationService } from './use-case-validation.service';

describe('UseCaseValidationService', () => {
  let service: UseCaseValidationService;
  let httpMock: HttpTestingController;
  const apiUrl = `${environment.apiUrl}/use-cases`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [UseCaseValidationService],
    });
    service = TestBed.inject(UseCaseValidationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('validateUseCase', () => {
    it('should validate a use case', () => {
      const mockReport: ValidationReport = {
        use_case_id: 'test-001',
        is_valid: true,
        can_publish: true,
        issues: [],
        errors: [],
        warnings: [],
        infos: [],
        validated_at: new Date().toISOString(),
      };

      service.validateUseCase('test-001').subscribe((report) => {
        expect(report).toEqual(mockReport);
      });

      const req = httpMock.expectOne(`${apiUrl}/test-001/validate`);
      expect(req.request.method).toBe('POST');
      req.flush(mockReport);
    });

    it('should handle validation errors', () => {
      const mockReport: ValidationReport = {
        use_case_id: 'test-002',
        is_valid: false,
        can_publish: false,
        issues: [],
        errors: [
          {
            rule_id: 'empty-system-prompt',
            severity: 'error',
            message: 'System prompt is empty',
          },
        ],
        warnings: [],
        infos: [],
        validated_at: new Date().toISOString(),
      };

      service.validateUseCase('test-002').subscribe((report) => {
        expect(report.is_valid).toBe(false);
        expect(report.errors.length).toBe(1);
      });

      const req = httpMock.expectOne(`${apiUrl}/test-002/validate`);
      req.flush(mockReport);
    });
  });

  describe('autoFixIssues', () => {
    it('should apply auto-fixes', () => {
      const mockResponse = {
        success: true,
        fixed_issues: 2,
        use_case: { use_case_id: 'test-001' },
      };

      service
        .autoFixIssues('test-001', ['rule-1', 'rule-2'])
        .subscribe((result) => {
          expect(result.success).toBe(true);
          expect(result.fixed_issues).toBe(2);
        });

      const req = httpMock.expectOne(`${apiUrl}/test-001/auto-fix`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ issue_ids: ['rule-1', 'rule-2'] });
      req.flush(mockResponse);
    });
  });

  describe('testQuery', () => {
    it('should execute test query', () => {
      const mockResult: TestQueryResult = {
        success: true,
        query: 'test query',
        response: { answer: 'test answer' },
        execution_time_ms: 1000,
        timestamp: new Date().toISOString(),
      };

      service.testQuery('test-001', 'test query').subscribe((result) => {
        expect(result.success).toBe(true);
        expect(result.query).toBe('test query');
      });

      const req = httpMock.expectOne(`${apiUrl}/test-001/test`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body.query).toBe('test query');
      req.flush(mockResult);
    });

    it('should include expected output when provided', () => {
      const expectedOutput = { format: 'json' };
      const mockResult: TestQueryResult = {
        success: true,
        query: 'test query',
        response: { answer: 'test answer' },
        execution_time_ms: 1000,
        validation_passed: true,
        timestamp: new Date().toISOString(),
      };

      service.testQuery('test-001', 'test query', expectedOutput).subscribe();

      const req = httpMock.expectOne(`${apiUrl}/test-001/test`);
      expect(req.request.body.expected_output).toEqual(expectedOutput);
      req.flush(mockResult);
    });
  });

  describe('runTestSuite', () => {
    it('should run test suite', () => {
      const testCases = [{ query: 'query 1' }, { query: 'query 2' }];
      const mockResult: TestSuiteResult = {
        use_case_id: 'test-001',
        total_tests: 2,
        passed: 2,
        failed: 0,
        pass_rate: 1.0,
        avg_execution_time_ms: 500,
        results: [],
        timestamp: new Date().toISOString(),
      };

      service.runTestSuite('test-001', testCases).subscribe((result) => {
        expect(result.total_tests).toBe(2);
        expect(result.passed).toBe(2);
      });

      const req = httpMock.expectOne(`${apiUrl}/test-001/test-suite`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body.test_cases).toEqual(testCases);
      req.flush(mockResult);
    });
  });
});
