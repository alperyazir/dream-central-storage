import { create } from 'zustand';

import { login as requestLogin, LoginPayload, TokenResponse } from '../lib/auth';
import { ApiError } from '../lib/api';

const baseData = {
  token: null as string | null,
  tokenType: null as string | null,
  isAuthenticated: false,
  isAuthenticating: false,
  error: null as string | null
};

const deriveErrorMessage = (error: unknown) => {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | null)?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (typeof error.body === 'string' && error.body.trim()) {
      const message = error.body.trim();
      if (/invalid credentials/i.test(message)) {
        return 'Invalid email or password.';
      }
      return message;
    }
  }

  if (error instanceof Error) {
    if (/invalid credentials/i.test(error.message)) {
      return 'Invalid email or password.';
    }

    return error.message;
  }

  return 'Unable to sign in right now. Please try again.';
};

export interface AuthState {
  token: string | null;
  tokenType: string | null;
  isAuthenticated: boolean;
  isAuthenticating: boolean;
  error: string | null;
  login: (payload: LoginPayload) => Promise<TokenResponse>;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  ...baseData,
  login: async (payload) => {
    set({ isAuthenticating: true, error: null });

    try {
      const { access_token, token_type } = await requestLogin({
        email: payload.email.trim().toLowerCase(),
        password: payload.password
      });

      const response: TokenResponse = {
        access_token,
        token_type: token_type ?? 'bearer'
      };

      set({
        token: response.access_token,
        tokenType: response.token_type,
        isAuthenticated: true,
        isAuthenticating: false,
        error: null
      });

      return response;
    } catch (error) {
      set({
        ...baseData,
        error: deriveErrorMessage(error)
      });

      throw error;
    }
  },
  logout: () => set({ ...baseData }),
  clearError: () => set({ error: null })
}));

export const resetAuthStore = () => {
  useAuthStore.setState({ ...baseData });
};
