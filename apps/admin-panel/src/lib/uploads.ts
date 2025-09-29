import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface UploadManifestEntry {
  path: string;
  size: number;
}

export interface BookUploadResponse {
  book_id: number;
  files: UploadManifestEntry[];
}

export interface AppUploadResponse {
  platform: string;
  version: string;
  files: UploadManifestEntry[];
}

const appendArchive = (formData: FormData, file: File) => {
  formData.append('file', file, file.name);
  return formData;
};

export const uploadBookArchive = async (
  bookId: number,
  file: File,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<BookUploadResponse> => {
  const formData = appendArchive(new FormData(), file);
  return client.postForm<BookUploadResponse>(`/books/${bookId}/upload`, formData, {
    headers: buildAuthHeaders(token, tokenType)
  });
};

export const uploadAppArchive = async (
  platform: string,
  file: File,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<AppUploadResponse> => {
  const normalizedPlatform = platform.toLowerCase();
  const formData = appendArchive(new FormData(), file);
  return client.postForm<AppUploadResponse>(`/apps/${normalizedPlatform}/upload`, formData, {
    headers: buildAuthHeaders(token, tokenType)
  });
};
