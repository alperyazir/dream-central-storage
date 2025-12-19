import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';
import type { BookRecord } from './books';

export interface UploadManifestEntry {
  path: string;
  size: number;
}

export interface BookUploadResponse {
  book_id: number;
  files: UploadManifestEntry[];
  version: string;
}

export interface NewBookUploadResponse {
  book: BookRecord;
  files: UploadManifestEntry[];
  version: string;
}

export interface AppUploadResponse {
  platform: string;
  version: string;
  files: UploadManifestEntry[];
}

interface UploadOptions {
  override?: boolean;
  publisherId?: number;
}

const appendQueryParams = (path: string, options: UploadOptions = {}): string => {
  const params: string[] = [];
  if (options.override) {
    params.push('override=true');
  }
  if (options.publisherId !== undefined) {
    params.push(`publisher_id=${options.publisherId}`);
  }
  if (params.length === 0) return path;
  const separator = path.includes('?') ? '&' : '?';
  return `${path}${separator}${params.join('&')}`;
};

const appendArchive = (formData: FormData, file: File) => {
  formData.append('file', file, file.name);
  return formData;
};

export const uploadBookArchive = async (
  bookId: number,
  file: File,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient,
  options: UploadOptions = {}
): Promise<BookUploadResponse> => {
  const formData = appendArchive(new FormData(), file);
  return client.postForm<BookUploadResponse>(appendQueryParams(`/books/${bookId}/upload`, options), formData, {
    headers: buildAuthHeaders(token, tokenType)
  });
};

export const uploadNewBookArchive = async (
  file: File,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient,
  options: UploadOptions = {}
): Promise<NewBookUploadResponse> => {
  const formData = appendArchive(new FormData(), file);
  return client.postForm<NewBookUploadResponse>(appendQueryParams('/books/upload', options), formData, {
    headers: buildAuthHeaders(token, tokenType)
  });
};

export const uploadAppArchive = async (
  platform: string,
  file: File,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient,
  options: UploadOptions = {}
): Promise<AppUploadResponse> => {
  const normalizedPlatform = platform.toLowerCase();
  const formData = appendArchive(new FormData(), file);
  return client.postForm<AppUploadResponse>(appendQueryParams(`/apps/${normalizedPlatform}/upload`, options), formData, {
    headers: buildAuthHeaders(token, tokenType)
  });
};

export interface BulkUploadResult {
  filename: string;
  success: boolean;
  book_id: number | null;
  book_name: string | null;
  publisher: string | null;
  error: string | null;
}

export interface BulkUploadResponse {
  total: number;
  successful: number;
  failed: number;
  results: BulkUploadResult[];
}

export const uploadBulkBookArchives = async (
  files: File[],
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient,
  options: UploadOptions = {}
): Promise<BulkUploadResponse> => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file, file.name);
  });
  return client.postForm<BulkUploadResponse>(
    appendQueryParams('/books/upload-bulk', options),
    formData,
    {
      headers: buildAuthHeaders(token, tokenType)
    }
  );
};
