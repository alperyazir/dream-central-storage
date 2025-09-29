import { appConfig, buildApiUrl, ensureLeadingSlash } from '../config/environment';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface RequestOptions extends RequestInit {
  method?: HttpMethod;
}

export interface ApiClient {
  request: <T = unknown>(path: string, init?: RequestOptions) => Promise<T>;
  get: <T = unknown>(path: string, init?: RequestOptions) => Promise<T>;
  post: <T = unknown, TBody = unknown>(path: string, body?: TBody, init?: RequestOptions) => Promise<T>;
  postForm: <T = unknown>(path: string, formData: FormData, init?: RequestOptions) => Promise<T>;
}

const parseResponse = async <T>(response: Response): Promise<T> => {
  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  const contentLength = response.headers.get('content-length');
  if (contentLength === '0') {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    return (await response.json()) as T;
  }

  const text = await response.text();
  return text as unknown as T;
};

const resolveUrl = (baseUrl: string, path: string) => `${baseUrl}${ensureLeadingSlash(path)}`;

export const createApiClient = (baseUrl: string = appConfig.apiBaseUrl): ApiClient => {
  const request = async <T>(path: string, init: RequestOptions = {}) => {
    const response = await fetch(resolveUrl(baseUrl, path), init);

    if (!response.ok) {
      const details = await response.text();
      const message = details ? `${response.status}: ${details}` : `${response.status}: ${response.statusText}`;
      throw new Error(`Request failed (${message})`);
    }

    return parseResponse<T>(response);
  };

  const get = <T>(path: string, init?: RequestOptions) => request<T>(path, { ...init, method: 'GET' });

  const post = <T, TBody = unknown>(path: string, body?: TBody, init?: RequestOptions) => {
    const headers = new Headers(init?.headers ?? {});

    if (body !== undefined && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    return request<T>(path, {
      ...init,
      method: 'POST',
      headers,
      body: body !== undefined ? JSON.stringify(body) : init?.body
    });
  };

  const postForm = <T>(path: string, formData: FormData, init?: RequestOptions) =>
    request<T>(path, {
      ...init,
      method: 'POST',
      body: formData
    });

  return {
    request,
    get,
    post,
    postForm
  };
};

export const apiClient = createApiClient();

export const resolveApiUrl = (path: string) => buildApiUrl(path);

export const apiBaseUrl = appConfig.apiBaseUrl;
