import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';
import { buildApiUrl } from '../config/environment';

// ---------------------------------------------------------------------------
// Types (matching backend schemas in ai_content.py)
// ---------------------------------------------------------------------------

export interface ManifestRead {
  content_id: string;
  activity_type: string;
  title: string;
  item_count: number;
  has_audio: boolean;
  has_passage: boolean;
  difficulty: string | null;
  language: string;
  created_by: string | null;
  created_at: string | null;
}

export interface AIContentRead {
  content_id: string;
  manifest: Omit<ManifestRead, 'content_id'>;
  content: Record<string, unknown>;
}

export interface AudioUploadResponse {
  filename: string;
  storage_path: string;
  size: number;
}

export interface BatchAudioResponse {
  uploaded: AudioUploadResponse[];
  failed: string[];
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * List all AI content manifests for a book.
 */
export const listAIContent = (
  bookId: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<ManifestRead[]> =>
  client.get<ManifestRead[]>(`/books/${bookId}/ai-content/`, {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Get full AI content (manifest + content.json) for a specific content_id.
 */
export const getAIContent = (
  bookId: number,
  contentId: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<AIContentRead> =>
  client.get<AIContentRead>(`/books/${bookId}/ai-content/${contentId}`, {
    headers: buildAuthHeaders(token, tokenType),
  });

/**
 * Hard-delete an AI content generation (manifest, content, audio).
 */
export const deleteAIContent = (
  bookId: number,
  contentId: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<{ content_id: string; objects_removed: number }> =>
  client.delete<{ content_id: string; objects_removed: number }>(
    `/books/${bookId}/ai-content/${contentId}`,
    undefined,
    { headers: buildAuthHeaders(token, tokenType) }
  );

/**
 * Build a full URL for streaming an audio file (uses auth header at fetch time).
 */
export const getAIContentAudioUrl = (
  bookId: number,
  contentId: string,
  filename: string
): string =>
  buildApiUrl(`/books/${bookId}/ai-content/${contentId}/audio/${encodeURIComponent(filename)}`);
