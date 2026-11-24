import { mockDownload, mockRequest } from './mock';
import type { ApiEnvelope } from './types';
import { saveBlob, toQuery } from './utils';

export const API_MODE: 'live' | 'mock' = import.meta.env.VITE_API_MODE === 'mock' ? 'mock' : 'live';
const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '');
const TOKEN_KEY = 'smart-exam.access_token';
const USER_KEY = 'smart-exam.user';

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: ApiEnvelope<unknown>['errors'];
  constructor(message: string, status: number, code?: string, details?: ApiEnvelope<unknown>['errors']) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let accessToken: string | null = localStorage.getItem(TOKEN_KEY);
let refreshPromise: Promise<boolean> | null = null;

export const tokenStore = {
  get: () => accessToken,
  set(token: string) {
    accessToken = token;
    localStorage.setItem(TOKEN_KEY, token);
  },
  setUser(user: unknown) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  getUser<T>() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || 'null') as T;
    } catch {
      return null;
    }
  },
  clear() {
    accessToken = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

function notifyUnauthorized() {
  tokenStore.clear();
  window.dispatchEvent(new CustomEvent('auth:unauthorized'));
}

async function refreshAccess(): Promise<boolean> {
  if (API_MODE === 'mock') return true;
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) return false;
      const envelope = (await response.json()) as ApiEnvelope<{ access_token: string; user: unknown }>;
      tokenStore.set(envelope.data.access_token);
      tokenStore.setUser(envelope.data.user);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, unknown>;
  body?: unknown;
  skipRefresh?: boolean;
}

async function parseEnvelope<T>(response: Response): Promise<ApiEnvelope<T>> {
  const text = await response.text();
  let envelope: ApiEnvelope<T>;
  try {
    envelope = JSON.parse(text) as ApiEnvelope<T>;
  } catch {
    throw new ApiError(response.statusText || 'Unexpected server response', response.status);
  }
  if (!response.ok || envelope.success === false) {
    if (response.status === 401) notifyUnauthorized();
    throw new ApiError(
      envelope.message || 'Request failed',
      response.status,
      envelope.code,
      envelope.errors,
    );
  }
  return envelope;
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<ApiEnvelope<T>> {
  const { params, body, skipRefresh, headers, ...rest } = options;
  if (API_MODE === 'mock') {
    await Promise.resolve();
    return mockRequest<T>(method, path, body, params ?? {}, accessToken);
  }

  const url = `${API_BASE}${path}${params ? toQuery(params) : ''}`;
  const isForm = body instanceof FormData;
  const doFetch = () =>
    fetch(url, {
      ...rest,
      method,
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && !isForm ? { 'Content-Type': 'application/json' } : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...headers,
      },
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });

  let response = await doFetch();
  if (response.status === 401 && !skipRefresh && !path.startsWith('/auth/')) {
    const refreshed = await refreshAccess();
    if (refreshed) response = await doFetch();
  }
  return parseEnvelope<T>(response);
}

async function download(path: string, filename: string, params?: Record<string, unknown>): Promise<void> {
  if (API_MODE === 'mock') {
    saveBlob(mockDownload(), filename);
    return;
  }
  const url = `${API_BASE}${path}${params ? toQuery(params) : ''}`;
  let response = await fetch(url, {
    credentials: 'include',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
  if (response.status === 401) {
    if (await refreshAccess()) {
      response = await fetch(url, {
        credentials: 'include',
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });
    }
  }
  if (!response.ok) {
    let message = 'Download failed';
    try {
      const payload = (await response.json()) as ApiEnvelope<unknown>;
      message = payload.message || message;
    } catch {
      // Binary error response; keep generic message.
    }
    if (response.status === 401) notifyUnauthorized();
    throw new ApiError(message, response.status);
  }
  await saveBlob(await response.blob(), filename);
}

export const api = {
  mode: API_MODE,
  baseUrl: API_BASE,
  get: <T>(path: string, params?: Record<string, unknown>, options?: RequestOptions) =>
    request<T>('GET', path, { ...options, params }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>('POST', path, { ...options, body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>('PATCH', path, { ...options, body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>('PUT', path, { ...options, body }),
  delete: <T>(path: string, options?: RequestOptions) => request<T>('DELETE', path, options),
  download,
  setToken: tokenStore.set,
  setUser: tokenStore.setUser,
  getUser: tokenStore.getUser,
  clearAuth: notifyUnauthorized,
  isAuthenticated: () => Boolean(accessToken),
};
