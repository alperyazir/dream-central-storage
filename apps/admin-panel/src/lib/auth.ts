import { apiClient } from './api';
import { buildAuthHeaders } from './http';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const login = (payload: LoginPayload): Promise<TokenResponse> =>
  apiClient.post<TokenResponse, LoginPayload>('/auth/login', payload);

export interface SessionResponse {
  user_id: number;
  email: string;
  token_type: string;
}

export const validateSession = (
  token: string,
  tokenType: string = 'Bearer'
): Promise<SessionResponse> =>
  apiClient.get<SessionResponse>('/auth/session', {
    headers: buildAuthHeaders(token, tokenType)
  });
