const STORAGE_KEY = 'dcs.auth.session';

export interface PersistedAuthSession {
  token: string;
  tokenType: string;
  savedAt: string;
}

const isStorageAvailable = () => {
  try {
    if (typeof window === 'undefined' || !window.localStorage) {
      return false;
    }
    const testKey = '__dcs_test__';
    window.localStorage.setItem(testKey, '1');
    window.localStorage.removeItem(testKey);
    return true;
  } catch (error) {
    console.warn('Unable to access localStorage for auth persistence', error);
    return false;
  }
};

export const loadPersistedAuth = (): PersistedAuthSession | null => {
  if (!isStorageAvailable()) {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as PersistedAuthSession | null;
    if (!parsed || typeof parsed.token !== 'string' || typeof parsed.tokenType !== 'string') {
      return null;
    }

    return parsed;
  } catch (error) {
    console.warn('Failed to parse persisted auth session', error);
    return null;
  }
};

export const persistAuthSession = (session: PersistedAuthSession) => {
  if (!isStorageAvailable()) {
    return;
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch (error) {
    console.warn('Failed to persist auth session', error);
  }
};

export const clearPersistedAuth = () => {
  if (!isStorageAvailable()) {
    return;
  }

  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.warn('Failed to clear persisted auth session', error);
  }
};
