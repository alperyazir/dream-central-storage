import { ApiClient, apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface ApiKeyCreate {
  name: string;
  description?: string;
  expires_at?: string | null;
  rate_limit?: number;
}

export interface ApiKeyCreated {
  id: number;
  key: string;
  name: string;
  created_at: string;
  expires_at: string | null;
  is_active: boolean;
}

export interface ApiKeyRead {
  id: number;
  key_prefix: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  rate_limit: number;
}

export interface ApiKeyListResponse {
  api_keys: ApiKeyRead[];
}

export const listApiKeys = (
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<ApiKeyListResponse> =>
  client.get<ApiKeyListResponse>('/api-keys/', {
    headers: buildAuthHeaders(token, tokenType),
  });

export const createApiKey = (
  data: ApiKeyCreate,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<ApiKeyCreated> =>
  client.post<ApiKeyCreated, ApiKeyCreate>('/api-keys/', data, {
    headers: buildAuthHeaders(token, tokenType),
  });

export const revokeApiKey = (
  keyId: number,
  token: string,
  tokenType: string = 'Bearer',
  client: ApiClient = apiClient
): Promise<{ status: string; id: number }> =>
  client.delete<{ status: string; id: number }>(
    `/api-keys/${keyId}`,
    undefined,
    {
      headers: buildAuthHeaders(token, tokenType),
    }
  );
