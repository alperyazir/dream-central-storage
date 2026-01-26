import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface TemplateInfo {
  platform: string;
  file_name: string;
  file_size: number;
  uploaded_at: string;
  download_url: string;
}

export interface TemplateListResponse {
  templates: TemplateInfo[];
}

export interface TemplateUploadResponse {
  platform: string;
  file_name: string;
  file_size: number;
  message: string;
}

export interface BundleRequest {
  platform: 'mac' | 'win' | 'win7-8' | 'linux';
  book_id: number;
  force?: boolean;
}

export interface BundleResponse {
  download_url: string;
  file_name: string;
  file_size: number;
  expires_at: string;
}

export interface AsyncBundleRequest {
  platform: 'mac' | 'win' | 'win7-8' | 'linux';
  book_id: number;
  force?: boolean;
}

export interface AsyncBundleResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface BundleJobResult {
  job_id: string;
  status: string;
  progress: number;
  current_step: string;
  download_url: string | null;
  file_name: string | null;
  file_size: number | null;
  cached: boolean;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface BundleInfo {
  publisher_name: string;
  book_name: string;
  platform: string;
  file_name: string;
  file_size: number;
  created_at: string;
  object_name: string;
  download_url: string | null;
}

export interface BundleListResponse {
  bundles: BundleInfo[];
}

export interface TemplateDownloadResponse {
  download_url: string;
  platform: string;
  expires_at: string;
}

/**
 * List all uploaded standalone app templates
 */
export const listTemplates = (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TemplateListResponse> =>
  client.get<TemplateListResponse>('/standalone-apps', {
    headers: buildAuthHeaders(token, tokenType)
  });

/**
 * Upload a standalone app template for a specific platform
 */
export const uploadTemplate = async (
  platform: string,
  file: File,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TemplateUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  return client.postForm<TemplateUploadResponse>(
    `/standalone-apps/${platform}/upload`,
    formData,
    { headers: buildAuthHeaders(token, tokenType) }
  );
};

/**
 * Delete a standalone app template for a specific platform
 */
export const deleteTemplate = (
  platform: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<void> =>
  client.delete<void>(`/standalone-apps/${platform}`, undefined, {
    headers: buildAuthHeaders(token, tokenType)
  });

/**
 * Get download URL for a standalone app template
 */
export const getTemplateDownloadUrl = (
  platform: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TemplateDownloadResponse> =>
  client.get<TemplateDownloadResponse>(`/standalone-apps/${platform}/download`, {
    headers: buildAuthHeaders(token, tokenType)
  });

/**
 * Create a bundled standalone app with book assets
 */
export const createBundle = (
  request: BundleRequest,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<BundleResponse> =>
  client.post<BundleResponse, BundleRequest>('/standalone-apps/bundle', request, {
    headers: buildAuthHeaders(token, tokenType)
  });

/**
 * List all created bundles
 */
export const listBundles = (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<BundleListResponse> =>
  client.get<BundleListResponse>('/standalone-apps/bundles', {
    headers: buildAuthHeaders(token, tokenType)
  });

/**
 * Delete a bundle by its object path
 */
export const deleteBundle = (
  objectName: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<void> =>
  client.delete<void>(`/standalone-apps/bundles/${objectName}`, undefined, {
    headers: buildAuthHeaders(token, tokenType)
  });

/**
 * Create a bundle asynchronously (returns job ID for polling)
 */
export const createBundleAsync = (
  request: AsyncBundleRequest,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<AsyncBundleResponse> =>
  client.post<AsyncBundleResponse, AsyncBundleRequest>('/standalone-apps/bundle/async', request, {
    headers: buildAuthHeaders(token, tokenType)
  });

/**
 * Get the status/result of an async bundle creation job
 */
export const getBundleJobStatus = (
  jobId: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<BundleJobResult> =>
  client.get<BundleJobResult>(`/standalone-apps/bundle/jobs/${jobId}`, {
    headers: buildAuthHeaders(token, tokenType)
  });

/**
 * Supported platforms for standalone apps
 */
export const STANDALONE_PLATFORMS = ['mac', 'win', 'win7-8', 'linux'] as const;
export type StandalonePlatform = typeof STANDALONE_PLATFORMS[number];

/**
 * Human-readable platform labels
 */
export const PLATFORM_LABELS: Record<StandalonePlatform, string> = {
  mac: 'macOS',
  win: 'Windows',
  'win7-8': 'Windows 7/8',
  linux: 'Linux'
};
