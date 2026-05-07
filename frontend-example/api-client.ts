/**
 * Minimal TypeScript client for the FastAPI gateway.
 *
 * The response shape `{ data, error }` mirrors `supabase-js`, so migrating
 * call sites is mostly a matter of swapping the call function and removing
 * the `body:` wrapper.
 *
 * Usage (in a Vite / React app that already uses supabase-js for Auth):
 *
 *   import { supabase } from "@/integrations/supabase/client";
 *   import { createApiClient } from "@/lib/api-client";
 *
 *   const api = createApiClient({
 *     baseUrl: import.meta.env.VITE_API_URL,
 *     getAccessToken: async () => {
 *       const { data } = await supabase.auth.getSession();
 *       return data.session?.access_token ?? null;
 *     },
 *   });
 *
 *   const { data, error } = await api.get<Profile>("/v1/profile");
 */

export interface ApiError {
  message: string;
  status?: number;
  details?: unknown;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
}

export interface CreateApiClientOptions {
  baseUrl: string;
  getAccessToken: () => Promise<string | null>;
}

type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

interface RequestOptions {
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
}

function buildUrl(
  baseUrl: string,
  path: string,
  query?: RequestOptions["query"],
): string {
  const url = new URL(path, baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

export function createApiClient(options: CreateApiClientOptions) {
  const baseUrl = options.baseUrl.replace(/\/$/, "");

  async function request<T>(
    method: HttpMethod,
    path: string,
    init: RequestOptions = {},
  ): Promise<ApiResponse<T>> {
    const token = await options.getAccessToken();

    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (method !== "GET" && init.body !== undefined) {
      headers["Content-Type"] = "application/json";
    }

    let response: Response;
    try {
      response = await fetch(buildUrl(baseUrl, path, init.query), {
        method,
        headers,
        body:
          method === "GET" || init.body === undefined
            ? undefined
            : JSON.stringify(init.body),
      });
    } catch (err) {
      return {
        data: null,
        error: {
          message: err instanceof Error ? err.message : "Network error",
        },
      };
    }

    let payload: unknown = null;
    if (response.status !== 204) {
      try {
        payload = await response.json();
      } catch {
        return {
          data: null,
          error: {
            message: "Invalid JSON from gateway",
            status: response.status,
          },
        };
      }
    }

    if (!response.ok) {
      const detail =
        payload && typeof payload === "object" && "detail" in payload
          ? (payload as { detail: unknown }).detail
          : null;
      const message =
        typeof detail === "string"
          ? detail
          : `Request failed with status ${response.status}`;
      return {
        data: null,
        error: { message, status: response.status, details: payload },
      };
    }

    return { data: payload as T, error: null };
  }

  return {
    get: <T = unknown>(path: string, init?: RequestOptions) =>
      request<T>("GET", path, init),
    post: <T = unknown>(path: string, init?: RequestOptions) =>
      request<T>("POST", path, init),
    patch: <T = unknown>(path: string, init?: RequestOptions) =>
      request<T>("PATCH", path, init),
    delete: <T = unknown>(path: string, init?: RequestOptions) =>
      request<T>("DELETE", path, init),

    publicAssetUrl(objectPath: string): string {
      const cleaned = objectPath.replace(/^\/+/, "");
      return `${baseUrl}/v1/storage/public/${cleaned}`;
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
