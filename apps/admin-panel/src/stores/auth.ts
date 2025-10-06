import { create } from 'zustand';

import { login as requestLogin, LoginPayload, TokenResponse, validateSession } from '../lib/auth';
import { ApiError } from '../lib/api';
import {
  clearPersistedAuth,
  loadPersistedAuth,
  persistAuthSession
} from '../lib/auth-storage';

const baseAuthState = {
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
  isHydrating: boolean;
  isHydrated: boolean;
  error: string | null;
  login: (payload: LoginPayload) => Promise<TokenResponse>;
  logout: () => void;
  clearError: () => void;
  hydrate: () => Promise<void>;
}

const buildPersistedPayload = (response: TokenResponse) => ({
  token: response.access_token,
  tokenType: response.token_type ?? 'bearer',
  savedAt: new Date().toISOString()
});

export const useAuthStore = create<AuthState>((set, get) => ({
  ...baseAuthState,
  isHydrating: false,
  isHydrated: false,
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

      persistAuthSession(buildPersistedPayload(response));

      set({
        token: response.access_token,
        tokenType: response.token_type,
        isAuthenticated: true,
        isAuthenticating: false,
        isHydrated: true,
        error: null
      });

      return response;
    } catch (error) {
      set({
        ...baseAuthState,
        isHydrating: false,
        isHydrated: true,
        error: deriveErrorMessage(error)
      });

      throw error;
    }
  },
  logout: () => {
    clearPersistedAuth();
    set({ ...baseAuthState, isHydrated: true, isHydrating: false });
  },
  clearError: () => set({ error: null }),
  hydrate: async () => {
    if (get().isHydrated || get().isHydrating) {
      return;
    }

    if (typeof window === 'undefined') {
      set({ ...baseAuthState, isHydrated: true, isHydrating: false });
      return;
    }

    const persisted = loadPersistedAuth();
    if (!persisted) {
      set({ ...baseAuthState, isHydrated: true, isHydrating: false });
      return;
    }

    set({ isHydrating: true, error: null });

    try {
      await validateSession(persisted.token, persisted.tokenType);
      set({
        token: persisted.token,
        tokenType: persisted.tokenType,
        isAuthenticated: true,
        isAuthenticating: false,
        isHydrating: false,
        isHydrated: true,
        error: null
      });
    } catch (error) {
      console.warn('Persisted session validation failed', error);
      clearPersistedAuth();
      set({ ...baseAuthState, isHydrating: false, isHydrated: true });
    }
  }
}));

export const resetAuthStore = () => {
  clearPersistedAuth();
  useAuthStore.setState({ ...baseAuthState, isHydrated: true, isHydrating: false });
};
