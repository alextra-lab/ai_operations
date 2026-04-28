import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  TestCase,
  TestQueryResult,
  TestSuiteResult,
} from '../models/test-query-result.model';
import { ValidationReport } from '../models/validation-report.model';

/**
 * Service for Use Case validation and testing.
 */
@Injectable({
  providedIn: 'root',
})
export class UseCaseValidationService {
  private apiUrl = `${environment.apiUrl}/use-cases`;

  constructor(private http: HttpClient) {}

  /**
   * Validate Use Case configuration and prompts.
   *
   * @param useCaseId Use Case ID to validate
   * @returns Observable of ValidationReport
   */
  validateUseCase(useCaseId: string): Observable<ValidationReport> {
    return this.http.post<ValidationReport>(
      `${this.apiUrl}/${useCaseId}/validate`,
      {}
    );
  }

  /**
   * Auto-fix validation issues.
   *
   * @param useCaseId Use Case ID
   * @param issueIds List of rule IDs to auto-fix
   * @returns Observable of auto-fix result
   */
  autoFixIssues(
    useCaseId: string,
    issueIds: string[]
  ): Observable<{ success: boolean; fixed_issues: number; use_case: any }> {
    return this.http.post<any>(`${this.apiUrl}/${useCaseId}/auto-fix`, {
      issue_ids: issueIds,
    });
  }

  /**
   * Execute a test query against Use Case.
   *
   * @param useCaseId Use Case ID to test
   * @param query Test query text
   * @param expectedOutput Optional expected output for validation
   * @returns Observable of TestQueryResult
   */
  testQuery(
    useCaseId: string,
    query: string,
    expectedOutput?: Record<string, any>
  ): Observable<TestQueryResult> {
    return this.http.post<TestQueryResult>(`${this.apiUrl}/${useCaseId}/test`, {
      query,
      expected_output: expectedOutput,
    });
  }

  /**
   * Run a test suite against Use Case.
   *
   * @param useCaseId Use Case ID to test
   * @param testCases Array of test cases
   * @returns Observable of TestSuiteResult
   */
  runTestSuite(
    useCaseId: string,
    testCases: TestCase[]
  ): Observable<TestSuiteResult> {
    return this.http.post<TestSuiteResult>(
      `${this.apiUrl}/${useCaseId}/test-suite`,
      {
        test_cases: testCases,
      }
    );
  }
}
