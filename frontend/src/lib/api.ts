import {
  getDemoAnalysis,
  getDemoFile,
  getDemoProject,
  getDemoProjects,
  getDemoRecent,
} from "./demo-data";

export function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (
    typeof window !== "undefined" &&
    window.location.hostname !== "localhost" &&
    window.location.hostname !== "127.0.0.1"
  ) {
    return "";
  }
  // Same origin + next.config rewrites → /api/* проксируется на uvicorn :8000
  if (typeof window !== "undefined") {
    return "";
  }
  return process.env.BACKEND_URL || "http://127.0.0.1:8000";
}

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
const DEFAULT_TIMEOUT_MS = 20_000;

async function request<T>(
  path: string,
  options?: RequestInit & { timeoutMs?: number }
): Promise<T> {
  if (DEMO_MODE) {
    return demoRequest<T>(path, options);
  }

  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { timeoutMs: _t, signal: extSignal, ...fetchOptions } = options ?? {};
  const controller = new AbortController();
  const timer =
    typeof window !== "undefined"
      ? window.setTimeout(() => controller.abort(), timeoutMs)
      : undefined;

  let res: Response;
  try {
    res = await fetch(`${getApiBase()}${path}`, {
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...fetchOptions.headers,
      },
      signal: extSignal ?? controller.signal,
      ...fetchOptions,
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error(`API timeout after ${timeoutMs}ms: ${path}`);
    }
    throw err;
  } finally {
    if (timer !== undefined) window.clearTimeout(timer);
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }

  const body = await res.text();
  if (!body) {
    return undefined as T;
  }

  return JSON.parse(body) as T;
}

function demoRequest<T>(path: string, options?: RequestInit): T {
  const method = options?.method?.toUpperCase() ?? "GET";

  if (method !== "GET") {
    throw new Error("В демо-режиме доступен только просмотр готовых примеров");
  }

  if (path === "/api/projects") {
    return getDemoProjects() as T;
  }

  const searchMatch = path.match(/^\/api\/search\?q=([^&]*)/);
  if (searchMatch) {
    const q = decodeURIComponent(searchMatch[1]).toLowerCase();
    const projects = getDemoProjects().filter((p) =>
      p.name.toLowerCase().includes(q)
    );
    const files = getDemoRecent(50).filter((f) => f.name.toLowerCase().includes(q));
    return { projects, files } as T;
  }

  const projectMatch = path.match(/^\/api\/projects\/([^/]+)$/);
  if (projectMatch) {
    const project = getDemoProject(projectMatch[1]);
    if (!project) throw new Error(`API error 404: project`);
    return project as T;
  }

  const recentMatch = path.match(/^\/api\/files\/recent\?limit=(\d+)$/);
  if (recentMatch) {
    return getDemoRecent(Number(recentMatch[1])) as T;
  }

  const fileMatch = path.match(/^\/api\/files\/([^/]+)$/);
  if (fileMatch && !path.endsWith("/analysis")) {
    const file = getDemoFile(fileMatch[1]);
    if (!file) throw new Error(`API error 404: file`);
    return file as T;
  }

  const analysisMatch = path.match(/^\/api\/files\/([^/]+)\/analysis$/);
  if (analysisMatch) {
    const analysis = getDemoAnalysis(analysisMatch[1]);
    if (!analysis) throw new Error(`API error 404: analysis`);
    return analysis as T;
  }

  if (path === "/api/health") {
    return { status: "ok", service: "framecheck-demo" } as T;
  }

  throw new Error(`API error 404: ${path}`);
}

export interface AnalysisSummaryAPI {
  total_scenes: number;
  risky_scenes: number;
  review_count?: number;
  risk_categories: Record<string, number>;
  critical_count: number;
  warning_count: number;
  recommended_age_rating?: string | null;
  age_rating_reason?: string | null;
  age_rating_triggers?: AgeRatingTriggerAPI[];
  entities?: EntityAPI[];
  markings_detected?: MarkingAPI[];
  compliance_checks?: ComplianceCheckAPI[];
  registry_verifications?: RegistryVerificationAPI[];
  legal_disclaimer?: string;
  incomplete_coverage?: boolean;
  incomplete_coverage_note?: string;
}

