/**
 * Validation report models for Use Case validation.
 */

export type ValidationSeverity = 'error' | 'warning' | 'info';

export interface ValidationIssue {
  rule_id: string;
  severity: ValidationSeverity;
  message: string;
  field?: string;
  suggestion?: string;
  auto_fix?: Record<string, any>;
}

export interface ValidationReport {
  use_case_id: string;
  is_valid: boolean;
  can_publish: boolean;
  issues: ValidationIssue[];
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  infos: ValidationIssue[];
  validated_at: string;
}
