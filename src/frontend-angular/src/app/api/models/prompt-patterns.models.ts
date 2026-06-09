/**
 * TypeScript models for Prompt Pattern Library
 * These models match the backend Pydantic schemas for pattern management
 */

export interface PatternVariable {
  name: string;
  description: string;
  default?: string;
}

export interface FewShotExample {
  user: string;
  assistant: string;
}

export interface PromptPattern {
  id: string;
  pattern_id: string;
  name: string;
  category: string;
  description: string;
  system_prompt_template?: string;
  developer_prompt_template?: string;
  fewshots_template: FewShotExample[];
  variables: PatternVariable[];
  source_url?: string;
  tags: string[];
  use_count: number;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface PromptPatternListResponse {
  patterns: PromptPattern[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApplyPatternRequest {
  pattern_id: string;
  variables: Record<string, string>;
}

export interface ApplyPatternResponse {
  system_prompt?: string;
  developer_prompt?: string;
  fewshots: FewShotExample[];
  pattern_used: string;
  variables_applied: Record<string, string>;
}

/**
 * Pattern category display metadata
 */
export interface CategoryInfo {
  id: string;
  label: string;
  icon: string;
  description: string;
  color: string;
}

export const PATTERN_CATEGORIES: CategoryInfo[] = [
  {
    id: 'reasoning',
    label: 'Reasoning',
    icon: 'brain-circuit',
    description: 'Step-by-step analytical thinking patterns',
    color: '#4CAF50',
  },
  {
    id: 'rag',
    label: 'RAG',
    icon: 'file-text',
    description: 'Retrieval-augmented generation patterns',
    color: '#2196F3',
  },
  {
    id: 'learning',
    label: 'Learning',
    icon: 'graduation-cap',
    description: 'Few-shot and example-based learning',
    color: '#9C27B0',
  },
  {
    id: 'tools',
    label: 'Tools',
    icon: 'wrench',
    description: 'Tool use and agent patterns',
    color: '#FF9800',
  },
  {
    id: 'json',
    label: 'JSON',
    icon: 'braces',
    description: 'Structured output generation',
    color: '#00BCD4',
  },
  {
    id: 'role',
    label: 'Role',
    icon: 'user',
    description: 'Expert persona and role-based prompting',
    color: '#E91E63',
  },
  {
    id: 'soc',
    label: 'SOC',
    icon: 'shield',
    description: 'Security operations patterns',
    color: '#F44336',
  },
  {
    id: 'safety',
    label: 'Safety',
    icon: 'shield',
    description: 'Input validation and security',
    color: '#795548',
  },
  {
    id: 'workflow',
    label: 'Workflow',
    icon: 'workflow',
    description: 'Multi-step process patterns',
    color: '#607D8B',
  },
  {
    id: 'context',
    label: 'Context',
    icon: 'file-text',
    description: 'Context management and compression',
    color: '#3F51B5',
  },
  {
    id: 'evaluation',
    label: 'Evaluation',
    icon: 'list-checks',
    description: 'Quality assessment and scoring',
    color: '#009688',
  },
  {
    id: 'classification',
    label: 'Classification',
    icon: 'tag',
    description: 'Categorization and tagging',
    color: '#CDDC39',
  },
];