export interface ComplianceCheckAPI {
  law: string;
  title: string;
  status: string;
  findings_count: number;
  note?: string;
  articles?: string[];
  registry_source?: string;
}

export interface RegistryVerificationAPI {
  name: string;
  type?: string;
  scene_number?: number;
  context?: string;
  registry?: string | null;
  registry_status: string;
  matched_registry_name?: string | null;
  law?: string | null;
  article?: string | null;
  severity?: string;
  required_marking?: string | null;
  marking_found?: boolean | null;
  source_url?: string;
}

export interface AgeRatingTriggerAPI {
  scene_number?: number;
  start_time?: string;
  end_time?: string;
  trigger?: string;
  reason?: string;
}

export interface EntityAPI {
  type?: string;
  name?: string;
  scene_number?: number;
  context?: string;
  registry?: string | null;
  registry_status?: string;
  matched_registry_name?: string | null;
  law?: string | null;
  article?: string | null;
  severity?: string;
}

export interface MarkingAPI {
  type?: string;
  text?: string;
  scene_number?: number;
  start_time?: string;
}

export interface AnalysisBriefAPI {
  id: string;
  status: string;
  summary: AnalysisSummaryAPI | null;
  analyzed_at: string | null;
}

export interface ProjectAPI {
  id: string;
  name: string;
  created_at: string;
  files_count?: number;
  folders: FolderAPI[];
  files: VideoFileAPI[];
}

export interface FolderAPI {
  id: string;
  name: string;
  project_id: string;
  created_at: string;
}

export interface VideoFileAPI {
  id: string;
  name: string;
  size: number;
  status: string;
  progress: number;
  project_id: string;
  folder_id: string | null;
  storage_path: string | null;
  analysis_id: string | null;
  analysis?: AnalysisBriefAPI | null;
  created_at: string;
}

export interface SceneAPI {
  id: string;
  analysis_id: string;
  scene_number: number;
  start_time: string | null;
  end_time: string | null;
  description: string | null;
  risk: string | null;
  mode: string | null;
  risk_level: string | null;
  probability: number | null;
  reason: string | null;
  quote: string | null;
  text_in_frame: string | null;
  recommendation: string | null;
}

export interface AnalysisAPI {
  id: string;
  video_file_id: string;
  video_title: string | null;
  duration: string | null;
  analyzed_at: string | null;
  summary: AnalysisSummaryAPI | null;
  status: string;
  created_at: string;
  scenes: SceneAPI[];
}

export interface OrganizationAPI {
  id: string;
  name: string;
  slug: string;
}

export interface UserAPI {
  id: string;
  email: string;
  display_name: string;
  role: string;
  organization: OrganizationAPI | null;
  active_organization: OrganizationAPI | null;
  created_at: string;
}

export interface AuthConfigAPI {
  auth_required: boolean;
  authenticated: boolean;
}

