/**
 * Tool Testing Models
 *
 * T6-F4: TypeScript interfaces for the tool testing UI.
 */

import { TestExecutionResult } from '../../../../api/services/tool-testing.service';

/**
 * Tool info for selection dropdown
 */
export interface ToolOption {
  id: string;
  tool_id: string;
  name: string;
  description: string | null;
  category: string;
  is_enabled: boolean;
  is_healthy: boolean;
  parameters_schema?: Record<string, unknown>;
}

/**
 * Test history entry stored in session
 */
export interface TestHistoryEntry {
  id: string;
  tool_id: string;
  tool_name: string;
  tool_display_name: string;
  parameters: Record<string, unknown>;
  result: TestExecutionResult;
  timestamp: Date;
}

/**
 * Validation status for the parameter editor
 */
export type JsonValidationStatus = 'valid' | 'invalid' | 'empty';

/**
 * Example parameters for common tool types
 */
export const EXAMPLE_PARAMETERS: Record<string, Record<string, unknown>> = {
  search: {
    query: 'example search query',
    limit: 10,
  },
  default: {
    param1: 'value1',
    param2: 123,
  },
};

/**
 * Generate a UUID for test history entries
 */
export function generateTestId(): string {
  return crypto.randomUUID();
}

/**
 * Format duration for display
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms.toFixed(1)}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Format timestamp for display
 */
export function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
