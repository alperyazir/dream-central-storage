export interface AppConfig {
  apiBaseUrl: string;
}

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

const normalizeBaseUrl = (value: string) => {
  const normalized = value.trim().replace(/\/+$/, '');
  return normalized.length > 0 ? normalized : DEFAULT_API_BASE_URL;
};

const resolvedBaseUrl = (() => {
  const fromEnv = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  return normalizeBaseUrl(fromEnv);
})();

export const appConfig: AppConfig = Object.freeze({
  apiBaseUrl: resolvedBaseUrl
});

export const ensureLeadingSlash = (path: string) => (path.startsWith('/') ? path : `/${path}`);

export const buildApiUrl = (path: string) => `${appConfig.apiBaseUrl}${ensureLeadingSlash(path)}`;