export const api = {
  auth: {
    config: () => request<AuthConfigAPI>("/api/auth/config"),
    me: () => request<UserAPI | null>("/api/auth/me"),
    register: (body: {
      email: string;
      password: string;
      display_name: string;
      registration_code: string;
    }) =>
      request<UserAPI>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    validateCode: (registration_code: string) =>
      request<{ valid: boolean; organization: OrganizationAPI }>(
        "/api/auth/validate-code",
        {
          method: "POST",
          body: JSON.stringify({ registration_code }),
        }
      ),
    listOrganizations: () =>
      request<OrganizationAPI[]>("/api/auth/organizations"),
    switchOrganization: (organization_id: string) =>
      request<UserAPI>("/api/auth/active-organization", {
        method: "POST",
        body: JSON.stringify({ organization_id }),
      }),
    login: (body: { email: string; password: string }) =>
      request<UserAPI>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    logout: () =>
      request<void>("/api/auth/logout", {
        method: "POST",
      }),
    updateProfile: (body: { display_name?: string; email?: string }) =>
      request<UserAPI>("/api/auth/me", {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
  },

  search: (q: string, limit = 8) =>
    request<{ projects: ProjectAPI[]; files: VideoFileAPI[] }>(
      `/api/search?q=${encodeURIComponent(q)}&limit=${limit}`,
      { timeoutMs: 10_000 }
    ),

  workspace: {
    summary: (recentLimit = 24) =>
      request<{
        projects: ProjectAPI[];
        recent_files: VideoFileAPI[];
        in_progress_count: number;
      }>(`/api/workspace/summary?recent_limit=${recentLimit}`, {
        timeoutMs: 15_000,
      }),
  },

  projects: {
    list: () => request<ProjectAPI[]>("/api/projects"),
    get: (id: string) => request<ProjectAPI>(`/api/projects/${id}`),
    create: (name: string) =>
      request<ProjectAPI>("/api/projects", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    rename: (id: string, name: string) =>
      request<ProjectAPI>(`/api/projects/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      }),
    delete: (id: string) =>
      request<void>(`/api/projects/${id}`, {
        method: "DELETE",
      }),
  },

  files: {
    get: (id: string) => request<VideoFileAPI>(`/api/files/${id}`),
    recent: (limit = 12, options?: { analyzedOnly?: boolean }) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (options?.analyzedOnly === false) {
        params.set("analyzed_only", "false");
      }
      return request<VideoFileAPI[]>(`/api/files/recent?${params.toString()}`);
    },
    assignToProject: (fileId: string, projectId: string) =>
      request<VideoFileAPI>(`/api/files/${fileId}/project`, {
        method: "PATCH",
        body: JSON.stringify({ project_id: projectId }),
      }),
    delete: (fileId: string) =>
      request<void>(`/api/files/${fileId}`, {
        method: "DELETE",
      }),
    getAnalysis: (id: string) =>
      request<AnalysisAPI>(`/api/files/${id}/analysis`),
    analyze: (id: string, options?: { force?: boolean }) => {
      if (DEMO_MODE) {
        return Promise.reject(new Error("Анализ недоступен в демо на GitHub Pages"));
      }
      const qs = options?.force ? "?force=true" : "";
      return request<AnalysisAPI | { status: string; file_id: string }>(
        `/api/files/${id}/analyze${qs}`,
        { method: "POST" }
      );
    },
    getReportUrl: (id: string) => `${getApiBase()}/api/files/${id}/report`,
    upload: async (
      projectId: string,
      file: File,
      folderId?: string,
      onProgress?: (progress: number) => void
    ): Promise<VideoFileAPI> => {
      if (DEMO_MODE) {
        throw new Error("Загрузка недоступна в демо на GitHub Pages");
      }

      const formData = new FormData();
      formData.append("file", file);

      const params = new URLSearchParams({ project_id: projectId });
      if (folderId) params.append("folder_id", folderId);

      const xhr = new XMLHttpRequest();

      return new Promise((resolve, reject) => {
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable && onProgress) {
            onProgress(Math.round((e.loaded / e.total) * 100));
          }
        });

        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            reject(new Error(`Upload failed: ${xhr.status}`));
          }
        });

        xhr.addEventListener("error", () => reject(new Error("Upload failed")));

        xhr.withCredentials = true;
        xhr.open("POST", `${getApiBase()}/api/files/upload?${params.toString()}`);
        xhr.send(formData);
      });
    },
  },

  health: () => request<{ status: string }>("/api/health"),

  ops: {
    metrics: () =>
      request<{
        video_provider: string;
        object_storage: boolean;
        cascade_enabled: boolean;
        worker_poll_seconds: number;
        videos_by_status: Record<string, number>;
        jobs_by_status: Record<string, number>;
        analyzing_count: number;
        queued_jobs: number;
        failed_jobs: number;
        stale_analyzing: number;
        max_job_attempts: number;
      }>("/api/ops/metrics"),
  },
};
