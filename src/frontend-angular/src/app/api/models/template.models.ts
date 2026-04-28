/**
 * Template Management Models for AI Operations Platform
 *
 * TypeScript interfaces matching the backend Pydantic schemas for
 * template CRUD operations, version control, and approval workflows.
 */

// ============================================================================
// Template Base Models
// ============================================================================

export interface TemplateBase {
  template_id: string;
  prompt_type: string;
  template_content: string;
  variables: string[];
  metadata_json: Record<string, any>;
}

export interface TemplateCreate extends TemplateBase {
  use_case_id?: string;
  deployment_status?: string;
}

export interface TemplateUpdate {
  template_content?: string;
  variables?: string[];
  metadata_json?: Record<string, any>;
  deployment_status?: string;
}

export interface TemplateResponse extends TemplateBase {
  id: string;
  use_case_id?: string;
  version_number: number;
  is_active_version: boolean;
  deployment_status: string;
  created_by_user_id?: string;
  approved_by_user_id?: string;
  approved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TemplateListResponse {
  templates: TemplateResponse[];
  total_count: number;
  page: number;
  page_size: number;
}

// ============================================================================
// Version Control Models
// ============================================================================

export interface TemplateVersionResponse {
  id: string;
  template_id: string;
  version_number: number;
  is_active_version: boolean;
  deployment_status: string;
  created_by_user_id?: string;
  approved_by_user_id?: string;
  approved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TemplateVersionListResponse {
  template_id: string;
  versions: TemplateVersionResponse[];
  total_versions: number;
}

export interface TemplateVersionCreate {
  template_content: string;
  variables: string[];
  metadata_json?: Record<string, any>;
  change_notes?: string;
}

// ============================================================================
// Approval Workflow Models
// ============================================================================

export interface TemplateApprovalRequest {
  approval_notes?: string;
}

export interface TemplateRejectionRequest {
  rejection_reason: string;
}

export interface TemplateActivationRequest {
  version_number: number;
}

// ============================================================================
// Template Comparison/Diff Models
// ============================================================================

export interface TemplateDiffRequest {
  version_1: number;
  version_2: number;
}

export interface TemplateDiffResponse {
  template_id: string;
  version_1: number;
  version_2: number;
  content_diff: string;
  variables_added: string[];
  variables_removed: string[];
  metadata_changes: Record<string, any>;
}

// ============================================================================
// Filter Models
// ============================================================================

export interface TemplateListFilters {
  page?: number;
  page_size?: number;
  template_id_filter?: string;
  deployment_status?: string;
  active_only?: boolean;
}

// ============================================================================
// Deployment Status Enum
// ============================================================================

export enum DeploymentStatus {
  DRAFT = 'draft',
  PENDING = 'pending',
  APPROVED = 'approved',
  DEPLOYED = 'deployed',
}
