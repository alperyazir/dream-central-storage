import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface AppDeleteRequest {
  path: string;
}

export const softDeleteAppBuild = (
  platform: string,
  path: string,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<void> =>
  client.delete<void, AppDeleteRequest>(`/apps/${platform}`, { path }, {
    headers: buildAuthHeaders(token, tokenType)
  });
