import { useMutation, useQuery, type UseMutationOptions, type UseQueryOptions } from '@tanstack/react-query';
import { api, ApiError } from './api';
import type { ApiEnvelope } from './types';

export function useApiQuery<T>(
  key: string,
  path: string,
  params?: Record<string, unknown>,
  options?: Omit<UseQueryOptions<T, ApiError, T>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<T, ApiError, T>({
    queryKey: [key, path, params ?? {}],
    queryFn: async () => (await api.get<T>(path, params)).data,
    staleTime: 30_000,
    retry: 1,
    ...options,
  });
}

export function useApiEnvelope<T>(
  key: string,
  path: string,
  params?: Record<string, unknown>,
  options?: Omit<UseQueryOptions<ApiEnvelope<T>, ApiError>, 'queryKey' | 'queryFn'>,
) {
  return useQuery<ApiEnvelope<T>, ApiError>({
    queryKey: [key, path, params ?? {}],
    queryFn: () => api.get<T>(path, params),
    staleTime: 30_000,
    retry: 1,
    ...options,
  });
}

export function useActionMutation<TData = unknown, TVariables = void>(
  action: (variables: TVariables) => Promise<ApiEnvelope<TData>>,
  options?: Omit<UseMutationOptions<ApiEnvelope<TData>, ApiError, TVariables>, 'mutationFn'>,
) {
  return useMutation<ApiEnvelope<TData>, ApiError, TVariables>({ mutationFn: action, ...options });
}
