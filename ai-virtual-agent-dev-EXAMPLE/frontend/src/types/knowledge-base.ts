export interface KnowledgeBase {
  vector_store_name: string; // Primary key - LlamaStack identifier
  name: string;
  version: string;
  embedding_model: string;
  provider_id?: string;
  is_external: boolean;
  source?: string;
  source_configuration?: Record<string, unknown>;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export type KnowledgeBaseStatus = 'succeeded' | 'running' | 'failed' | 'unknown';

export interface KnowledgeBaseWithStatus extends KnowledgeBase {
  status: KnowledgeBaseStatus;
}

// Status utility functions
export function getStatusColor(status: KnowledgeBaseStatus): 'green' | 'orange' | 'red' {
  switch (status) {
    case 'succeeded':
      return 'green';
    case 'running':
      return 'orange';
    case 'failed':
    case 'unknown':
      return 'red';
    default:
      return 'orange';
  }
}

export function getStatusLabel(status: KnowledgeBaseStatus): string {
  switch (status) {
    case 'succeeded':
      return 'Succeeded';
    case 'running':
      return 'Running';
    case 'failed':
      return 'Failed';
    default:
      return 'Unknown';
  }
}
