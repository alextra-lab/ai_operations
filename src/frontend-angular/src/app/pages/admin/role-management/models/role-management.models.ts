/**
 * TypeScript models for role management operations.
 *
 * These models match the backend Pydantic schemas for RBAC V2
 * per ADR-060 (two-tier RBAC with grouping roles and teams).
 */

export interface RoleUseCaseAssignment {
  id: string;
  role_name: string;
  use_case_id: string;
  use_case_name: string;
  granted_by?: string;
  granted_at: string;
  expires_at?: string;
  is_active: boolean;
  metadata: Record<string, any>;
}

export interface RoleUseCaseListResponse {
  role_name: string;
  total: number;
  active: number;
  assignments: RoleUseCaseAssignment[];
}

export interface RoleUseCaseAssignRequest {
  use_case_id: string;
  expires_at?: string;
  metadata?: Record<string, any>;
}

export interface RoleInfo {
  role_name: string;
  display_name: string;
  description: string;
  is_system_role: boolean;
  use_case_count?: number;
}

export interface UseCaseListItem {
  id: string;
  use_case_id: string;
  name: string;
  category?: string;
  intent_type?: string;
  lifecycle_state: string;
}

export interface RoleFilters {
  search?: string;
  include_system?: boolean;
  include_custom?: boolean;
}

/**
 * Predefined system roles (Tier 1).
 */
export const SYSTEM_ROLES: RoleInfo[] = [
  {
    role_name: 'admin',
    display_name: 'Administrator',
    description: 'Full system access - superuser',
    is_system_role: true,
  },
  {
    role_name: 'corpus_admin',
    display_name: 'Corpus Administrator',
    description: 'Document and collection management - sees all documents',
    is_system_role: true,
  },
  {
    role_name: 'developer',
    display_name: 'Developer',
    description:
      'Team-scoped use case development - can create/edit use cases for assigned teams',
    is_system_role: true,
  },
  {
    role_name: 'use_case_admin',
    display_name: 'Use Case Administrator',
    description: 'Use case super admin - sees all use cases across all teams',
    is_system_role: true,
  },
  {
    role_name: 'tools_admin',
    display_name: 'Tools Administrator',
    description: 'Tool and MCP management',
    is_system_role: true,
  },
  {
    role_name: 'role_admin',
    display_name: 'Role Administrator',
    description: 'Create roles and assign users to roles',
    is_system_role: true,
  },
  {
    role_name: 'use_case_publisher',
    display_name: 'Use Case Publisher',
    description: 'Review, approve, and publish use cases',
    is_system_role: true,
  },
  {
    role_name: 'conversations_privileged',
    display_name: 'Conversations Privileged',
    description: 'Privileged access to multi-turn conversation interface',
    is_system_role: true,
  },
  {
    role_name: 'user',
    display_name: 'User',
    description:
      'Standard end-user - requires grouping roles for use case access',
    is_system_role: true,
  },
  {
    role_name: 'service',
    display_name: 'Service Account',
    description: 'API automation and service-to-service authentication',
    is_system_role: true,
  },
];

/**
 * Use case grouping role (Tier 2) - Dynamic, admin-created.
 */
export interface GroupingRoleInfo {
  role_name: string;
  display_name?: string;
  description?: string;
  user_count: number;
  use_case_count: number;
  collection_count: number;
}

/**
 * Developer team (Tier 3) - Isolation boundaries.
 */
export interface DeveloperTeamInfo {
  team_id: string;
  display_name: string;
  description?: string;
  member_count: number;
  draft_count: number;
  published_count: number;
}
