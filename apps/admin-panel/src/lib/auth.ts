import { apiClient } from './api';

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
