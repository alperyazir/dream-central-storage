import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export type ProcessingJobType = 'full' | 'text_only' | 'vocabulary_only' | 'audio_only';
export type ProcessingStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'partial' | 'cancelled';
export type JobPriority = 'high' | 'normal' | 'low';

export interface ProcessingTriggerRequest {
  job_type?: ProcessingJobType;
  priority?: JobPriority;
  admin_override?: boolean;
}

export interface ProcessingJobResponse {
  job_id: string;
  book_id: string;
  publisher_id: string;
  job_type: ProcessingJobType;
  status: ProcessingStatus;
  priority: JobPriority;
  progress: number;
  current_step: string;
  error_message?: string | null;
  retry_count: number;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ProcessingStatusResponse {
  job_id: string;
  book_id: string;
  status: ProcessingStatus;
  progress: number;
  current_step: string;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface CleanupStatsResponse {
  total_deleted: number;
  text_deleted: number;
  modules_deleted: number;
  audio_deleted: number;
  vocabulary_deleted: number;
  metadata_deleted: number;
  errors: string[];
}

/**
 * Trigger AI processing for a book.
 */
export const triggerProcessing = (
  bookId: number,
  token: string,
  tokenType: string = 'Bearer',
  options: ProcessingTriggerRequest = {},
  client: ApiClient = apiClient
): Promise<ProcessingJobResponse> =>
  client.post<ProcessingJobResponse, ProcessingTriggerRequest>(
    `/books/${bookId}/process-ai`,
    options,
    { headers: buildAuthHeaders(token, tokenType) }
  );

/**
 * Get processing status for a book.
 */
export const getProcessingStatus = (
  bookId: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<ProcessingStatusResponse> =>
  client.get<ProcessingStatusResponse>(
    `/books/${bookId}/process-ai/status`,
    { headers: buildAuthHeaders(token, tokenType) }
  );

/**
 * Delete AI data for a book, optionally triggering reprocessing.
 */
export const deleteAIData = (
  bookId: number,
  token: string,
  tokenType: string = 'Bearer',
  reprocess: boolean = false,
  client: ApiClient = apiClient
): Promise<CleanupStatsResponse> =>
  client.delete<CleanupStatsResponse>(
    `/books/${bookId}/ai-data?reprocess=${reprocess}`,
    undefined,
    { headers: buildAuthHeaders(token, tokenType) }
  );

/**
 * Get status color for display.
 */
export const getStatusColor = (status: ProcessingStatus): 'default' | 'primary' | 'secondary' | 'success' | 'error' | 'info' | 'warning' => {
  switch (status) {
    case 'queued':
      return 'info';
    case 'processing':
      return 'primary';
    case 'completed':
      return 'success';
    case 'failed':
      return 'error';
    case 'partial':
      return 'warning';
    case 'cancelled':
      return 'default';
    default:
      return 'default';
  }
};

/**
 * Get human-readable status label.
 */
export const getStatusLabel = (status: ProcessingStatus): string => {
  switch (status) {
    case 'queued':
      return 'Queued';
    case 'processing':
      return 'Processing';
    case 'completed':
      return 'Completed';
    case 'failed':
      return 'Failed';
    case 'partial':
      return 'Partial';
    case 'cancelled':
      return 'Cancelled';
    default:
      return status;
  }
};
