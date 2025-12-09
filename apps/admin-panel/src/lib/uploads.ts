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
}

const appendOverrideParam = (path: string, override?: boolean) =>
  override ? `${path}${path.includes('?') ? '&' : '?'}override=true` : path;

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
  return client.postForm<BookUploadResponse>(appendOverrideParam(`/books/${bookId}/upload`, options.override), formData, {
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
  return client.postForm<NewBookUploadResponse>(appendOverrideParam('/books/upload', options.override), formData, {
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
  return client.postForm<AppUploadResponse>(appendOverrideParam(`/apps/${normalizedPlatform}/upload`, options.override), formData, {
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
    appendOverrideParam('/books/upload-bulk', options.override),
    formData,
    {
      headers: buildAuthHeaders(token, tokenType)
    }
  );
};
