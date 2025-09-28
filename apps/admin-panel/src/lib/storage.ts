import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface StorageNode {
  path: string;
  type: 'folder' | 'file';
  size?: number;
  children?: StorageNode[];
}

export const listAppContents = (
  platform: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<StorageNode> => client.get<StorageNode>(`/storage/apps/${platform}`, {
  headers: buildAuthHeaders(token, tokenType)
});
