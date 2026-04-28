/**
 * Test query result models for Use Case testing.
 */

export interface TestQueryResult {
  success: boolean;
  query: string;
  response?: Record<string, any>;
  error?: string;
  execution_time_ms: number;
  validation_passed?: boolean;
  validation_message?: string;
  timestamp: string;
}

export interface TestCase {
  query: string;
  expected_output?: Record<string, any>;
  description?: string;
}

export interface TestSuiteResult {
  use_case_id: string;
  total_tests: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_execution_time_ms: number;
  results: TestQueryResult[];
  timestamp: string;
}
