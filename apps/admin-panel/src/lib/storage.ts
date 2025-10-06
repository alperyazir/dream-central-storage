import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface StorageNode {
  path: string;
  type: 'folder' | 'file';
  size?: number;
  children?: StorageNode[];
}

export type TrashItemType = 'book' | 'app' | 'unknown';

export interface TrashEntry {
  key: string;
  bucket: string;
  path: string;
  item_type: TrashItemType;
  object_count: number;
  total_size: number;
  metadata?: Record<string, string>;
}

export interface RestoreResponse {
  restored_key: string;
  objects_moved: number;
  item_type: TrashItemType;
}

export interface TrashDeleteResponse {
  deleted_key: string;
  objects_removed: number;
  item_type: TrashItemType;
}

export const listAppContents = (
  platform: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<StorageNode> => client.get<StorageNode>(`/storage/apps/${platform}`, {
  headers: buildAuthHeaders(token, tokenType)
});

export const listTrashEntries = (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TrashEntry[]> =>
  client.get<TrashEntry[]>('/storage/trash', {
    headers: buildAuthHeaders(token, tokenType)
  });

export const restoreTrashEntry = (
  key: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<RestoreResponse> =>
  client.post<RestoreResponse, { key: string }>(
    '/storage/restore',
    { key },
    { headers: buildAuthHeaders(token, tokenType) }
  );

export const deleteTrashEntry = (
  key: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<TrashDeleteResponse> =>
  client.delete<TrashDeleteResponse, { key: string }>(
    '/storage/trash',
    { key },
    { headers: buildAuthHeaders(token, tokenType) }
  );
