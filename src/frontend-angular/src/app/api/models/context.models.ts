/**
 * TypeScript models for conversation thread management.
 *
 * These models match the backend thread management schemas for
 * multi-turn conversations with DiscussionID support.
 */

export interface ContextThread {
  id: string;
  thread_id: string;
  title?: string;
  description?: string;
  user_id: string;
  center_id?: string;
  discussion_id?: string;
  use_case_id?: string;
  use_case_name?: string;
  source: string;
  is_active: boolean;
  message_count: number;
  context_size_tokens: number;
  max_context_tokens: number;
  first_query_id?: string;
  last_query_id?: string;
  created_at: string;
  updated_at: string;
  last_activity_at: string;
  archived_at?: string;
  metadata_json: Record<string, unknown>;
}

export interface ThreadMessage {
  id: string;
  thread_id: string;
  query_id?: string;
  sequence_number: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  token_count: number;
  model_used?: string;
  is_summary: boolean;
  original_message_count?: number;
  created_at: string;
}

export interface ThreadCreate {
  title?: string;
  description?: string;
  discussion_id?: string;
  use_case_id?: string;
  use_case_name?: string;
  source?: string;
  center_id?: string;
  metadata?: Record<string, unknown>;
}

export interface ThreadUpdate {
  title?: string;
  description?: string;
  is_active?: boolean;
  discussion_id?: string;
  metadata?: Record<string, unknown>;
}

export interface ThreadListResponse {
  items: ContextThread[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface SendMessageRequest {
  query: string;
  thread_id: string;
  use_case_id?: string;
  discussion_id?: string;
}
