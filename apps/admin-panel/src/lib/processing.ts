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

// Extended status type that includes 'not_started'
export type ExtendedProcessingStatus = ProcessingStatus | 'not_started';

export interface BookWithProcessingStatus {
  book_id: number;
  book_name: string;
  book_title: string;
  publisher_id: number;
  publisher_name: string;
  processing_status: ExtendedProcessingStatus;
  progress: number;
  current_step: string | null;
  error_message: string | null;
  job_id: string | null;
  last_processed_at: string | null;
}

export interface BooksWithProcessingStatusResponse {
  books: BookWithProcessingStatus[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProcessingQueueItem {
  job_id: string;
  book_id: number;
  book_name: string;
  book_title: string;
  publisher_name: string;
  status: ProcessingStatus;
  progress: number;
  current_step: string;
  position: number;
  created_at: string;
  started_at: string | null;
}

export interface ProcessingQueueResponse {
  queue: ProcessingQueueItem[];
  total_queued: number;
  total_processing: number;
}

export interface BulkReprocessRequest {
  book_ids: number[];
  job_type?: ProcessingJobType;
  priority?: JobPriority;
}

export interface BulkReprocessResponse {
  triggered: number;
  skipped: number;
  errors: string[];
  job_ids: string[];
}

/**
 * Get list of books with their processing status.
 */
export const getBooksWithProcessingStatus = (
  token: string,
  tokenType: string = 'Bearer',
  params: {
    status?: ExtendedProcessingStatus;
    publisher?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {},
  client: ApiClient = apiClient
): Promise<BooksWithProcessingStatusResponse> => {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.set('status', params.status);
  if (params.publisher) searchParams.set('publisher', params.publisher);
  if (params.search) searchParams.set('search', params.search);
  if (params.page !== undefined) searchParams.set('page', params.page.toString());
  if (params.page_size !== undefined) searchParams.set('page_size', params.page_size.toString());

  const queryString = searchParams.toString();
  const url = `/processing/books${queryString ? `?${queryString}` : ''}`;

  return client.get<BooksWithProcessingStatusResponse>(url, {
    headers: buildAuthHeaders(token, tokenType),
  });
};

/**
 * Get current processing queue.
 */
export const getProcessingQueue = (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<ProcessingQueueResponse> =>
  client.get<ProcessingQueueResponse>('/processing/queue', {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Clear processing error for a book (reset to not_started).
 */
export const clearProcessingError = (
  bookId: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<{ message: string }> =>
  client.post<{ message: string }, undefined>(
    `/processing/books/${bookId}/clear-error`,
    undefined,
    { headers: buildAuthHeaders(token, tokenType) }
  );

/**
 * Bulk reprocess multiple books.
 */
export const bulkReprocess = (
  request: BulkReprocessRequest,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<BulkReprocessResponse> =>
  client.post<BulkReprocessResponse, BulkReprocessRequest>(
    '/processing/bulk-reprocess',
    request,
    { headers: buildAuthHeaders(token, tokenType) }
  );

/**
 * Get status color for extended status (including not_started).
 */
export const getExtendedStatusColor = (
  status: ExtendedProcessingStatus
): 'default' | 'primary' | 'secondary' | 'success' | 'error' | 'info' | 'warning' => {
  if (status === 'not_started') return 'default';
  return getStatusColor(status as ProcessingStatus);
};

/**
 * Get human-readable label for extended status.
 */
export const getExtendedStatusLabel = (status: ExtendedProcessingStatus): string => {
  if (status === 'not_started') return 'Not Started';
  return getStatusLabel(status as ProcessingStatus);
};
